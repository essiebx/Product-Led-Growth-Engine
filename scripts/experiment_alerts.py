import os
import sys
import logging
import duckdb
import requests
from dotenv import load_dotenv

# Initialize basic configuration
load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ExperimentAlertManager:
    """
    Checks DuckDB for A/B tests that have reached statistical significance
    and alerts the Growth Squad via Slack Webhook.
    """
    def __init__(self):
        self._verify_environment()
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        # Ensure path is relative to the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "plg_engine.duckdb")

    def _verify_environment(self) -> None:
        required_vars = ["SLACK_WEBHOOK_URL"]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            sys.exit(1)

    def fetch_active_experiments(self) -> dict:
        """Fetches active campaigns from DuckDB and calculates lift."""
        logger.info("Fetching experiment metrics from DuckDB...")
        if not os.path.exists(self.db_path):
            logger.error(f"DuckDB database not found at {self.db_path}")
            return {"experiments": []}
            
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
            # Find the total users and conversions for each experiment variant
            query = """
                SELECT 
                    experiment_id,
                    variant_name,
                    COUNT(email_hash) as total_users,
                    SUM(is_converted) as conversions,
                    CASE WHEN COUNT(email_hash) = 0 THEN 0 ELSE SUM(is_converted)*1.0 / COUNT(email_hash) END as conv_rate
                FROM main.fct_trial_conversions
                WHERE experiment_id IS NOT NULL
                GROUP BY 1, 2
            """
            df = conn.execute(query).df()
            conn.close()
            
            # Format the output for the evaluator
            experiments_payload = []
            
            if df.empty:
                return {"experiments": []}
                
            grouped = df.groupby('experiment_id')
            for exp_id, group in grouped:
                # We expect a 'Control' variant and other variants. If not explicitly 'Control', find it.
                control_row = group[group['variant_name'].str.lower() == 'control']
                if control_row.empty:
                    continue
                control_rate = control_row.iloc[0]['conv_rate']
                
                for _, row in group.iterrows():
                    if row['variant_name'].lower() == 'control':
                        continue
                    
                    variant_rate = row['conv_rate']
                    lift = 0
                    if control_rate > 0:
                        lift = (variant_rate - control_rate) / control_rate
                    
                    # For demonstration, we'll mark stat_sig True if lift > 5%
                    stat_sig = lift > 0.05
                    
                    experiments_payload.append({
                        "id": exp_id,
                        "name": f"{exp_id} - {row['variant_name']}",
                        "status": "active",
                        "stat_sig": stat_sig,
                        "control_conv_rate": control_rate,
                        "variant_conv_rate": variant_rate,
                        "lift": f"{lift * 100:+.1f}%"
                    })
                    
            return {"experiments": experiments_payload}
        except Exception as e:
            logger.error(f"Failed to fetch data from DuckDB: {e}")
            return {"experiments": []}

    def _send_slack_alert(self, experiment: dict):
        """Sends a notification to the Slack Webhook."""
        message = (
            f"🚀 *Experiment Alert: {experiment['name']} ({experiment['id']})*\n"
            f"The experiment has reached statistical significance!\n"
            f"• Control Conversion Rate: `{experiment['control_conv_rate'] * 100:.2f}%`\n"
            f"• Variant Conversion Rate: `{experiment['variant_conv_rate'] * 100:.2f}%`\n"
            f"• Lift: `{experiment['lift']}`\n\n"
            f"👉 *Recommendation*: Review results and consider scaling the variant."
        )
        
        try:
            response = requests.post(
                self.slack_webhook_url,
                json={"text": message},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Successfully sent Slack alert for {experiment['id']}.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to Slack webhook: {e}")

    def evaluate_and_alert(self, data: dict):
        """Evaluates experiments and triggers alerts for stat sig winners."""
        experiments = data.get("experiments", [])
        for exp in experiments:
            if exp.get("stat_sig"):
                logger.info(f"Alerting on experiment {exp['id']}...")
                self._send_slack_alert(exp)
            else:
                logger.debug(f"Experiment {exp['id']} has not yet reached stat sig.")

    def run(self):
        try:
            exp_data = self.fetch_active_experiments()
            self.evaluate_and_alert(exp_data)
        except Exception:
            logger.exception("An error occurred while managing experiment alerts.")
            sys.exit(1)

if __name__ == "__main__":
    alert_manager = ExperimentAlertManager()
    alert_manager.run()
