import os

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
GRACE_DAYS = int(os.environ.get("GRACE_DAYS", "7"))
CPU_IDLE_THRESHOLD = float(os.environ.get("CPU_IDLE_THRESHOLD", "5"))
IDLE_LOOKBACK_DAYS = int(os.environ.get("IDLE_LOOKBACK_DAYS", "7"))
TABLE_NAME = os.environ.get("TABLE_NAME", "")
TOPIC_ARN = os.environ.get("TOPIC_ARN", "")

EBS_PRICE_GB_MONTH = 0.08   # approx gp3, us-east-1
EIP_PRICE_MONTH = 3.65      # approx idle public IPv4
EC2_PRICE_HOUR = {"t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416}