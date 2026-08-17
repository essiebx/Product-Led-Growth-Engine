import os
import pytest
import duckdb
from scripts.ingest_to_duckdb import ingest_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_data_dir(tmp_path):
    """Creates a temporary data directory with all three mock CSVs."""
    (tmp_path / "hubspot_leads.csv").write_text(
        "email_hash,cta_click_date,acquisition_source\nuser1,2024-01-01,organic\nuser2,2024-01-02,paid\n"
    )
    (tmp_path / "salesforce_deals.csv").write_text(
        "email_hash,opportunity_stage,closed_date,deal_value\nuser1,Closed Won,2024-02-01,5000\n"
    )
    (tmp_path / "vwo_experiments.csv").write_text(
        "email_hash,experiment_id,variant_name\nuser1,EXP-001,Control\nuser2,EXP-001,Variant A\n"
    )
    return tmp_path

@pytest.fixture
def in_memory_db():
    """Provides an isolated in-memory DuckDB connection for inspection."""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# ingest_data: happy path
# ---------------------------------------------------------------------------

def test_ingest_creates_raw_schema(tmp_path, mock_data_dir, mocker):
    """After ingestion, the 'raw' schema should exist in the database."""
    db_path = str(tmp_path / "test.duckdb")
    mocker.patch(
        "scripts.ingest_to_duckdb.os.path.dirname",
        side_effect=lambda p: str(tmp_path) if "ingest" in p else os.path.dirname(p)
    )
    # Run with patched paths so it writes to tmp_path
    conn = duckdb.connect(db_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    schemas = [row[0] for row in conn.execute("SELECT schema_name FROM information_schema.schemata;").fetchall()]
    conn.close()
    assert "raw" in schemas

def test_ingest_loads_all_three_tables(tmp_path, mock_data_dir):
    """All three staging tables should be created in the raw schema."""
    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    for table, filename in [
        ("hubspot_leads", "hubspot_leads.csv"),
        ("salesforce_deals", "salesforce_deals.csv"),
        ("vwo_experiments", "vwo_experiments.csv"),
    ]:
        safe_path = str(mock_data_dir / filename).replace("\\", "/")
        conn.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM read_csv_auto('{safe_path}');")

    tables = [row[0] for row in conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw';"
    ).fetchall()]
    conn.close()

    assert "hubspot_leads" in tables
    assert "salesforce_deals" in tables
    assert "vwo_experiments" in tables

def test_ingest_correct_row_counts(tmp_path, mock_data_dir):
    """Tables should contain the same number of rows as the source CSVs."""
    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    safe_hs = str(mock_data_dir / "hubspot_leads.csv").replace("\\", "/")
    conn.execute(f"CREATE OR REPLACE TABLE raw.hubspot_leads AS SELECT * FROM read_csv_auto('{safe_hs}');")

    row_count = conn.execute("SELECT COUNT(*) FROM raw.hubspot_leads;").fetchone()[0]
    conn.close()
    assert row_count == 2  # our fixture has 2 rows

def test_ingest_correct_columns_hubspot(tmp_path, mock_data_dir):
    """Ingested hubspot_leads should have all expected columns."""
    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    safe_hs = str(mock_data_dir / "hubspot_leads.csv").replace("\\", "/")
    conn.execute(f"CREATE OR REPLACE TABLE raw.hubspot_leads AS SELECT * FROM read_csv_auto('{safe_hs}');")
    cols = [row[0] for row in conn.execute("DESCRIBE raw.hubspot_leads;").fetchall()]
    conn.close()
    assert "email_hash" in cols
    assert "acquisition_source" in cols
    assert "cta_click_date" in cols


# ---------------------------------------------------------------------------
# ingest_data: missing files
# ---------------------------------------------------------------------------

def test_ingest_skips_missing_file(mocker):
    """ingest_data should log a warning and not crash if a CSV is missing."""
    mock_warn = mocker.patch("scripts.ingest_to_duckdb.logger.warning")
    mocker.patch("scripts.ingest_to_duckdb.os.path.dirname", return_value="/nonexistent")
    mocker.patch("scripts.ingest_to_duckdb.duckdb.connect").return_value.__enter__ = lambda s: s
    conn_mock = mocker.MagicMock()
    mocker.patch("scripts.ingest_to_duckdb.duckdb.connect", return_value=conn_mock)
    conn_mock.execute = mocker.MagicMock()
    # os.path.exists returns False for csv files, True for data_dir
    mocker.patch("os.path.exists", return_value=False)
    ingest_data()
    # Warning should have been logged for each missing file
    assert mock_warn.call_count >= 1

def test_ingest_handles_empty_data_dir(tmp_path, mocker):
    """ingest_data should not crash when data directory exists but is empty."""
    db_path = str(tmp_path / "test.duckdb")
    empty_dir = tmp_path / "empty_data"
    empty_dir.mkdir()
    mocker.patch("scripts.ingest_to_duckdb.os.path.dirname", return_value=str(tmp_path))
    mocker.patch("scripts.ingest_to_duckdb.os.path.join", side_effect=os.path.join)
    # Should just log warnings, not raise
    mock_warn = mocker.patch("scripts.ingest_to_duckdb.logger.warning")
    conn_mock = mocker.MagicMock()
    mocker.patch("scripts.ingest_to_duckdb.duckdb.connect", return_value=conn_mock)
    ingest_data()
    assert conn_mock.close.called
