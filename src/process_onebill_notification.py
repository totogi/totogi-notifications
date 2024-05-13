import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
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
    pk = Key('pk').eq('ONEBILL_NOTIFICATION')
    sk = Key('sk').eq(f'PROVIDER#{provider}#ACCOUNT#{account}')
    print(pk.get_expression())
    print(sk.get_expression())
    expression = pk & sk
    items = table.query(
        KeyConditionExpression=expression
    )['Items']
    if len(items) < 1:
        print("One bill not found for provider " + provider + " account " + account)
        return

    item = items[0]
    if item['enabled']:
        print("One bill enabled for provider - making API call" + provider + " account " + account)
        return

    print("One bill not enabled for provider " + provider + " account " + account)
