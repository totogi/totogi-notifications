import os
import boto3
from datetime import datetime
import numbers

def is_number(value):
    return isinstance(value, numbers.Number)

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
    provider_id: str = threshold_event['detail']['providerid']
    account_id: str = threshold_event['detail']['eventdata']['accountid']
    counter_type: str = threshold_event['detail']['eventdata']['notificationinformation']['name']
    event_state = threshold_event['detail']['eventdata']['notificationinformation']['state']
    threshold = threshold_event['detail']['eventdata']['notificationinformation'].get('threshold')
    
    if 'AllowanceThresholdVoice' in counter_type or 'Voice Thresholds' in counter_type:
        message = f"voice {event_state}"
        try:
            if is_number(threshold):
                threshold /= 60
                message += f" {threshold} mins"
        except:
            print(f"Error processing threshold {threshold}")
        record_notification(message, account_id, provider_id)
    if 'AllowanceThresholdText' in counter_type or 'Text Thresholds' in counter_type:
        message = f"text {event_state}"
        try:
            if is_number(threshold):
                message += f" {threshold}"
        except:
            print(f"Error processing threshold {threshold}")
        record_notification(message, account_id, provider_id)
    if  'AllowanceThresholdData' in counter_type or 'Data Thresholds' in counter_type:
        message = f"data {event_state}"
        try:
            if is_number(threshold):
                threshold /= (1024 * 1024)
                message += f" {threshold} MB"
        except:
            print(f"Error processing threshold {threshold}")
        record_notification(message, account_id, provider_id)


def event_is_threshold(event) -> bool:
    detail = event.get('detail', {})
    event_data = detail.get('eventdata', '')
    notificationinformation = event_data.get('notificationinformation', '')
    event_name = notificationinformation.get('name', '')
    event_state = notificationinformation.get('state', '')
    if "Thresholds" in event_name and (event_state == 'low' or 'warning' in event_state or ('normal' not in event_state)):
        return True
    return False


def record_notification(threshold_type: str, account: str, provider: str):
    print('Recording notification for ' + threshold_type + ' for account ' + account)
    message = f'NOTIFICATION: Threshold {threshold_type}.'
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
