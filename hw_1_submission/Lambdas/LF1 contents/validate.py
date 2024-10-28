# First Check Completed

import dateutil.parser
import dateutil.tz
import re
from datetime import datetime

import json

def validate_location(location):
    
    # whether or not chosen city is in Manhattan
    parsed = location.strip().lower().split()
    print("parsed location: ", parsed)
    if ("manhattan" in parsed):
        return True
    else:
        return False

def validate_cuisine(cuisine):
    # list of predefined cuisines
    cuisine_list = ["chinese", "italian", "french", "japanese", "mexican", "greek", "thai", "europian","korean", "mediterranean"]
    return cuisine.lower() in cuisine_list
    
def validate_number_of_people(number_of_people):
    # 0 or negative number should show error and Lex should ask user to input again.
    # need to check if only contains digits
    if int(number_of_people) <= 0:
        return False
    else:
        return True
    
def validate_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def validate_time(time, date):
    
    eastern = dateutil.tz.gettz('US/Eastern')
    current_time = datetime.now(tz=eastern).time()
    time_proposed_list = time.split(':')
    # calibrating time for comparison
    hour = str(int(time_proposed_list[0])) 
    minutes = time_proposed_list[1]
    time_proposed = datetime.strptime('{}:{}:00'.format(hour, minutes), '%H:%M:%S').time()
    # if the date is today
    if datetime.strptime(date, '%Y-%m-%d').date() == datetime.now().date():
        print('time_proposed: {}, current_time: {}'.format(time_proposed, current_time) )
        if time_proposed < current_time:
            return False
            
        else:
            return True
    
    else:
        return True
    
    

def validate_phoneNumber(phone_number):
    # check if only numbers are included
    numbers_only = phone_number.isnumeric()
    # check if the length is equal to 10
    length_valid = (len(phone_number) == 10)
    
    if numbers_only and length_valid:
        return True
    
    else:
        return False
        
def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if(re.fullmatch(regex, email)):
        print("Valid Email")
        return True
        
    else:
        print("Invalid Email")
        return False
        