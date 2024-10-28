'''https://gist.github.com/alexcasalboni/3ea2d8dda11c6b73bbf98adf2dd6a214
code repurposed from the link above to validate and handle the event parameter

First Check Completed
'''

import json
import boto3

from validate import *
from datetime import datetime

def lambda_handler(event, context):
    print(event)
    
    intent_name = event['interpretations'][0]['intent']['name']
    
    # Lex will propose a next state if available but if user input is not valid,
    # you will modify it to tell Lex to ask the same question again (meaning ask
    # the current slot question again)

    resp = {"statusCode": 200, "sessionState": event["sessionState"]}
    
    if "proposedNextState" not in event:
        # here we can send slots to sqs
        resp["sessionState"]["dialogAction"] = {"type": "Delegate"}
        response_slots = {}
        
        response_slots['Cuisine'] = resp['sessionState']['intent']['slots']['Cuisine']['value']['interpretedValue']
        response_slots['NumberOfPeople'] = resp['sessionState']['intent']['slots']['NumberOfPeople']['value']['interpretedValue']
        response_slots['PhoneNumber'] = resp['sessionState']['intent']['slots']['PhoneNumber']['value']['interpretedValue']
        response_slots['Time'] = resp['sessionState']['intent']['slots']['Time']['value']['interpretedValue']
        response_slots['Date'] = resp['sessionState']['intent']['slots']['Date']['value']['interpretedValue']
        response_slots['Location'] = resp['sessionState']['intent']['slots']['Location']['value']['interpretedValue']
        response_slots['Email'] = resp['sessionState']['intent']['slots']['Email']['value']['interpretedValue']
        
        print("these are the response slots: ", response_slots)
        send_response_to_sqs(response_slots)
        return resp
        
    else:
        resp = {"statusCode": 200, "sessionState": event["sessionState"]}
        # getting the slots
        slots = event['interpretations'][0]['intent']['slots']
        
        if (
        not slots['Location'] and not slots['Cuisine'] and not slots['NumberOfPeople']
        and not slots['Date'] and not slots['Time'] and not slots['PhoneNumber']
        and not slots['Email']
        ):
            print('here')
            resp["sessionState"]["dialogAction"] = {"type": "Delegate"}
            return resp
            
        
        location = slots.get('Location')
        cuisine = slots.get('Cuisine')
        number_of_people = slots.get('NumberOfPeople')
        date = slots.get('Date')
        time = slots.get('Time')
        phone_number = slots.get('PhoneNumber')
        email = slots.get('Email')
        
    
        # we're going to add the validation stuff here
        intent_name = 'DiningSuggestionsIntent'
        
        
        if location and not validate_location(location.get('value').get('originalValue')):
            
            resp["sessionState"]["dialogAction"] = {
                'type': 'ElicitSlot',
                'intentName': intent_name,
                'slots': slots,
                'slotToElicit': 'Location',
                'message': 'We currently do not support {} as a valid \
                destination, only Manhattan.  Can you try a different \
                city?'.format(location.get('value').get('originalValue'))
            }
            
            print(resp)
            
            return resp
            
            
        if cuisine and not validate_cuisine(cuisine.get('value').get('interpretedValue')):
            
            resp["sessionState"]["dialogAction"] = {
                'type': 'ElicitSlot',
                'intentName': intent_name,
                'slots': slots,
                'slotToElicit': 'Cuisine',
                'message': 'We currently do not support {} as a cuisine \
                type. Try from Chinese, French, Italian, Indian, Japanese, \
                Thai, Mediterranean, or Mexican.'.format(cuisine.get('value').get('interpretedValue'))
            }
            
            return resp
            
        if number_of_people and not validate_number_of_people(number_of_people.get('value').get('interpretedValue')):
            
            resp["sessionState"]["dialogAction"] = {
                'type': 'ElicitSlot',
                'intentName': intent_name,
                'slots': slots,
                'slotToElicit': 'NumberOfPeople',
                'message': 'Suggestions should be for at least one person. \
                Please re-enter a valid number for your party.'
            }
            
            return resp
            
        if date:
            if not validate_date(date.get('value').get('interpretedValue')):
                resp["sessionState"]["dialogAction"] = {
                    'type': 'ElicitSlot',
                    'intentName': intent_name,
                    'slots': slots,
                    'slotToElicit': 'Date',
                    'message': 'I did not understand your date. Please try again'
                    
                }
                
                return resp
                
            if datetime.strptime(date.get('value').get('interpretedValue'), '%Y-%m-%d').date() < datetime.now().date():
                
                resp["sessionState"]["dialogAction"] = {
                    'type': 'ElicitSlot',
                    'intentName': intent_name,
                    'slots': slots,
                    'slotToElicit': 'Date',
                    'message': 'Suggestions must be at least for the current \
                    date.  Can you try a different date?'
                }
                
                return resp
            
        if (time and date) and not validate_time(time.get('value').get('interpretedValue'), date.get('value').get('interpretedValue')):
            resp["sessionState"]["dialogAction"] = {
                'type': 'ElicitSlot',
                'intentName': intent_name,
                'slots': slots,
                'slotToElicit': 'Time',
                'message': 'Suggestions must be at least for the current \
                time if for today. Can you try a different time?'
                    
                }
                
            return resp
            
        if phone_number and not validate_phoneNumber(phone_number.get('value').get('interpretedValue')):
            resp["sessionState"]["dialogAction"] = {
                'type': 'ElicitSlot',
                'intentName': intent_name,
                'slots': slots,
                'slotToElicit': 'PhoneNumber',
                'message': 'Please re-enter your phone number.'
                
            }
                
            return resp
        
        if email and not validate_email(email.get('value').get('interpretedValue')):
            
            resp["sessionState"]["dialogAction"] = {
                'type': 'ElicitSlot',
                'intentName': intent_name,
                'slots': slots,
                'slotToElicit': 'Email',
                'message': 'Please re-enter your email.'
                
            }
                
            return resp
            
        # all good
        resp["sessionState"]["dialogAction"] = {"type": "Delegate"}
        return resp

