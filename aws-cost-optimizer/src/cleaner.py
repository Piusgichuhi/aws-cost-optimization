import boto3
from config import DRY_RUN

ec2 = boto3.client("ec2")

def clean_resource(r):
    if DRY_RUN:
        return "dry-run"
    if r["type"] == "ebs":
        ec2.delete_volume(VolumeId=r["id"])
    elif r["type"] == "eip":
        ec2.release_address(AllocationId=r["id"])
    elif r["type"] == "ec2":
        ec2.stop_instances(InstanceIds=[r["id"]])
    return "done"