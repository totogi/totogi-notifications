import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode
import time
import json

AWS_REGIONS_INFO = {
    'us-east-1': {
        'aws_project_region': 'us-east-1',
        'aws_cognito_region': 'us-east-1',
        'aws_user_pools_id': 'us-east-1_foZ45Yf8D',
        'aws_user_pools_web_client_id': '58jcnn51q51crrlmvrque7q0du',
        'aws_appsync_graphqlEndpoint': 'https://gql.produseast1.api.totogi.com/graphql',
        'aws_appsync_region': 'us-east-1',
        'aws_appsync_authenticationType': 'AMAZON_COGNITO_USER_POOLS'
    },
    'ap-southeast-1': {
        'aws_project_region': 'us-east-1',
        'aws_cognito_region': 'ap-southeast-1',
        'aws_user_pools_id': 'ap-southeast-1_f5XO01S4q',
        'aws_user_pools_web_client_id': '6dm5labfmiqsbofgbbtdvkkrov',
        'aws_appsync_graphqlEndpoint': 'https://gql.prodapsoutheast1.api.totogi.com/graphql',
        'aws_appsync_region': 'ap-southeast-1',
        'aws_appsync_authenticationType': 'AMAZON_COGNITO_USER_POOLS'
    }
}


DEFAULT_AWS_REGION = 'us-east-1'


def authorized_response():
    return {'isAuthorized': True, 'context': {}}


def unauthorized_response():
    return {'isAuthorized': False, 'context': {}}


def get_public_keys(region=DEFAULT_AWS_REGION):
    # cognito_idp = boto3.client('cognito-idp', region_name=region)
    # try:
    #     response = cognito_idp.get_signing_keys(UserPoolId=AWS_REGIONS_INFO[region]['aws_user_pools_id'])
    #     return {key['kid']: key for key in response['Keys']}
    # except ClientError as e:
    #     print(e)
    #     return {}

    region_info = AWS_REGIONS_INFO[region]
    keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(region, region_info['aws_user_pools_id'])
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()

    return json.loads(response.decode('utf-8'))['keys']


def handler(event, context):
    print('Auth event')
    print(event)
    workaround_token = event["headers"]["authorization"].split('|')
    token = workaround_token[0]
    region = workaround_token[1] if len(workaround_token) > 1 else DEFAULT_AWS_REGION
    headers = jwt.get_unverified_headers(token)
    region_info = AWS_REGIONS_INFO[region]
    # get the kid from the headers prior to verification
    keys = get_public_keys(region)
    kid = headers['kid']
    # search for the kid in the downloaded public keys
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]["kid"]:
            key_index = i
            break
    if key_index == -1:
        print("Public key not found in jwks.json")
        return unauthorized_response()
    # construct the public key
    public_key = jwk.construct(keys[key_index])
    # get the last two sections of the token,
    # message and signatu re (encoded in base64)
    message, encoded_signature = str(token).rsplit(".", 1)
    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        print("Signature verification failed")
        return unauthorized_response()
    
    print("Signature successfully verified")
    # since we passed the verification, we can now safely
    # use the unverified claims
    claims = jwt.get_unverified_claims(token)
    # additionally we can verify the token expiration
    # if time.time() > claims['exp']:
    #     logger.error('Token is expired')
    #     return False
    # and the Audience  (use claims['client_id'] if verifying an access token)
    if (time.time() > claims["exp"] or time.time() < claims["auth_time"]):
      print("Claim is expired or invalid")
      return unauthorized_response()
    
    if claims["iss"] != f"https://cognito-idp.{region}.amazonaws.com/{region_info['aws_user_pools_id']}":
      print("claim issuer is invalid")
      return unauthorized_response()
    
    if claims["token_use"] != "id":
      print("claim use is not access")
      return unauthorized_response()

    if not claims.get("aud"):
        claims["aud"] = claims["client_id"]

    if claims["aud"] != region_info['aws_user_pools_web_client_id']:
        print("Token was not issued for this audience")
        return unauthorized_response()
    
    # now we can use the claims
    return authorized_response()
