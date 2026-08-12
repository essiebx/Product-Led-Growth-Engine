import os
import sys
import logging
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize basic configuration
load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ExperimentAlertManager:
    """
    Checks VWO for A/B tests that have reached statistical significance
    and alerts the Growth Squad via Slack.
    """
    def __init__(self):
        self._verify_environment()
        self.slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.slack_channel = os.getenv("SLACK_CHANNEL_ID")
        self.vwo_api_key = os.getenv("VWO_API_KEY")
        self.vwo_account_id = os.getenv("VWO_ACCOUNT_ID")

    def _verify_environment(self) -> None:
        required_vars = ["VWO_API_KEY", "VWO_ACCOUNT_ID", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            sys.exit(1)

    def fetch_active_experiments(self) -> dict:
        """Fetches active campaigns from VWO API."""
        logger.info("Fetching experiment metrics from VWO...")
        
        # Mocking generic JSON payload for illustrative skeleton setup
        return {
            "experiments": [
                {
                    "id": "EXP-102",
                    "name": "Simplified Onboarding Step 2",
                    "status": "active",
                    "stat_sig": True,
                    "control_conv_rate": 0.15,
                    "variant_conv_rate": 0.234,
                    "lift": "+8.4%"
                },
                {
                    "id": "EXP-103",
                    "name": "Pricing Page Tooltip",
                    "status": "active",
                    "stat_sig": False,
                    "control_conv_rate": 0.05,
                    "variant_conv_rate": 0.051,
                    "lift": "+0.1%"
                }
            ]
        }

    def _send_slack_alert(self, experiment: dict):
        """Sends a notification to the Slack channel."""
        message = (
            f"🚀 *Experiment Alert: {experiment['name']} ({experiment['id']})*\n"
            f"The experiment has reached statistical significance!\n"
            f"• Control Conversion Rate: `{experiment['control_conv_rate'] * 100:.2f}%`\n"
            f"• Variant Conversion Rate: `{experiment['variant_conv_rate'] * 100:.2f}%`\n"
            f"• Lift: `{experiment['lift']}`\n\n"
            f"👉 *Recommendation*: Review results in VWO and consider scaling the variant."
        )
        
        try:
            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                text=message
            )
            logger.info(f"Successfully sent Slack alert for {experiment['id']}.")
        except SlackApiError as e:
            logger.error(f"Error sending message to Slack: {e.response['error']}")

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
