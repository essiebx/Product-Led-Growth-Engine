import os
import pandas as pd
# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch
from scripts.data_reconciliation import CRMDataReconciliator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_dir(tmp_path):
    """Creates a temporary directory that exists on disk."""
    return str(tmp_path)

@pytest.fixture
def mock_dir(mocker):
    """Patches os.path.exists so the constructor doesn't sys.exit."""
    mocker.patch("os.path.exists", return_value=True)
    return "/mock/dir"

@pytest.fixture
def hubspot_clean():
    return pd.DataFrame({
        "email_hash": ["user1", "user2", "user3"],
        "acquisition_source": ["organic", "paid", "email"]
    })

@pytest.fixture
def hubspot_missing_source():
    return pd.DataFrame({
        "email_hash": ["user1", "user2", "user3"],
        "acquisition_source": ["organic", "paid", None]
    })

@pytest.fixture
def vwo_clean():
    return pd.DataFrame({
        "email_hash": ["user1", "user2", "user3"],
        "experiment_id": ["EXP-001", "EXP-001", "EXP-001"]
    })

@pytest.fixture
def vwo_missing_experiment():
    return pd.DataFrame({
        "email_hash": ["user1", "user2"],
        "experiment_id": ["EXP-001", None]
    })

@pytest.fixture
def salesforce_full():
    return pd.DataFrame({
        "email_hash": ["user1", "user2", "user3"],
        "opportunity_stage": ["Closed Won", "Prospecting", "Qualified"]
    })

@pytest.fixture
def salesforce_partial():
    """user2 is missing — should be detected as orphan."""
    return pd.DataFrame({
        "email_hash": ["user1", "user3"],
        "opportunity_stage": ["Closed Won", "Prospecting"]
    })


# ---------------------------------------------------------------------------
# __init__: Constructor
# ---------------------------------------------------------------------------

def test_init_exits_if_dir_not_found(mocker):
    """Constructor should call sys.exit when data directory doesn't exist."""
    mocker.patch("os.path.exists", return_value=False)
    mock_exit = mocker.patch("sys.exit")
    CRMDataReconciliator("/nonexistent/path")
    mock_exit.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# extract_hubspot_leads
# ---------------------------------------------------------------------------

def test_extract_hubspot_leads_returns_dataframe(tmp_path, mocker):
    """Should return a DataFrame when the CSV exists."""
    csv_content = "email_hash,acquisition_source\nuser1,organic\n"
    csv_file = tmp_path / "hubspot_leads.csv"
    csv_file.write_text(csv_content)
    mocker.patch("os.path.exists", return_value=True)
    r = CRMDataReconciliator(str(tmp_path))
    df = r.extract_hubspot_leads()
    assert not df.empty
    assert "email_hash" in df.columns

def test_extract_hubspot_leads_missing_file(mock_dir):
    """Should return an empty DataFrame if file is missing."""
    with patch("os.path.exists", side_effect=lambda p: p == "/mock/dir"):
        r = CRMDataReconciliator("/mock/dir")
        df = r.extract_hubspot_leads()
        assert df.empty


# ---------------------------------------------------------------------------
# extract_vwo_experiments
# ---------------------------------------------------------------------------

def test_extract_vwo_experiments_returns_dataframe(tmp_path, mocker):
    """Should return a DataFrame when the CSV exists."""
    csv_content = "email_hash,experiment_id,variant_name\nuser1,EXP-001,Control\n"
    (tmp_path / "vwo_experiments.csv").write_text(csv_content)
    mocker.patch("os.path.exists", return_value=True)
    r = CRMDataReconciliator(str(tmp_path))
    df = r.extract_vwo_experiments()
    assert not df.empty

def test_extract_vwo_experiments_missing_file(mock_dir):
    """Should return an empty DataFrame if file is missing."""
    with patch("os.path.exists", side_effect=lambda p: p == "/mock/dir"):
        r = CRMDataReconciliator("/mock/dir")
        df = r.extract_vwo_experiments()
        assert df.empty


# ---------------------------------------------------------------------------
# extract_salesforce_opportunities
# ---------------------------------------------------------------------------

def test_extract_salesforce_opportunities_returns_dataframe(tmp_path, mocker):
    """Should return a DataFrame when the CSV exists."""
    csv_content = "email_hash,opportunity_stage\nuser1,Closed Won\n"
    (tmp_path / "salesforce_deals.csv").write_text(csv_content)
    mocker.patch("os.path.exists", return_value=True)
    r = CRMDataReconciliator(str(tmp_path))
    df = r.extract_salesforce_opportunities()
    assert not df.empty

def test_extract_salesforce_missing_file(mock_dir):
    """Should return an empty DataFrame if file is missing."""
    with patch("os.path.exists", side_effect=lambda p: p == "/mock/dir"):
        r = CRMDataReconciliator("/mock/dir")
        df = r.extract_salesforce_opportunities()
        assert df.empty


# ---------------------------------------------------------------------------
# reconcile_data: Missing tracking parameters
# ---------------------------------------------------------------------------

