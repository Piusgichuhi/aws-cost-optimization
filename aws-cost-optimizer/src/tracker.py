import boto3
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Attr
from config import TABLE_NAME, GRACE_DAYS

table = boto3.resource("dynamodb").Table(TABLE_NAME)

def track_first_seen(resource):
    item = table.get_item(Key={"resource_id": resource["id"]}).get("Item")
    if item and item.get("status") == "flagged":
        return item
    item = {"resource_id": resource["id"], "type": resource["type"],
            "status": "flagged",
            "first_seen": datetime.now(timezone.utc).isoformat()}
    table.put_item(Item=item)
    return item

def past_grace(item):
    first = datetime.fromisoformat(item["first_seen"])
    return datetime.now(timezone.utc) - first >= timedelta(days=GRACE_DAYS)

def mark_deleted(resource_id):
    table.update_item(Key={"resource_id": resource_id},
        UpdateExpression="SET #s = :d, deleted_at = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":d": "deleted",
            ":t": datetime.now(timezone.utc).isoformat()})

def clear_resolved(current_ids):
    resp = table.scan(FilterExpression=Attr("status").eq("flagged"))
    for it in resp["Items"]:
        if it["resource_id"] not in current_ids:
            table.delete_item(Key={"resource_id": it["resource_id"]})