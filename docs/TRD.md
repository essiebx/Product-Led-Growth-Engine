# Technical Requirements Document (TRD)

## 1. System Architecture
Data flows sequentially across platforms using `email_hash` or `user_id` as the primary key:
`HubSpot (Lead Capture) -> VWO (Variant Assignment) -> Salesforce (Deal State) -> DuckDB (Storage) -> dbt (Transform) -> Tableau (Unified Reporting)`

## 2. Data Pipeline Specifications

* **Ingestion:** Local synthetically generated CSV datasets (`data/hubspot_leads.csv`, `data/salesforce_deals.csv`, `data/vwo_experiments.csv`) loaded via `scripts/ingest_to_duckdb.py` using `pandas.read_csv()` and persisted to a local DuckDB database (`plg_engine.duckdb`).
* **Storage:** DuckDB (`plg_engine.duckdb`) acts as the local analytical database. Scalable to PostgreSQL or a cloud warehouse (e.g., BigQuery, Snowflake) for production.
* **Transformation:** dbt Core (`dbt/`) runs SQL models against DuckDB to clean, join, and aggregate data. Both `dbt run` and `dbt test` execute in CI.
* **Visualization:** Tableau ingests the exported CSV (`scripts/export_to_tableau.py`) mapped to the workbook schema defined in `tableau/workbook_schema.json`.
* **Alerting Mechanism:** Direct integration with `slack_sdk` to push statistically significant experiment signals to the Growth Squad channel.

## 3. Key Data Fields Strategy

| Field Name | Source System | Data Type | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | HubSpot / Product | String | Primary global key |
| `email_hash` | HubSpot | String | Privacy-centric key mapping HubSpot <-> Salesforce |
| `cta_first_click_at` | HubSpot | Timestamp | First touchpoint timestamp |
| `vwo_experiment_id` | VWO | String | Variant ID assigned on landing page |
| `trial_activated_at` | Product Analytics | Timestamp | Marked when user hits activation milestone |
| `sf_opportunity_stage` | Salesforce | String | Current CRM pipeline stage |

## 4. Error Handling & Data Quality Controls
* Automated script (`scripts/data_reconciliation.py`) executes daily at 02:00 UTC via GitHub Actions.
* Checks for orphan records (e.g., Salesforce deal exists with no corresponding HubSpot contact) and missing parameters (e.g. `utm_source`).
* Any errors in workflow connections return `sys.exit(1)` keeping CI/CD pipelines aware of silent failures.
* Alert script (`scripts/experiment_alerts.py`) fetches all active campaigns and validates against conversion rates, triggering Slack only if statistical significance is met.

## 5. Testing Strategy
* **Framework:** pytest with pytest-mock. All 43 tests are fully mocked — no live API calls or credentials required.
* **Test Discovery:** `pytest.ini` sets `testpaths = tests` and `pythonpath = .` so `scripts/` imports resolve correctly.
* **Shared Fixtures:** `conftest.py` inserts the project root into `sys.path` for both the terminal runner and VS Code language server.
* **Coverage:**

| Script | Test File | Scenarios Covered |
| :--- | :--- | :--- |
| `data_reconciliation.py` | `test_data_reconciliation.py` | Lead matching, orphan detection, UTM field validation, exit codes |
| `experiment_alerts.py` | `test_experiment_alerts.py` | VWO API responses, significance thresholds, Slack dispatch |
| `ingest_to_duckdb.py` | `test_ingest_to_duckdb.py` | DuckDB writes, schema checks, empty data handling |
| `export_to_tableau.py` | `test_export_to_tableau.py` | CSV output, success/failure logging |

## 6. IDE & Developer Tooling
* `.vscode/settings.json` configures Pylance with `python.analysis.extraPaths` pointing to both system-level and user-level `site-packages`, eliminating false-positive `Cannot find module` warnings for packages like `pytest` and `duckdb`.
* `python.analysis.diagnosticSeverityOverrides` suppresses `reportMissingModuleSource` to prevent noise from packages that ship without bundled type stubs.