import json
import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError
import random

SQS_REGION = 'us-east-1'
#SQS_REGION = 'us-east-2'
DYNAMO_REGION = 'us-east-2'
HOST = 'search-yelp-data-opensearch-wh2bpiwbc2mbewyfzv2skzneci.us-east-2.es.amazonaws.com'
INDEX = 'restaurants'
TABLE = 'yelp-restaurants'
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/355738687625/DiningConciergeSQS.fifo"
#QUEUE_URL = 'https://sqs.us-east-2.amazonaws.com/838127000767/Yelp-Restaurant-Queue'
#QUEUE_URL = "https://sqs.us-east-2.amazonaws.com/838127000767/Yelp-Restaurant.fifo"

# This address must be verified with Amazon SES.
SENDER_EMAIL = "vg2565@columbia.edu"


"""
Query 5 random restaurants from OpenSearch based on the provided cuisine
"""
def query(term):
    q = {'query': {'multi_match': {'query': term}}}

    client = OpenSearch(hosts=[{
            'host': HOST,
            'port': 443
        }],
        http_auth=get_awsauth(DYNAMO_REGION, 'es'),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection)

    res = client.search(index=INDEX, body=q)

    hits = res['hits']['hits']
    print(hits)
    sample = random.sample(hits, 5 if len(hits) > 5 else len(hits)-1)
    results = []
    for restaurant_dict in sample:
        results.append(restaurant_dict['_source'])

    return results


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)
     
"""
Connect to the target table and query data
"""
def get_restaurant_data(keys, table='yelp-restaurants'):
    try:
        db = boto3.resource('dynamodb', region_name=DYNAMO_REGION)
        # table = db.Table(table)
        print(keys)
        response = db.batch_get_item(RequestItems={
            table: {
                "Keys": [{"restaurantID": key} for key in keys],
                "AttributesToGet": ["name", "address"],
                }
            }
        )
        return response["Responses"][table]
    except ClientError as e:
        print(e)
        print('Error', e.response['Error']['Message'])

        
def send_email_to_client(recipient, subject, email_data):
    
    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = 'us-east-2'
                
    # The HTML body of the email.
    restaurants_recs_string_list = ["{}. {}, located at {}".format(i+1, restaurant_dict["name"], restaurant_dict["address"]) for (i, restaurant_dict) in enumerate(email_data["Restaurants_dict"])]
    BODY_HTML = """
                <html>
                <head></head>
                <body>
                  <h1>DiningConcierge ChatBot Restaurant Recommendations</h1>
                  <p>
                  “Hello! Here are my {cuisine_type} restaurant suggestions for {num_people} people, for {date} at {time}: <br /> {restaurant_suggestions}. Enjoy your meal!”
                  </p>
                </body>
                </html>
                """.format(
                    cuisine_type = email_data["Cuisine"].title(), 
                    num_people=email_data["NumberOfPeople"], 
                    date=email_data["Date"],
                    time=email_data["Time"],
                    restaurant_suggestions="<br />".join(restaurants_recs_string_list))
    
    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)
    
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject,
                },
            },
            Source=SENDER_EMAIL,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        raise 
    else:
        print("Email sent! Message ID:", response['MessageId'])



def lambda_handler(event, context):
    # cuisine = "mediterranean"

    # Receive message from SQS queue
    sqs = boto3.client('sqs', region_name=SQS_REGION)
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        AttributeNames=[
            'SentTimestamp'
        ],
        MessageAttributeNames=[
            'All'
        ],
        MaxNumberOfMessages=1,
        VisibilityTimeout=20,
        WaitTimeSeconds=0
    )
    
    # Process the message
    print("Whole Response from SQS")
    print(response)
    
    if not response.get("Messages", None):
        print("No message to process :(")
        return None
    
    message = response["Messages"][0]
    print("Processing MessageID:", message["MessageId"])
    print("Echoing attributes")
    print(message["MessageAttributes"])
    
    
    cuisine = message["MessageAttributes"]["Cuisine"]["StringValue"]
    
    # Querying OpenSearch for the specified cuisine and retreiving restaurantIDs
    # Using the restaurantIDs to query DynamoDB for additional details
    opensearch_results = query(cuisine)
    results = get_restaurant_data([restaurant_dict["restaurantID"] for restaurant_dict in opensearch_results], TABLE)
    
    print("Printing OpenSearch results")
    print(results)
    
    print("Deleting MessageID:", message["MessageId"])
    
    response = sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle'],
                )
    
    print("Response after Deleting from SQS")
    print(response)
    
    print("Generating Email")
    
    recipient = message["MessageAttributes"]["Email"]["StringValue"]
    email_data = {
                    "Cuisine": cuisine, 
                    "NumberOfPeople": message["MessageAttributes"]["Cuisine"]["StringValue"],
                    "Date": message["MessageAttributes"]["Date"]["StringValue"],
                    "Time": message["MessageAttributes"]["Time"]["StringValue"],
                    "Restaurants_dict": results,
    }
    send_email_to_client(recipient, "DiningConcierge ChatBot Restaurant Recommendations", email_data)
    
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
        },
        'body': json.dumps(results)
    }