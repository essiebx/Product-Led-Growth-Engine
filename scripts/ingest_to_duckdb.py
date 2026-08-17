import os
import duckdb
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def ingest_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    db_path = os.path.join(base_dir, "plg_engine.duckdb")

    logger.info(f"Connecting to DuckDB at {db_path}")
    conn = duckdb.connect(db_path)
    
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    files_to_ingest = {
        "hubspot_leads": "hubspot_leads.csv",
        "salesforce_deals": "salesforce_deals.csv",
        "vwo_experiments": "vwo_experiments.csv"
    }

    for table_name, file_name in files_to_ingest.items():
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            logger.info(f"Ingesting {file_name} into raw.{table_name}...")
            # Windows path handling for duckdb: replace backslashes with forward slashes
            safe_file_path = file_path.replace('\\', '/')
            conn.execute(f"CREATE OR REPLACE TABLE raw.{table_name} AS SELECT * FROM read_csv_auto('{safe_file_path}');")
        else:
            logger.warning(f"File {file_path} not found, skipping.")

    logger.info("Data ingestion complete.")
    conn.close()

if __name__ == "__main__":
    ingest_data()
