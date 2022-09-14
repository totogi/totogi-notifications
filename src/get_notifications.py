import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)


# Decimal Bug Fix: https://stackoverflow.com/questions/63278737/object-of-type-decimal-is-not-json-serializable
class DecimalEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal):
      return str(obj)
    return json.JSONEncoder.default(self, obj)


def handler(event, context):
    print(event)
    provider_id: str = event['queryStringParameters']['providerId']
    account_id: str = event['queryStringParameters']['accountId']
    pk = Key('pk').eq(f'PROVIDER#{provider_id}#ACCOUNT#{account_id}')
    sk = Key('sk').begins_with('TYPE#THRESHOLD#')
    expression = pk & sk
    items = table.query(
        KeyConditionExpression=expression
    )['Items']
    return {
        'statusCode': 200,
        'body': json.dumps({
            'items': items
        }, cls=DecimalEncoder)
    }
