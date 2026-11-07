import boto3
from config import TABLE_NAME

table = boto3.resource("dynamodb").Table(TABLE_NAME)

def is_exempt(resource):
    if resource["tags"].get("cost-optimizer", "").lower() == "exempt":
        return True
    item = table.get_item(Key={"resource_id": resource["id"]}).get("Item")
    return bool(item and item.get("status") == "exempt")