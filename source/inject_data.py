from pathlib import Path
import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent


load_dotenv(project_root / ".env")

data_path = project_root / "Data" / "raw" / "dynamic_supply_chain_logistics_dataset.csv"

db_host = os.getenv("MYSQL_HOST", "localhost")
db_port = os.getenv("MYSQL_PORT", "3307")
db_user = os.getenv("MYSQL_USER", "root")
db_password = os.getenv("MYSQL_PASSWORD")
db_name = os.getenv("MYSQL_DATABASE", "logistics")

print(f"Loading CSV from {data_path}...")

df = pd.read_csv(data_path)

legacy_mapping = {
    "timestamp": "TS_UTC",
    "vehicle_gps_latitude": "V_LAT",
    "vehicle_gps_longitude": "V_LON",
    "iot_temperature": "IOT_TEMP_VAL_C",
    "cargo_condition_status": "CGO_COND_CD",
    "risk_classification": "RISK_CLS_TXT",
    "delay_probability": "DELAY_PROB_DEC",
    "port_congestion_level": "PRT_CNG_LVL",
    "route_risk_level": "RT_RSK_IDX"
}

df_legacy = df[list(legacy_mapping.keys())].rename(columns=legacy_mapping)

df_legacy["SYS_INGEST_FLAG"] = "Y"

print("Connecting to legacy MySQL database...")

connection_url = (
    f"mysql+pymysql://{db_user}:{db_password}"
    f"@{db_host}:{db_port}/{db_name}"
)

engine = create_engine(connection_url)

table_name = "TBL_SC_FLEET_HIST_RAW"

print(f"Ingesting into {table_name}. This may take a minute...")

df_legacy.to_sql(
    table_name,
    engine,
    if_exists="replace",
    index=False
)

print("✅ Legacy MySQL data ingestion complete!")

