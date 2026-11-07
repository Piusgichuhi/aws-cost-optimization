import boto3
from config import TOPIC_ARN, DRY_RUN, GRACE_DAYS

sns = boto3.client("sns")

def _section(title, items):
    if not items:
        return ""
    lines = [f"### {title}", "| Type | ID | Detail | $/month |", "|---|---|---|---|"]
    for r in items:
        lines.append(f'| {r["type"]} | {r["id"]} | {r["detail"]} | ${r["monthly_cost"]:.2f} |')
    return "\n".join(lines) + "\n\n"

def build_report(flagged, deleted, exempt):
    at_risk = sum(r["monthly_cost"] for r in flagged)
    saved = sum(r["monthly_cost"] for r in deleted)
    mode = "DRY RUN (nothing deleted)" if DRY_RUN else "LIVE"
    return (f"# Daily AWS cost report [{mode}]\n\n"
            f"Potential savings: ${at_risk:.2f}/month. "
            f"Saved today: ${saved:.2f}/month.\n"
            f"Flagged resources are cleaned after {GRACE_DAYS} days unless exempted.\n\n"
            + _section("Flagged (grace period running)", flagged)
            + _section("Cleaned up today", deleted)
            + _section("Exempt (skipped)", exempt))

def send_report(body):
    sns.publish(TopicArn=TOPIC_ARN, Subject="Daily AWS cost report", Message=body)