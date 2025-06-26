import boto3
from datetime import datetime, timedelta
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('matriculas')

def save_plate_to_db(plate_text):
    plate_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    if not check_plate_exists(plate_text, period_s=60):
        print(f"Plate {plate_text} does not exist in the database, saving it.")
        table.put_item(Item={
            'id_matricula': plate_id,
            'texto_matricula': plate_text,
            'timestamp': timestamp
        })
    else:
        print(f"Skip {plate_text} (detected within the last 60 seconds).")

def check_plate_exists(plate_text, period_s: int):
    """
    Check if a plate exists in the database within a specified period in seconds.
    Returns True if the plate exists, False otherwise.
    """
    timestamp_limit = (datetime.now() - timedelta(seconds=period_s)).isoformat()
    response = table.query(
        IndexName='texto_matricula-timestamp-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('texto_matricula').eq(plate_text) &
                               boto3.dynamodb.conditions.Key('timestamp').gt(timestamp_limit)
    )
    
    return len(response['Items']) > 0