def send_response_to_sqs(response_slots):
    sqs = boto3.client('sqs', region_name='us-east-1')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/355738687625/DiningConciergeSQS.fifo'
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageAttributes={
            'Cuisine': {
                'DataType': 'String',
                'StringValue': response_slots['Cuisine']
            },
            'NumberOfPeople': {
                'DataType': 'String',
                'StringValue': response_slots['NumberOfPeople']
            },
            'PhoneNumber': {
                'DataType': 'String',
                'StringValue': response_slots['PhoneNumber']
            },
            'Time': {
                'DataType': 'String',
                'StringValue': response_slots['Time']
            },
            'Date': {
                'DataType': 'String',
                'StringValue': response_slots['Date']
            },
            'Location': {
                'DataType': 'String',
                'StringValue': response_slots['Location']
            },
            'Email': {
                'DataType': 'String',
                'StringValue': response_slots['Email']
            },
        },
        MessageBody=(
            json.dumps({
            'Cuisine': {
                'DataType': 'String',
                'StringValue': response_slots['Cuisine']
            },
            'NumberOfPeople': {
                'DataType': 'String',
                'StringValue': response_slots['NumberOfPeople']
            },
            'PhoneNumber': {
                'DataType': 'String',
                'StringValue': response_slots['PhoneNumber']
            },
            'Time': {
                'DataType': 'String',
                'StringValue': response_slots['Time']
            },
            'Date': {
                'DataType': 'String',
                'StringValue': response_slots['Date']
            },
            'Location': {
                'DataType': 'String',
                'StringValue': response_slots['Location']
            },
            'Email': {
                'DataType': 'String',
                'StringValue': response_slots['Email']
            },
            })
        ),
        MessageGroupId = "LF1",
    )
    print(response)