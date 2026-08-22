import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dirty_data.ingest import ingest_raw_data
from dirty_data.detect import detect_anomalies, generate_anomaly_report
import os

if __name__ == "__main__":
    df = ingest_raw_data("data/raw/case-export-2023-2025.csv")
    anomalies = detect_anomalies(df)
    report_df = generate_anomaly_report(anomalies)
    
    os.makedirs("outputs", exist_ok=True)
    report_df.to_csv("outputs/phase2_anomaly_report.csv", index=False)
