import os
import duckdb
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def export_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "plg_engine.duckdb")
    export_path = os.path.join(base_dir, "data", "tableau_export.csv")

    logger.info(f"Connecting to DuckDB at {db_path}")
    if not os.path.exists(db_path):
        logger.error(f"DuckDB database not found at {db_path}")
        return

    try:
        conn = duckdb.connect(db_path, read_only=True)
        safe_export_path = export_path.replace('\\', '/')
        query = f"COPY (SELECT * FROM main.fct_trial_conversions) TO '{safe_export_path}' (HEADER, DELIMITER ',');"
        conn.execute(query)
        logger.info(f"Successfully exported data to {export_path}")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to export data: {e}")

if __name__ == "__main__":
    export_data()
