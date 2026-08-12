# Technical Requirements Document (TRD)

## 1. System Architecture
Data flows sequentially across platforms using `email_hash` or `user_id` as the primary key:
`HubSpot (Lead Capture) -> VWO (Variant Assignment) -> Salesforce (Deal State) -> Tableau (Unified Reporting)`

## 2. Data Pipeline Specifications
* **Ingestion:** Local synthetically generated CSV datasets (`data/hubspot_leads.csv`, `data/salesforce_deals.csv`, `data/vwo_experiments.csv`) loaded directly via `pandas.read_csv()` to circumvent live API limits.
* **Storage/Processing:** In-memory `pandas` dataframes for fast internal reconciliation of the CSVs. Scalable to PostgreSQL staging area for persistent queries.
* **Visualization:** Tableau Server mapped structure (`workbook_schema.json`), extracting via database connector.
* **Alerting Mechanism:** Direct integration with `slack_sdk` to push significant events.

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