# PLG Free Trial Optimization & Experimentation Engine

An end-to-end operational framework designed to track free trial leads from first CTA click to Product Qualified Lead (PQL) status, monitor live A/B experiments, and automate data hygiene checks across CRM, product, and analytics stacks.

## Stack Integration
* **Data Sources & CRM:** HubSpot, Salesforce
* **Experimentation:** VWO / Wingify
* **Visualization:** Tableau
* **Automation:** Python, GitHub Actions
* **Docs & Qualitative Data:** Markdown, Notion
* **Alerts:** Slack

## Repository Structure
* `.github/workflows/`: GitHub actions for scheduled daily runs.
* `data/`: Local synthetic CSV datasets (HubSpot, VWO, Salesforce) to respect PII compliance.
* `docs/`: Product Requirements Document (PRD) and Technical Requirements Document (TRD).
* `scripts/`: Automated Python pipelines for data reconciliation (using local CSVs) and experiment alerting.
* `tableau/`: Field mapping and workbook structural specs.
* `templates/`: Structured frameworks for user interview summaries and weekly squad syncs.

## Quick Start

1. **Clone the repository and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Copy `.env.example` to `.env` and fill in API keys for HubSpot, Salesforce, VWO, and Slack.
   ```bash
   cp .env.example .env
   # Edit .env with your favorite text editor
   ```

3. **Run the data reconciliation script:**
   Validates lead flow from HubSpot to Salesforce and spots missing parameters.
   ```bash
   python scripts/data_reconciliation.py
   ```

4. **Run the experiment alerts script:**
   Checks VWO for statistical significance and triggers Slack alerts for the Growth Squad.
   ```bash
   python scripts/experiment_alerts.py
   ```

## CI/CD and Automation
The project includes a GitHub Action (`data-quality-check.yml`) configured to run every day at 02:00 UTC. Ensure to export your API keys into the GitHub Repository Secrets to properly utilize this workflow.
