import boto3
from datetime import datetime, timedelta, timezone
from config import *

ec2 = boto3.client("ec2")
cw = boto3.client("cloudwatch")

def _tags(obj):
    return {t["Key"]: t["Value"] for t in obj.get("Tags", [])}

def find_orphaned_volumes():
    found = []
    pages = ec2.get_paginator("describe_volumes").paginate(
        Filters=[{"Name": "status", "Values": ["available"]}])
    for page in pages:
        for v in page["Volumes"]:
            found.append({
                "type": "ebs", "id": v["VolumeId"],
                "detail": f'{v["Size"]} GB {v["VolumeType"]}, unattached',
                "monthly_cost": round(v["Size"] * EBS_PRICE_GB_MONTH, 2),
                "tags": _tags(v)})
    return found

def find_unattached_eips():
    found = []
    for a in ec2.describe_addresses()["Addresses"]:
        if "AssociationId" not in a:
            found.append({
                "type": "eip", "id": a["AllocationId"],
                "detail": f'{a["PublicIp"]}, not associated',
                "monthly_cost": EIP_PRICE_MONTH, "tags": _tags(a)})
    return found

def find_idle_instances():
    found = []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=IDLE_LOOKBACK_DAYS)
    pages = ec2.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
    for page in pages:
        for res in page["Reservations"]:
            for i in res["Instances"]:
                stats = cw.get_metric_statistics(
                    Namespace="AWS/EC2", MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": i["InstanceId"]}],
                    StartTime=start, EndTime=end, Period=86400,
                    Statistics=["Average"])["Datapoints"]
                if stats and max(d["Average"] for d in stats) < CPU_IDLE_THRESHOLD:
                    price = EC2_PRICE_HOUR.get(i["InstanceType"], 0.02)
                    found.append({
                        "type": "ec2", "id": i["InstanceId"],
                        "detail": f'{i["InstanceType"]}, CPU under {CPU_IDLE_THRESHOLD}% for {IDLE_LOOKBACK_DAYS}d',
                        "monthly_cost": round(price * 730, 2),
                        "tags": _tags(i)})
    return found