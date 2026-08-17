import pytest
import os
from scripts.experiment_alerts import ExperimentAlertManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://mock-webhook-url.com")

@pytest.fixture
def stat_sig_experiment():
    return {
        "id": "EXP-1", "name": "EXP-1 - Variant A", "stat_sig": True,
        "control_conv_rate": 0.10, "variant_conv_rate": 0.20, "lift": "+100.0%"
    }

@pytest.fixture
def non_stat_sig_experiment():
    return {
        "id": "EXP-2", "name": "EXP-2 - Variant B", "stat_sig": False,
        "control_conv_rate": 0.10, "variant_conv_rate": 0.11, "lift": "+10.0%"
    }

@pytest.fixture
def mixed_experiment_data(stat_sig_experiment, non_stat_sig_experiment):
    return {"experiments": [stat_sig_experiment, non_stat_sig_experiment]}


# ---------------------------------------------------------------------------
# __init__: Constructor / Environment validation
# ---------------------------------------------------------------------------

def test_init_exits_on_missing_env_var(monkeypatch):
    """Constructor should call sys.exit(1) when SLACK_WEBHOOK_URL is missing."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    import sys
    with pytest.raises(SystemExit) as exc_info:
        ExperimentAlertManager()
    assert exc_info.value.code == 1

def test_init_sets_webhook_url(mock_env):
    """Constructor should correctly store the SLACK_WEBHOOK_URL."""
    manager = ExperimentAlertManager()
    assert manager.slack_webhook_url == "http://mock-webhook-url.com"


# ---------------------------------------------------------------------------
# evaluate_and_alert: Alerting logic
# ---------------------------------------------------------------------------

def test_evaluate_alerts_only_stat_sig_experiments(mocker, mock_env, mixed_experiment_data):
    """Should only fire an alert for experiments where stat_sig is True."""
    manager = ExperimentAlertManager()
    mock_alert = mocker.patch.object(manager, "_send_slack_alert")
    manager.evaluate_and_alert(mixed_experiment_data)
    mock_alert.assert_called_once()
    assert mock_alert.call_args[0][0]["id"] == "EXP-1"

def test_evaluate_sends_no_alerts_when_none_stat_sig(mocker, mock_env, non_stat_sig_experiment):
    """Should send no alerts when no experiments have reached stat sig."""
    manager = ExperimentAlertManager()
    mock_alert = mocker.patch.object(manager, "_send_slack_alert")
    manager.evaluate_and_alert({"experiments": [non_stat_sig_experiment]})
    mock_alert.assert_not_called()

def test_evaluate_sends_multiple_alerts(mocker, mock_env, stat_sig_experiment):
    """Should fire one alert per stat sig experiment when multiple win."""
    manager = ExperimentAlertManager()
    mock_alert = mocker.patch.object(manager, "_send_slack_alert")
    second_winner = {**stat_sig_experiment, "id": "EXP-5", "name": "EXP-5 - Variant C"}
    manager.evaluate_and_alert({"experiments": [stat_sig_experiment, second_winner]})
    assert mock_alert.call_count == 2

def test_evaluate_handles_empty_experiment_list(mocker, mock_env):
    """Should gracefully handle an empty experiments list without crashing."""
    manager = ExperimentAlertManager()
    mock_alert = mocker.patch.object(manager, "_send_slack_alert")
    manager.evaluate_and_alert({"experiments": []})
    mock_alert.assert_not_called()

def test_evaluate_handles_missing_experiments_key(mocker, mock_env):
    """Should gracefully handle a payload with no 'experiments' key."""
    manager = ExperimentAlertManager()
    mock_alert = mocker.patch.object(manager, "_send_slack_alert")
    manager.evaluate_and_alert({})
    mock_alert.assert_not_called()


# ---------------------------------------------------------------------------
# _send_slack_alert: HTTP request
# ---------------------------------------------------------------------------

def test_send_slack_alert_posts_to_correct_url(mocker, mock_env, stat_sig_experiment):
    """Should POST to the configured Slack webhook URL."""
    manager = ExperimentAlertManager()
    mock_post = mocker.patch("scripts.experiment_alerts.requests.post")
    mock_post.return_value.raise_for_status = lambda: None
    manager._send_slack_alert(stat_sig_experiment)
    mock_post.assert_called_once()
    assert mock_post.call_args[0][0] == "http://mock-webhook-url.com"

def test_send_slack_alert_message_contains_experiment_name(mocker, mock_env, stat_sig_experiment):
    """Slack message text should include the experiment name."""
    manager = ExperimentAlertManager()
    mock_post = mocker.patch("scripts.experiment_alerts.requests.post")
    mock_post.return_value.raise_for_status = lambda: None
    manager._send_slack_alert(stat_sig_experiment)
    payload = mock_post.call_args[1]["json"]
    assert "Variant A" in payload["text"]

def test_send_slack_alert_message_contains_lift(mocker, mock_env, stat_sig_experiment):
    """Slack message text should include the lift figure."""
    manager = ExperimentAlertManager()
    mock_post = mocker.patch("scripts.experiment_alerts.requests.post")
    mock_post.return_value.raise_for_status = lambda: None
    manager._send_slack_alert(stat_sig_experiment)
    payload = mock_post.call_args[1]["json"]
    assert "+100.0%" in payload["text"]

def test_send_slack_alert_handles_request_exception(mocker, mock_env, stat_sig_experiment):
    """Should log an error but not crash when the HTTP request fails."""
    import requests as req
    manager = ExperimentAlertManager()
    mocker.patch("scripts.experiment_alerts.requests.post",
                 side_effect=req.exceptions.ConnectionError("connection refused"))
    mock_logger_error = mocker.patch("scripts.experiment_alerts.logger.error")
    manager._send_slack_alert(stat_sig_experiment)  # Should not raise
    assert mock_logger_error.called


# ---------------------------------------------------------------------------
# fetch_active_experiments: DuckDB integration
# ---------------------------------------------------------------------------

def test_fetch_returns_empty_when_db_missing(mocker, mock_env):
    """Should return empty experiments payload when plg_engine.duckdb doesn't exist."""
    manager = ExperimentAlertManager()
    mocker.patch("os.path.exists", return_value=False)
    result = manager.fetch_active_experiments()
    assert result == {"experiments": []}

def test_fetch_returns_empty_on_db_error(mocker, mock_env):
    """Should return empty experiments payload on database query failure."""
    manager = ExperimentAlertManager()
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("duckdb.connect", side_effect=Exception("DB error"))
    result = manager.fetch_active_experiments()
    assert result == {"experiments": []}


# ---------------------------------------------------------------------------
# run(): Integration
# ---------------------------------------------------------------------------

def test_run_calls_fetch_and_evaluate(mocker, mock_env):
    """run() should call fetch_active_experiments and evaluate_and_alert."""
    manager = ExperimentAlertManager()
    mock_fetch = mocker.patch.object(manager, "fetch_active_experiments",
                                     return_value={"experiments": []})
    mock_eval = mocker.patch.object(manager, "evaluate_and_alert")
    manager.run()
    mock_fetch.assert_called_once()
    mock_eval.assert_called_once()

def test_run_exits_on_unexpected_exception(mocker, mock_env):
    """run() should call sys.exit(1) on an unexpected error."""
    manager = ExperimentAlertManager()
    mocker.patch.object(manager, "fetch_active_experiments",
                        side_effect=RuntimeError("unexpected!"))
    mock_exit = mocker.patch("sys.exit")
    manager.run()
    mock_exit.assert_called_once_with(1)
