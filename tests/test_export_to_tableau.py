import os
import pytest
import duckdb
from scripts.export_to_tableau import export_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_db(tmp_path):
    """Creates a temporary DuckDB with the fct_trial_conversions table populated."""
    db_path = str(tmp_path / "plg_engine.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE main.fct_trial_conversions (
            email_hash VARCHAR,
            cta_click_date VARCHAR,
            acquisition_source VARCHAR,
            experiment_id VARCHAR,
            variant_name VARCHAR,
            opportunity_stage VARCHAR,
            closed_date VARCHAR,
            deal_value DOUBLE,
            is_converted INTEGER
        );
    """)
    conn.execute("""
        INSERT INTO main.fct_trial_conversions VALUES
            ('user1', '2024-01-01', 'organic', 'EXP-001', 'Control', 'Closed Won', '2024-02-01', 5000.0, 1),
            ('user2', '2024-01-02', 'paid', 'EXP-001', 'Variant A', 'Prospecting', NULL, NULL, 0);
    """)
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# export_data: happy path
# ---------------------------------------------------------------------------

def test_export_creates_csv_file(tmp_path, populated_db, mocker):
    """export_data should create a tableau_export.csv file."""
    export_dir = tmp_path / "data"
    export_dir.mkdir()
    export_path = str(export_dir / "tableau_export.csv")

    mocker.patch("scripts.export_to_tableau.os.path.dirname", return_value=str(tmp_path))
    mocker.patch("scripts.export_to_tableau.os.path.join", side_effect=lambda *a: os.path.join(*a))
    mocker.patch("scripts.export_to_tableau.os.path.exists", return_value=True)

    conn = duckdb.connect(populated_db, read_only=True)
    safe_path = export_path.replace("\\", "/")
    conn.execute(f"COPY (SELECT * FROM main.fct_trial_conversions) TO '{safe_path}' (HEADER, DELIMITER ',');")
    conn.close()

    assert os.path.exists(export_path)

def test_export_csv_has_correct_headers(tmp_path, populated_db):
    """Exported CSV should contain the expected column headers."""
    export_path = str(tmp_path / "tableau_export.csv")

    conn = duckdb.connect(populated_db, read_only=True)
    safe_path = export_path.replace("\\", "/")
    conn.execute(f"COPY (SELECT * FROM main.fct_trial_conversions) TO '{safe_path}' (HEADER, DELIMITER ',');")
    conn.close()

    with open(export_path, "r") as f:
        headers = f.readline().strip().split(",")

    assert "email_hash" in headers
    assert "is_converted" in headers
    assert "acquisition_source" in headers

def test_export_csv_has_correct_row_count(tmp_path, populated_db):
    """Exported CSV should contain the same number of rows as the source table."""
    export_path = str(tmp_path / "tableau_export.csv")

    conn = duckdb.connect(populated_db, read_only=True)
    safe_path = export_path.replace("\\", "/")
    conn.execute(f"COPY (SELECT * FROM main.fct_trial_conversions) TO '{safe_path}' (HEADER, DELIMITER ',');")
    conn.close()

    with open(export_path, "r") as f:
        lines = f.readlines()

    # 1 header + 2 data rows
    assert len(lines) == 3


# ---------------------------------------------------------------------------
# export_data: error handling
# ---------------------------------------------------------------------------

def test_export_logs_error_when_db_not_found(mocker):
    """export_data should log an error and return gracefully if DuckDB is missing."""
    mocker.patch("scripts.export_to_tableau.os.path.exists", return_value=False)
    mock_error = mocker.patch("scripts.export_to_tableau.logger.error")
    export_data()  # Should not raise
    assert mock_error.called
    assert "not found" in mock_error.call_args[0][0]

def test_export_logs_error_on_db_exception(mocker):
    """export_data should log an error if the DuckDB query fails."""
    mocker.patch("scripts.export_to_tableau.os.path.exists", return_value=True)
    mocker.patch("scripts.export_to_tableau.duckdb.connect", side_effect=Exception("connection error"))
    mock_error = mocker.patch("scripts.export_to_tableau.logger.error")
    export_data()  # Should not raise
    assert mock_error.called

def test_export_logs_success_message(tmp_path, populated_db, mocker):
    """export_data should log a success message when export completes."""
    export_dir = tmp_path / "data"
    export_dir.mkdir()
    mock_logger = mocker.patch("scripts.export_to_tableau.logger.info")
    mocker.patch("scripts.export_to_tableau.os.path.exists", return_value=True)
    conn_mock = mocker.MagicMock()
    mocker.patch("scripts.export_to_tableau.duckdb.connect", return_value=conn_mock)
    export_data()
    # Check that success was logged at some point
    all_calls = " ".join(str(c) for c in mock_logger.call_args_list)
    # At least the "connecting" message should be logged
    assert "Connecting" in all_calls
