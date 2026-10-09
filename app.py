"""Basic local Streamlit UI for the PRISM logistics project."""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "Data" / "raw" / "dynamic_supply_chain_logistics_dataset.csv"
logger = logging.getLogger(__name__)

load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="PRISM | Logistics Operations",
    page_icon="🚚",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #08111f; color: #e7eef8; }
    [data-testid="stSidebar"] { background: #0d1828; }
    .hero {
        padding: 1.2rem 1.5rem; border: 1px solid #233956; border-radius: 16px;
        background: linear-gradient(120deg, #102744, #0c1728 70%);
        margin-bottom: 1rem;
    }
    .hero h1 { margin: 0; color: #f1f6ff; }
    .hero p { margin: .45rem 0 0; color: #a8bad1; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Reading the project CSV…")
def read_dataset(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def get_project_tools() -> tuple[Any, Any, Any]:
    from src.agent_tool import (
        fetch_corridor_conditions,
        query_telemetry_db,
        search_compliance_sop,
    )

    return query_telemetry_db, fetch_corridor_conditions, search_compliance_sop


def safe_display_text(value: Any) -> str:
    text = str(value)
    for name in (
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "PINECONE_API_KEY",
        "LANGCHAIN_API_KEY",
        "MYSQL_PASSWORD",
    ):
        secret = os.getenv(name)
        if secret:
            text = text.replace(secret, "[redacted]")
    text = re.sub(
        r"(?i)mysql(?:\+\w+)?://[^\s'\"`]+",
        "mysql://[redacted]",
        text,
    )
    text = re.sub(
        r"(?i)\b(password|api[_ -]?key|token)\s*([=:])\s*[^\s,;]+",
        r"\1\2[redacted]",
        text,
    )
    return text


def render_overview() -> None:
    st.subheader("How PRISM helps logistics teams")
    st.write(
        "PRISM helps operations teams spot shipment risks sooner, understand what may "
        "be affecting a delivery, and identify practical next steps."
    )

    st.markdown("#### Core highlights")
    highlights = st.columns(3)
    highlights[0].markdown(
        "**See emerging risks**\n\n"
        "Review fleet temperature, delay, congestion, and risk information to find "
        "shipments that may need attention."
    )
    highlights[1].markdown(
        "**Understand conditions**\n\n"
        "Check corridor weather for a shipment location and bring relevant operating "
        "guidance into the investigation."
    )
    highlights[2].markdown(
        "**Move from question to action**\n\n"
        "Ask the dispatch assistant to combine available telemetry, corridor conditions, "
        "and procedures into a concise operational response."
    )

    st.markdown("#### Explore PRISM")
    st.markdown(
        "- **Data explorer:** inspect the fleet dataset included with this project.\n"
        "- **Tool checks:** verify each connected data service when troubleshooting.\n"
        "- **Dispatch assistant:** ask an operational question and review the response."
    )
    st.info(
        "PRISM recommendations depend on the connected data and services being available. "
        "Confirm operational details with the source data and your team's procedures."
    )


def render_data_explorer() -> None:
    st.subheader("Data explorer")
    st.caption("Fleet data summary and shipment locations from the project dataset.")
    if not DATASET_PATH.exists():
        st.error(f"Project dataset not found: {DATASET_PATH}")
        return
    try:
        df = read_dataset(str(DATASET_PATH))
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
        OSError,
        ValueError,
    ) as exc:
        logger.error("Project dataset could not be read (%s)", type(exc).__name__)
        st.error("The project dataset could not be read. Check the CSV file and try again.")
        return

    if df.empty:
        st.info("The project dataset is empty, so there is no summary to display.")
        return

    risk_column = "risk_classification"
    temp_column = "iot_temperature"
    delay_column = "delay_probability"
    expected_columns = {
        risk_column,
        temp_column,
        delay_column,
        "vehicle_gps_latitude",
        "vehicle_gps_longitude",
    }
    missing_columns = sorted(expected_columns.difference(df.columns))
    if missing_columns:
        st.info(
            "Some dataset summaries are unavailable because expected columns are missing: "
            + ", ".join(missing_columns)
        )

    risk = df[risk_column].fillna("Unknown") if risk_column in df.columns else None
    temperature = (
        pd.to_numeric(df[temp_column], errors="coerce")
        if temp_column in df.columns
        else None
    )
    delay_probability = (
        pd.to_numeric(df[delay_column], errors="coerce")
        if delay_column in df.columns
        else None
    )

    st.caption(
        f"Dataset summary · `{DATASET_PATH.name}` · {len(df):,} historical records "
        "(not live fleet status)"
    )
    metrics = st.columns(4)
    metrics[0].metric("Dataset records", f"{len(df):,}")
    metrics[1].metric(
        "Dataset high-risk records",
        f"{int((risk == 'High Risk').sum()):,}" if risk is not None else "N/A",
    )
    metrics[2].metric(
        "Dataset readings above 4°C",
        f"{int((temperature > 4.0).sum()):,}" if temperature is not None else "N/A",
        help="Historical dataset count using the fresh-perishables threshold in the project SOP.",
    )
    metrics[3].metric(
        "Dataset delays above 65%",
        f"{int((delay_probability > 0.65).sum()):,}"
        if delay_probability is not None
        else "N/A",
    )

    chart_column, map_column = st.columns((1, 1.4))
    if risk is not None:
        with chart_column:
            st.markdown("#### Dataset risk profile")
            risk_summary = (
                risk.value_counts()
                .rename_axis("Risk classification")
                .reset_index(name="Records")
            )
            st.bar_chart(risk_summary, x="Risk classification", y="Records", color="#ef4444")

    lat_col, lon_col = "vehicle_gps_latitude", "vehicle_gps_longitude"
    if lat_col in df.columns and lon_col in df.columns:
        map_data = df[[lat_col, lon_col]].rename(
            columns={lat_col: "lat", lon_col: "lon"}
        )
        map_data = map_data.apply(pd.to_numeric, errors="coerce").dropna()
        if not map_data.empty:
            map_data = map_data.sample(
                n=min(len(map_data), 2000),
                random_state=0,
            )
            import pydeck as pdk

            with map_column:
                st.markdown("#### Dataset shipment locations")
                if len(map_data) < len(df):
                    st.caption("Showing a representative sample of up to 2,000 locations.")
                st.pydeck_chart(
                    pdk.Deck(
                        map_style=None,
                        initial_view_state=pdk.ViewState(
                            latitude=float(map_data["lat"].mean()),
                            longitude=float(map_data["lon"].mean()),
                            zoom=3,
                            pitch=0,
                        ),
                        layers=[
                            pdk.Layer(
                                "ScatterplotLayer",
                                data=map_data,
                                get_position="[lon, lat]",
                                get_fill_color=[239, 68, 68, 190],
                                get_radius=2500,
                                radius_min_pixels=3,
                                radius_max_pixels=8,
                                pickable=False,
                            )
                        ],
                    ),
                    width="stretch",
                )
        else:
            with map_column:
                st.info("The dataset has no valid shipment coordinates to map.")
    else:
        with map_column:
            st.info("Shipment map is unavailable because GPS columns are missing.")

    if temperature is not None and temperature.notna().any():
        st.markdown("#### Dataset temperature distribution")
        temperature_bins = pd.cut(temperature.dropna(), bins=12)
        temperature_summary = (
            temperature_bins.value_counts(sort=False)
            .rename_axis("Temperature range")
            .reset_index(name="Records")
        )
        temperature_summary["Temperature range"] = temperature_summary[
            "Temperature range"
        ].astype(str)
        st.bar_chart(temperature_summary, x="Temperature range", y="Records")


def render_tool_checks() -> None:
    st.subheader("Project tool checks")
    st.caption("Run each integration explicitly. The first SOP search may download/load local embeddings.")
    tool_choice = st.radio(
        "Tool",
        ("MySQL telemetry", "Corridor weather", "SOP search"),
        horizontal=True,
    )

    if tool_choice == "MySQL telemetry":
        st.write("Check that PRISM can reach the fleet data service.")
        if st.button("Check fleet data connection", type="primary"):
            try:
                query_tool, _, _ = get_project_tools()
                result = query_tool.invoke(
                    "SELECT `Timestamp`, Latitude, Longitude, Current_Temperature_C, "
                    "Cargo_Condition_Code, Risk_Classification, Delay_Probability, "
                    "Port_Congestion_Level, Route_Risk_Index "
                    "FROM FDE_VIEWS.VW_ACTIVE_FLEET ORDER BY `Timestamp` DESC LIMIT 5"
                )
                if result.startswith("COLUMNS:"):
                    record_count = max(len(result.splitlines()) - 1, 0)
                    st.success(
                        f"Fleet data connection is working. "
                        f"{record_count} recent record(s) were retrieved."
                    )
                elif result == "No records matched the query criteria.":
                    st.success("Fleet data connection is working, but no records were returned.")
                elif result.startswith("Database Error:") or result.startswith("SECURITY BLOCK:"):
                    logger.error("Fleet telemetry tool reported a database/security failure")
                    st.error("Could not check fleet data. Verify the database service and configuration.")
                else:
                    logger.error("Fleet telemetry tool returned an unexpected response")
                    st.error("The fleet data check did not complete successfully.")
            except Exception as exc:
                logger.error("Fleet telemetry check failed (%s)", type(exc).__name__)
                st.error("Could not check fleet data. Verify the database service and try again.")

    elif tool_choice == "Corridor weather":
        left, right = st.columns(2)
        latitude = left.number_input("Latitude", min_value=-90.0, max_value=90.0, value=33.5078)
        longitude = right.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-117.0369)
        if st.button("Check corridor conditions", type="primary"):
            try:
                _, weather_tool, _ = get_project_tools()
                result = weather_tool.invoke({"latitude": latitude, "longitude": longitude})
                if result.startswith("Corridor API Communication Failure:"):
                    logger.error("Corridor weather tool reported an API failure")
                    st.error("Could not retrieve corridor conditions. Try again later.")
                else:
                    st.code(result, language="text")
            except Exception as exc:
                logger.error("Corridor weather check failed (%s)", type(exc).__name__)
                st.error("Could not retrieve corridor conditions. Try again later.")

    else:
        question = st.text_input(
            "Question about the operating procedures",
            value="",
            placeholder="Enter a question when you are ready.",
        )
        if st.button("Search SOPs", type="primary", disabled=not question.strip()):
            try:
                _, _, sop_tool = get_project_tools()
                with st.spinner("Loading embeddings and searching the SOP index…"):
                    result = sop_tool.invoke(question)
                if result.startswith("Vector Store Retrieval Error:"):
                    logger.error("SOP search tool reported a vector-store failure")
                    st.error("Could not search operating procedures. Verify the SOP service and try again.")
                else:
                    st.markdown(result)
            except Exception as exc:
                logger.error("SOP search failed (%s)", type(exc).__name__)
                st.error("Could not search operating procedures. Verify the SOP service and try again.")


def render_dispatch_assistant() -> None:
    st.subheader("Dispatch assistant")
    st.caption(
        "Ask a question about fleet conditions. The agent may use MySQL, corridor weather, "
        "and SOP retrieval; the first request compiles the graph."
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_thread_id" not in st.session_state:
        st.session_state.chat_thread_id = None

    if st.button("New conversation"):
        st.session_state.chat_messages = []
        st.session_state.chat_thread_id = str(uuid.uuid4())
        st.rerun()

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    example_questions = (
        "Which vehicles have high-risk telemetry readings, and what are their current temperatures and delay probabilities?",
        "A refrigerated shipment is reporting a temperature of 9°C. What risks does this create, and what actions should the dispatcher take?",
        "Check the current weather conditions along the corridor. Could they disrupt deliveries, and what should we do?",
        "Search the compliance SOPs for the correct procedure when a refrigerated shipment exceeds its permitted temperature. Give me the recommended steps.",
        "Analyze the available telemetry, check relevant route conditions, consult the compliance SOPs, and recommend the best actions for the highest-risk shipment. Explain your reasoning.",
    )

    question = st.chat_input("Ask a question about fleet conditions…")
    suggested_question = None
    examples_placeholder = st.empty()
    if not st.session_state.chat_messages and not question:
        with examples_placeholder.container():
            st.markdown("**Example questions**")
            question_columns = st.columns(2)
            for index, example in enumerate(example_questions):
                if question_columns[index % 2].button(
                    example,
                    key=f"dispatch_example_{index}",
                    use_container_width=True,
                ):
                    suggested_question = example

    question = question or suggested_question
    if not question:
        return

    examples_placeholder.empty()
    st.session_state.chat_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from src.orchestration import fde_agent

        thread_id = st.session_state.chat_thread_id
        if thread_id is None:
            thread_id = str(uuid.uuid4())
            st.session_state.chat_thread_id = thread_id

        config = {"configurable": {"thread_id": thread_id}}
        checkpoint_messages = fde_agent.get_state(config).values.get("messages", [])
        has_system_prompt = any(
            isinstance(message, SystemMessage) for message in checkpoint_messages
        )
        messages = [HumanMessage(content=question)]
        if not has_system_prompt:
            prompt_path = ROOT / "src" / "prompts" / "system_prompts.txt"
            system_prompt = prompt_path.read_text(encoding="utf-8")
            messages.insert(0, SystemMessage(content=system_prompt))

        with st.chat_message("assistant"):
            with st.spinner("Running the PRISM agent and its tools…"):
                result = fde_agent.invoke(
                    {"messages": messages},
                    config=config,
                )
            answer = result["messages"][-1].content
            if isinstance(answer, list):
                answer = "\n".join(
                    str(block.get("text", "")) if isinstance(block, dict) else str(block)
                    for block in answer
                )
            safe_answer = safe_display_text(answer)
            st.markdown(safe_answer)
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": safe_answer}
        )
    except Exception as exc:
        logger.error("Dispatch assistant request failed (%s)", type(exc).__name__)
        st.error("PRISM could not complete that request. Check service availability and try again.")


with st.sidebar:
    st.title("PRISM")
    st.caption("Logistics intelligence")
    page = st.radio(
        "Workspace",
        ("Overview", "Data explorer", "Tool checks", "Dispatch assistant"),
    )
    st.divider()
    st.caption("Dataset and service calls are loaded only when requested.")

st.markdown(
    '<div class="hero"><h1>PRISM Logistics Command Center</h1>'
    "<p>Explore fleet data, validate project integrations, and investigate operational risks.</p></div>",
    unsafe_allow_html=True,
)

if page == "Overview":
    render_overview()
elif page == "Data explorer":
    render_data_explorer()
elif page == "Tool checks":
    render_tool_checks()
else:
    render_dispatch_assistant()
