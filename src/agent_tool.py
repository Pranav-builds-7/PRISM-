import os
import urllib
import requests
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from langchain_core.tools import tool



script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  

load_dotenv(dotenv_path=project_root / ".env")




# 1. CACHED HUGGING FACE EMBEDDINGS

def get_cached_huggingface_embeddings(model_name: str):
    """
    Loads and caches Hugging Face model weights
    across Streamlit reruns.
    """
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _load_model(name: str):
        print(f"🧠 MEMORY SEED: Caching local model [{name}]...")
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

    return _load_model(model_name)


@lru_cache(maxsize=1)
def get_sop_retriever():
    """Load the local embedding model and Pinecone retriever on first SOP search."""
    local_model_target = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "BAAI/bge-small-en-v1.5"
    ).strip()

    print(
        f"HuggingFace Mode: Connecting to Local Hugging Face "
        f"[{local_model_target}] Index (384 Dim Space)..."
    )

    try:
        import streamlit as st

        if st.runtime.exists():
            embeddings = get_cached_huggingface_embeddings(local_model_target)
        else:
            from langchain_huggingface import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(
                model_name=local_model_target,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
    except ImportError:
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(
            model_name=local_model_target,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

    from langchain_pinecone import PineconeVectorStore

    vector_store = PineconeVectorStore(
        index_name="fde-sop-index-local",
        embedding=embeddings
    )
    return vector_store.as_retriever(search_kwargs={"k": 2})

# 2. DATABASE CONFIGURATION


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

db_host = os.getenv("MYSQL_HOST", "localhost")
db_port = os.getenv("MYSQL_PORT", "3307")
db_user = os.getenv("MYSQL_USER", "usr_fde_ro")
db_password = os.getenv("MYSQL_PASSWORD")
db_name = os.getenv("MYSQL_DATABASE", "FDE_VIEWS")



# 3. VALIDATE PINECONE API KEY


if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is missing from .env")


@tool
def query_telemetry_db(sql_query: str) -> str:
    """
    Executes a SQL SELECT query against the FDE_VIEWS.VW_ACTIVE_FLEET view.
    Columns available:
    Timestamp, Latitude, Longitude, Current_Temperature_C, Cargo_Condition_Code,
    Risk_Classification, Delay_Probability, Port_Congestion_Level, Route_Risk_Index.
    Always write standard MySQL queries.
    """

    connection_string = (
        f"mysql+pymysql://{db_user}:"
        f"{urllib.parse.quote_plus(db_password)}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    engine = None
    try:
        if not sql_query.strip().upper().startswith("SELECT"):
            return "SECURITY BLOCK: Only SELECT operations are authorized on this view."

        engine = create_engine(
            connection_string,
            connect_args={
                "connect_timeout": 5,
                "read_timeout": 15,
                "write_timeout": 5,
            },
        )
        with engine.connect() as conn:
            cursor = conn.execute(text(sql_query))
            columns = list(cursor.keys())
            rows = cursor.fetchmany(10)

            if not rows:
                return "No records matched the query criteria."

            formatted_output = f"COLUMNS: {', '.join(columns)}\n"
            for row in rows:
                formatted_output += str(tuple(row)) + "\n"

            return formatted_output

    except Exception as e:
        return f"Database Error: {str(e)}"
    finally:
        if engine is not None:
            engine.dispose()
    

@tool
def fetch_corridor_conditions(latitude: float, longitude: float) -> str:
    """
    Fetches real-time weather and corridor conditions from a live REST API for given GPS coordinates.
    Provides temperature, wind speed, and computed corridor congestion index.
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        response = requests.get(url, timeout=6)
        response.raise_for_status()
        
        payload = response.json().get("current_weather", {})
        temp = payload.get("temperature", "N/A")
        wind = payload.get("windspeed", 0.0)
        
        congestion_index = 8.5 if wind > 10.0 else 2.5
        status_note = "High Transit Disruption" if wind > 10.0 else "Corridor Normal"
        
        return (
            f"--- LIVE CORRIDOR TELEMETRY ---\n"
            f"Target GPS: {latitude}, {longitude}\n"
            f"External Temp: {temp}°C | Wind Speed: {wind} km/h\n"
            f"Corridor Risk: {status_note} (Congestion Index: {congestion_index}/10)\n"
            f"-------------------------------"
        )
    except Exception as e:
        return f"Corridor API Communication Failure: {str(e)}"
    

@tool
def search_compliance_sop(query: str) -> str:
    """
    Searches enterprise Standard Operating Procedures (SOPs) indexed in the Pinecone Vector DB.
    Use this to retrieve regulatory thresholds, cold-chain breach mitigations, and rerouting rules.
    """
    try:
        matched_docs = get_sop_retriever().invoke(query)
        if not matched_docs:
            return "No matching compliance clauses found."
            
        formatted_context = "\n\n".join(
              [f"[Source: {doc.metadata.get('source_file', 'SOP')} | Format: {doc.metadata.get('file_format', 'RAW')}]\n{doc.page_content}" for doc in matched_docs]
        )
        return f"--- COMPLIANCE SOP CONTEXT ---\n{formatted_context}\n------------------------------"
    except Exception as e:
        return f"Vector Store Retrieval Error: {str(e)}"



if __name__ == "__main__":
    print("\n--- Testing Tool 1: SQL Telemetry View ---")
    print(query_telemetry_db.invoke(
    "SELECT Latitude, Longitude, Current_Temperature_C FROM FDE_VIEWS.VW_ACTIVE_FLEET LIMIT 2"
))
    
    print("\n--- Testing Tool 2: Live Corridor API ---")
    print(fetch_corridor_conditions.invoke({"latitude": 33.77, "longitude": -118.19}))
    
    print("\n--- Testing Tool 3: Pinecone Vector Retrieval ---")
    print(search_compliance_sop.invoke("What are the temperature rules for fresh perishables?"))    