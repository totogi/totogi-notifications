import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def handler(event, context):
    print("Event: " + str(event))
    if event_is_threshold(event):
        handle_threshold(event)


def handle_threshold(threshold_event):
    provider_id: str = threshold_event['detail']['provider']
    account_id: str = threshold_event['detail']['account']
    counter_type: str = threshold_event['detail']['counter']
    
    if counter_type == 'AllowanceThresholdVoice':
        record_notification('voice', account_id, provider_id)
    if counter_type == 'AllowanceThresholdText':
        record_notification('text', account_id, provider_id)
    if counter_type == 'AllowanceThresholdData':
        record_notification('data', account_id, provider_id)


def event_is_threshold(event) -> bool:
    detail = event.get('detail', {})
    counter_type = detail.get('counter', '')
    state = detail.get('state', '')
    if 'AllowanceThreshold' in counter_type and state == 'low':
        return True
    return False


def record_notification(threshold_type: str, account: str, provider: str):
    print('Recording notification for ' + threshold_type + ' for account ' + account)
    message = f'NOTIFICATION: The  {threshold_type} balance is low.'
    now = datetime.now()
    now_timestamp = now.isoformat()[:-4]+'Z'
    now_epoch = int(now.timestamp())
    item = {
        'pk': f'PROVIDER#{provider}#ACCOUNT#{account}',
        'sk': 'TYPE#THRESHOLD#TIMESTAMP#' + now_timestamp,
        'message': message,
        'thresholdType': threshold_type,
        'timestamp': now_timestamp,
        'expireAtEpochSeconds': now_epoch + DAY * 30
    }
    table.put_item(Item=item)
