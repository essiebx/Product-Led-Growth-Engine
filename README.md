# PLG(product led growth) Trial Optimization & Experimentation Engine

An end-to-end operational framework designed to track free trial leads from first CTA click to Product Qualified Lead (PQL) status, monitor live A/B experiments, and automate data hygiene checks across CRM, product, and analytics stacks.

## Stack Integration
* **Data Sources & CRM:** HubSpot, Salesforce
* **Experimentation:** VWO / Wingify
* **Storage & Processing:** DuckDB, dbt Core
* **Visualization:** Tableau
* **Automation:** Python, GitHub Actions
* **Testing:** pytest, pytest-mock
* **Docs & Qualitative Data:** Markdown, Notion
* **Alerts:** Slack

## Repository Structure
* `.github/workflows/`: GitHub Actions for scheduled daily runs (`data-quality-check.yml`).
* `.vscode/`: Workspace settings for VS Code (Python interpreter, Pylance paths, pytest integration).
* `data/`: Local synthetic CSV datasets (HubSpot, VWO, Salesforce) to respect PII compliance.
* `docs/`: Product Requirements Document (PRD) and Technical Requirements Document (TRD).
* `dbt/`: dbt project for transforming raw ingested data inside DuckDB.
* `scripts/`: Automated Python pipelines:
  * `data_reconciliation.py` — validates lead flow from HubSpot to Salesforce, flags orphan records and missing UTM parameters.
  * `experiment_alerts.py` — checks VWO for statistical significance and triggers Slack alerts for the Growth Squad.
  * `ingest_to_duckdb.py` — loads synthetic CSV data into a local DuckDB database for dbt transformation.
  * `export_to_tableau.py` — exports transformed DuckDB data to a CSV for Tableau consumption.
* `tableau/`: Field mapping and workbook structural specs.
* `templates/`: Structured frameworks for user interview summaries and weekly squad syncs.
* `tests/`: Full pytest test suite (43 tests) covering all four scripts.
* `conftest.py`: Shared pytest configuration; ensures `scripts/` is importable from any test context.
* `pytest.ini`: Pytest settings (test discovery path, Python path).

## Quick Start

1. **Clone the repository and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Copy `.env.example` to `.env` and fill in API keys for HubSpot, Salesforce, VWO, and Slack.
   ```bash
   cp .env.example .env
   # Edit .env with your favourite text editor
   ```

3. **Ingest data into DuckDB:**
   Loads the synthetic CSVs from `data/` into a local `plg_engine.duckdb` database.
   ```bash
   python scripts/ingest_to_duckdb.py
   ```

4. **Run the dbt transformation pipeline:**
   ```bash
   dbt run --profiles-dir dbt --project-dir dbt
   dbt test --profiles-dir dbt --project-dir dbt
   ```

5. **Export data for Tableau:**
   Writes the transformed dataset from DuckDB to a CSV ready for Tableau ingestion.
   ```bash
   python scripts/export_to_tableau.py
   ```

6. **Run the data reconciliation script:**
   Validates lead flow from HubSpot to Salesforce and spots missing parameters.
   ```bash
   python scripts/data_reconciliation.py
   ```

7. **Run the experiment alerts script:**
   Checks VWO for statistical significance and triggers Slack alerts for the Growth Squad.
   ```bash
   python scripts/experiment_alerts.py
   ```

## Running Tests

The test suite uses `pytest` and `pytest-mock`. All 43 tests run against mocked external APIs, so no live credentials are required.

```bash
python -m pytest tests/ -v
```

| Test File | Script Covered | What's Tested |
|---|---|---|
| `test_data_reconciliation.py` | `data_reconciliation.py` | HubSpot/Salesforce lead matching, orphan detection, UTM validation |
| `test_experiment_alerts.py` | `experiment_alerts.py` | VWO API fetching, significance logic, Slack alert dispatch |
| `test_ingest_to_duckdb.py` | `ingest_to_duckdb.py` | DuckDB ingestion, schema validation, empty data handling |
| `test_export_to_tableau.py` | `export_to_tableau.py` | CSV export, logging, file output verification |

## VS Code Developer Setup

The `.vscode/settings.json` configures the workspace for Pylance and the built-in pytest runner:
* Points Pylance to the correct Python interpreter.
* Adds both system-level and user-level `site-packages` to `python.analysis.extraPaths` so imports like `pytest` and `duckdb` resolve in the IDE without false-positive warnings.
* Enables the pytest runner with `tests/` as the test root.

If you see a `Cannot find module 'pytest'` warning in VS Code, reload the window via `Ctrl+Shift+P` → **Developer: Reload Window**.

## CI/CD and Automation

The project includes a GitHub Action (`data-quality-check.yml`) that runs every day at **02:00 UTC** in this order:

1. Run pytest test suite
2. Ingest data to DuckDB
3. Run dbt pipeline (run + test)
4. Export data for Tableau
5. Run data reconciliation
6. Run experiment alerts

Export your API keys to **GitHub Repository Secrets** (`HUBSPOT_API_KEY`, `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, `SALESFORCE_SECURITY_TOKEN`, `VWO_API_KEY`, `VWO_ACCOUNT_ID`, `SLACK_WEBHOOK_URL`) to enable the live data steps. The workflow can also be triggered manually via **workflow_dispatch**.
