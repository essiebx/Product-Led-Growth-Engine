import os
import sys
import logging
import pandas as pd

# Initialize basic configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class CRMDataReconciliator:
    """
    Reconciles data between HubSpot and Salesforce to ensure no trial data is dropped.
    Utilizes local synthetic CSV data to comply with PII and API constraints.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            logger.error(f"Data directory '{self.data_dir}' not found.")
            sys.exit(1)

    def extract_hubspot_leads(self) -> pd.DataFrame:
        """Extracts trial leads from synthetic HubSpot data."""
        logger.info("Extracting data from local HubSpot CSV...")
        hs_path = os.path.join(self.data_dir, "hubspot_leads.csv")
        return pd.read_csv(hs_path) if os.path.exists(hs_path) else pd.DataFrame()

    def extract_vwo_experiments(self) -> pd.DataFrame:
        """Extracts experiment data from synthetic VWO data."""
        logger.info("Extracting data from local VWO CSV...")
        vwo_path = os.path.join(self.data_dir, "vwo_experiments.csv")
        return pd.read_csv(vwo_path) if os.path.exists(vwo_path) else pd.DataFrame()

    def extract_salesforce_opportunities(self) -> pd.DataFrame:
        """Extracts current opportunities from synthetic Salesforce data."""
        logger.info("Extracting data from local Salesforce CSV...")
        sf_path = os.path.join(self.data_dir, "salesforce_deals.csv")
        return pd.read_csv(sf_path) if os.path.exists(sf_path) else pd.DataFrame()

    def reconcile_data(self, hubspot_df: pd.DataFrame, sf_df: pd.DataFrame, vwo_df: pd.DataFrame) -> None:
        """Finds orphans and data quality issues."""
        logger.info("Reconciling HubSpot, Salesforce, and VWO data...")
        
        # Merge HubSpot with VWO
        hs_vwo_merged = pd.merge(hubspot_df, vwo_df, on="email_hash", how="left")

        # Checking for missing UTM/Acquisition or Experiment variables
        missing_params = hs_vwo_merged[
            hs_vwo_merged['acquisition_source'].isna() | hs_vwo_merged['experiment_id'].isna()
        ]
        
        if not missing_params.empty:
            logger.warning(f"Found {len(missing_params)} leads with missing tracking parameters (Acquisition Source or VWO Experiment ID).")
        
        # Checking for orphans: in HubSpot but not in Salesforce
        merged = pd.merge(hs_vwo_merged, sf_df, on="email_hash", how="left", indicator=True)
        orphan_in_hubspot = merged[merged['_merge'] == 'left_only']
        
        if not orphan_in_hubspot.empty:
            logger.error(f"Data Sync Issue: {len(orphan_in_hubspot)} HubSpot records missing in Salesforce.")
            for _, row in orphan_in_hubspot.iterrows():
                logger.error(f"  - Missing SF Record for hash: {row['email_hash']}")
            
        logger.info("Data reconciliation completed.")

    def run(self):
        try:
            hs_data = self.extract_hubspot_leads()
            vwo_data = self.extract_vwo_experiments()
            sf_data = self.extract_salesforce_opportunities()
            self.reconcile_data(hs_data, sf_data, vwo_data)
        except Exception:
            logger.exception("An error occurred during data reconciliation.")
            sys.exit(1)

if __name__ == "__main__":
    # Resolve the data directory relative to this script
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    
    reconciliator = CRMDataReconciliator(data_dir)
    reconciliator.run()