def test_reconcile_warns_on_missing_acquisition_source(
    mocker, mock_dir, hubspot_missing_source, vwo_clean, salesforce_full
):
    """Should log a warning when acquisition_source is null."""
    r = CRMDataReconciliator(mock_dir)
    mock_warn = mocker.patch("scripts.data_reconciliation.logger.warning")
    r.reconcile_data(hubspot_missing_source, salesforce_full, vwo_clean)
    assert mock_warn.called
    assert "missing tracking parameters" in mock_warn.call_args[0][0]

def test_reconcile_warns_on_missing_experiment_id(
    mocker, mock_dir, hubspot_clean, vwo_missing_experiment, salesforce_full
):
    """Should log a warning when experiment_id is null after left join."""
    r = CRMDataReconciliator(mock_dir)
    mock_warn = mocker.patch("scripts.data_reconciliation.logger.warning")
    r.reconcile_data(hubspot_clean, salesforce_full, vwo_missing_experiment)
    assert mock_warn.called

def test_reconcile_no_warnings_on_clean_data(
    mocker, mock_dir, hubspot_clean, vwo_clean, salesforce_full
):
    """Should NOT log a warning when all tracking parameters are present."""
    r = CRMDataReconciliator(mock_dir)
    mock_warn = mocker.patch("scripts.data_reconciliation.logger.warning")
    r.reconcile_data(hubspot_clean, salesforce_full, vwo_clean)
    assert not mock_warn.called


# ---------------------------------------------------------------------------
# reconcile_data: Orphan detection
# ---------------------------------------------------------------------------

def test_reconcile_detects_orphan_records(
    mocker, mock_dir, hubspot_clean, vwo_clean, salesforce_partial
):
    """Should log an error for leads present in HubSpot but absent from Salesforce."""
    r = CRMDataReconciliator(mock_dir)
    mock_error = mocker.patch("scripts.data_reconciliation.logger.error")
    r.reconcile_data(hubspot_clean, salesforce_partial, vwo_clean)
    assert mock_error.called
    # user2 is the orphan
    all_error_messages = " ".join(str(c) for c in mock_error.call_args_list)
    assert "user2" in all_error_messages

def test_reconcile_no_errors_when_all_matched(
    mocker, mock_dir, hubspot_clean, vwo_clean, salesforce_full
):
    """Should NOT log an error when every HubSpot lead exists in Salesforce."""
    r = CRMDataReconciliator(mock_dir)
    mock_error = mocker.patch("scripts.data_reconciliation.logger.error")
    r.reconcile_data(hubspot_clean, salesforce_full, vwo_clean)
    assert not mock_error.called


# ---------------------------------------------------------------------------
# reconcile_data: Empty data edge cases
# ---------------------------------------------------------------------------

def test_reconcile_handles_empty_hubspot(mocker, mock_dir, salesforce_full, vwo_clean):
    """Should not crash when HubSpot DataFrame is empty."""
    r = CRMDataReconciliator(mock_dir)
    empty_df = pd.DataFrame(columns=["email_hash", "acquisition_source"])
    mocker.patch("scripts.data_reconciliation.logger.warning")
    mocker.patch("scripts.data_reconciliation.logger.error")
    r.reconcile_data(empty_df, salesforce_full, vwo_clean)  # Should not raise

def test_reconcile_handles_empty_salesforce(mocker, mock_dir, hubspot_clean, vwo_clean):
    """All HubSpot leads should be flagged as orphans when Salesforce is empty."""
    r = CRMDataReconciliator(mock_dir)
    empty_sf = pd.DataFrame(columns=["email_hash", "opportunity_stage"])
    mock_error = mocker.patch("scripts.data_reconciliation.logger.error")
    mocker.patch("scripts.data_reconciliation.logger.warning")
    r.reconcile_data(hubspot_clean, empty_sf, vwo_clean)
    assert mock_error.called


# ---------------------------------------------------------------------------
# run(): Integration
# ---------------------------------------------------------------------------

def test_run_calls_all_extract_and_reconcile(mocker, mock_dir):
    """run() should call all three extractors and then reconcile."""
    r = CRMDataReconciliator(mock_dir)
    mock_hs = mocker.patch.object(r, "extract_hubspot_leads", return_value=pd.DataFrame())
    mock_vwo = mocker.patch.object(r, "extract_vwo_experiments", return_value=pd.DataFrame())
    mock_sf = mocker.patch.object(r, "extract_salesforce_opportunities", return_value=pd.DataFrame())
    mock_reconcile = mocker.patch.object(r, "reconcile_data")
    r.run()
    mock_hs.assert_called_once()
    mock_vwo.assert_called_once()
    mock_sf.assert_called_once()
    mock_reconcile.assert_called_once()

def test_run_exits_on_exception(mocker, mock_dir):
    """run() should call sys.exit(1) if an unexpected exception occurs."""
    r = CRMDataReconciliator(mock_dir)
    mocker.patch.object(r, "extract_hubspot_leads", side_effect=RuntimeError("boom"))
    mock_exit = mocker.patch("sys.exit")
    r.run()
    mock_exit.assert_called_once_with(1)
