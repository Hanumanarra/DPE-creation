import requests
import boto3
import base64
import json
import uuid
import botocore
import logging
from datetime import datetime


# AWS and Google API credentials
AWS_ACCESS_KEY_ID = 'AKIARKXPVNN3LVVXP35N'
AWS_SECRET_ACCESS_KEY = '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'
GOOGLE_API_KEY = 'AIzaSyDRhOeB7INqWcV0yiNpw6pNmUqdtEE8JAI'

def parse_regular_fields(data):
    result = {}
    simple_types = [
        "HIDDEN_FIELDS", "CALCULATED_FIELDS", "INPUT_TEXT", "INPUT_NUMBER", "INPUT_EMAIL", 
        "INPUT_PHONE_NUMBER", "INPUT_LINK", "INPUT_DATE", "INPUT_TIME", "TEXTAREA", 
        "PAYMENT", "RATING", "LINEAR_SCALE"
    ]
    for question in data:
        if question["type"] in simple_types:
            result[question["label"]] = question["value"]
    return result

def parse_multiple_choice_types(data):
    result = {}
    for question in data:
        if question["type"] == "MULTIPLE_CHOICE":
            selected_id = question["value"][0]
            for option in question["options"]:
                if option["id"] == selected_id:
                    result[question["label"]] = option["text"]
    return result

def parse_complex_types(data):
    result = {}
    complex_types = ["MULTI_SELECT", "RANKING"]
    for question in data:
        if question["type"] in complex_types:
            selected_options = []
            for selected_id in question["value"]:
                for option in question["options"]:
                    if option["id"] == selected_id:
                        selected_options.append(option["text"])
            result[question["label"]] = selected_options
    return result

def parse_dropdown_fields(data):
    result = {}
    for question in data:
        if question["type"] == "DROPDOWN":
            for selected_id in question["value"]:
                for option in question["options"]:
                    if option["id"] == selected_id:
                        value = option["text"]
            result[question["label"]] = value
    return result

def parse_checkbox_fields(data):
    result = {}
    for question in data:
        if question["type"] == "CHECKBOXES":
            if "options" in question:
                selected_options = []
                if question["value"] is None:
                    continue
                for selected_id in question["value"]:
                    for option in question["options"]:
                        if option["id"] == selected_id:
                            selected_options.append(option["text"])
                result[question["label"]] = selected_options
            else:
                result[question["label"]] = question["value"]
    return result

def parse_fields_with_url(data):
    result = {}
    url_fields = ["FILE_UPLOAD", "SIGNATURE"]
    for question in data:
        if question["type"] in url_fields:
            result[question["label"]] = question["value"][0]["url"]
    return result

def serialize_form_data(form_data):
    fields = form_data["data"]["fields"]
    result = {}
    result.update(parse_regular_fields(fields))
    result.update(parse_dropdown_fields(fields))
    result.update(parse_complex_types(fields))
    result.update(parse_checkbox_fields(fields))
    result.update(parse_fields_with_url(fields))
    result.update(parse_multiple_choice_types(fields))
    return result
 
def convert_to_words(num):
    # Indian numbering system words
    Indian = {
        1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six', 7: 'Seven', 8: 'Eight', 9: 'Nine', 10: 'Ten',
        11: 'Eleven', 12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen', 15: 'Fifteen', 16: 'Sixteen', 17: 'Seventeen', 18: 'Eighteen',
        19: 'Nineteen', 20: 'Twenty', 30: 'Thirty', 40: 'Forty', 50: 'Fifty', 60: 'Sixty', 70: 'Seventy', 80: 'Eighty', 90: 'Ninety'
    }

    # Function to convert two-digit number to words
    def convert_two_digits(n):
        if n <= 20:
            return Indian[n]
        else:
            return Indian[n // 10 * 10] + '-' + Indian[n % 10] if n % 10 != 0 else Indian[n // 10 * 10]

    # Function to convert three-digit number to words
    def convert_three_digits(n):
        hundred = n // 100
        rest = n % 100
        if hundred != 0 and rest != 0:
            return Indian[hundred] + ' Hundred ' + convert_two_digits(rest)
        elif hundred != 0:
            return Indian[hundred] + ' Hundred'
        else:
            return convert_two_digits(rest)

    # Remove commas and convert the number to an integer
    num = int(''.join(num.split(',')))

    if num == 0:
        return 'Zero'

    words = ''
    crore = num // 10000000
    lakh = (num % 10000000) // 100000
    thousand = (num % 100000) // 1000
    remaining = num % 1000

    if crore != 0:
        words += convert_three_digits(crore) + ' Crore '

    if lakh != 0:
        words += convert_three_digits(lakh) + ' Lakh '

    if thousand != 0:
        words += convert_three_digits(thousand) + ' Thousand '

    if remaining != 0:
        words += convert_three_digits(remaining)

    return words.capitalize()



def save_base64_as_mp3_to_s3(base64_string, object_key, aws_access_key_id, aws_secret_access_key, region_name="eu-north-1", bucket_name="emi-calculator-s1"):
    mp3_data = base64.b64decode(base64_string)
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )
    try:
        s3.put_object(Body=mp3_data, Bucket=bucket_name, Key=object_key)
    except botocore.exceptions.ClientError as e:
        logging.error(f"Failed to upload to S3: {e}")
        raise

def text_to_speech(text, google_api_key, aws_access_key_id, aws_secret_access_key):
    url = "https://texttospeech.googleapis.com/v1/text:synthesize"

    data = {
        "input": {"ssml": text},  # Ensure 'ssml' is a valid string
        "voice": {"languageCode": "en-IN", "name": "en-IN-Standard-C"},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    if response.status_code == 200:
        content = response.json()
        base64_string = content.get("audioContent")
        if base64_string:
            output_filename = "VO_Banking_Demo/" + str(uuid.uuid4()) + ".mp3"
            save_base64_as_mp3_to_s3(base64_string, output_filename, aws_access_key_id, aws_secret_access_key)
            return output_filename
    else:
        raise Exception(f"Text to speech conversion failed with status code {response.status_code}: {response.text}")

def get_audio_text(name, total_premium, benefit_premium,total_premium_words,benefit_premium_words,special_one,special_two):
    audio_text = (
        f'<speak>'
        f'<break time="1500ms"/>Hello, {name}, One More Reason To Smile, S-U-D Life Century Income A Non Participating individual Savings Life Insurance plan, that Offer Protection and survival benefits, Enjoy the personalized Presentation.'
        f'<break time="1500ms"/>Key Features .'
        f'<break time="1500ms"/>Choose income options tailored to your needs.'
        f'<break time="1000ms"/>Receive income as early as the end of the 1st policy year or choose to defer  ,Get Life Cover of {special_two}.'
        f'<break time="3000ms"/>Guaranteed Maturity Benefit of {special_one}  ,Enjoy tax benefits on premiums paid.'
        f'<break time="3500ms"/>Awards Won by S-U-D Life ,Insurance Leader Of the Year, Fastest Growing Life Insurance Company, Best CSR initiative Awards, Innovation in Customer Engagement.'
        f'<break time="2000ms"/>Highlights. '
        f'<break time="2500ms"/> What You Give Total Premium ({total_premium_words}), what you get Total Benefits ({benefit_premium_words}).'
        f'<break  time="3000ms"/>You Pay Annual premium of ₹50000, you get Guaranteed Income Including Loyalty Income of up to ₹14000, and you get Maturity Benefits of {special_one}.'
        f'<break time="8000ms"/>Here Is The Quick SnapShot of Solution for your reference.'
        f'<break time="4000ms"/>This is Presented by Hanuma, If You Have any doubts feel free to reach out.'
        f'<break time="4000ms"/>The benefits and return shown in presentation for illustrative purpose only,  you are required to reach I-R-D-I-O.'
        f'</speak>'
    )
    return audio_text
    
def calculate_age(dob):
    dob_date=datetime.strptime(dob,"%Y-%m-%d")
    today=datetime.today()
    age=today.year-dob_date.year-((today.month,today.day)<(dob_date.month,dob_date.day))
    return age

def extract_numeric_values(text):
    return int(''.join(filter(str.isdigit,text)))

def formatINR(value):
    num=str(value).replace(",", "")
    parts=num.split(",")
    integer_part=parts[0]
    fractional_part=parts[1] if len(parts)>1 else ""
    length=len(integer_part)
    if length<=3:
        formatted_integer=integer_part
    else:
        last_three=integer_part[-3:]
        other_numbers=integer_part[:-3]
        formatted_other=""
        while len(other_numbers)>2:
            formatted_other=","+other_numbers[-2:]+formatted_other
            other_numbers=other_numbers[:-2]
        if other_numbers:
            formatted_other=other_numbers+formatted_other
            formatted_integer=formatted_other+","+last_three
            formatted_number=formatted_integer+("."+fractional_part if fractional_part else"")
            return formatted_number        


    
     

def process_calculation_logic(form_data, env_variables, user_meta, **kwargs):
    tally_form_data = serialize_form_data(form_data)
    name = tally_form_data["Name"]
    premium = int(tally_form_data["Premium"])
    dob=tally_form_data["DOB"]
    age=calculate_age(dob)

  
    
    term=tally_form_data["Policy Term"]
    
    payTerm=tally_form_data["Premium Payment Term"]
    frequency=tally_form_data["Premium Payment Frequency"]

    term_numeric=extract_numeric_values(term)
    payTerm_numeric=extract_numeric_values(payTerm)

    frequency_multipler_map={
        "Annual":1,
        "Semi-Annual":2,
        "Quarterly":4,
        "Monthly":12,
    }
    multipler_map=frequency_multipler_map.get(frequency,1)
    

    total_premium=premium*term_numeric*multipler_map
    benefit_premium=int(1.5*total_premium)
    ageOne=age+1
    ageTwo=age+term_numeric-1
    ageThree=age+payTerm_numeric-1


   
    formatted_permium=formatINR(premium)
    formatted_total_premium=formatINR(total_premium)
    formatted_benefit_premium=formatINR(benefit_premium)
    total_premium_words=convert_to_words(str(total_premium))
    benefit_premium_words=convert_to_words(str(benefit_premium))
    special_one=338390
    special_two=500000
    special_one=convert_to_words(str(special_one))
    special_two=convert_to_words(str(special_two))

    audio_text = get_audio_text(name,total_premium ,benefit_premium,total_premium_words,benefit_premium_words,special_one,special_two)
    audio_url = text_to_speech(audio_text, GOOGLE_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    s3_audio_url=f"https://emi-calculator-s1.s3.eu-north-1.amazonaws.com/{audio_url}"
    return {
        "audioUrl":s3_audio_url,
        "name":name,
        "premium":premium,
        "total_premium":total_premium,
        "benefit_premium":benefit_premium,
        "formatted_premium":formatted_permium,
        "formatted_total_premium":formatted_total_premium,
        "foramtted_benefit_premium":formatted_benefit_premium,
        "total_premium_words":total_premium_words,
        "benefit_premium_words":benefit_premium_words,
        "special_one":special_one,
        "special_two":special_two,
        "dob":dob,
        "age":age,
        "ageOne":ageOne,
        "ageTwo":ageTwo,
        "ageThree":ageThree,
        "term":term,
        "payTerm":payTerm,
        "frequency":frequency,
    }


if __name__ == "__main__":
    form_data = {
  "eventId": "f20b08cc-a86b-4d8d-901d-e728449c7b05",
  "eventType": "FORM_RESPONSE",
  "createdAt": "2025-03-06T18:27:06.835Z",
  "data": {
    "responseId": "LQy7MJ",
    "submissionId": "LQy7MJ",
    "respondentId": "GyzlBk",
    "formId": "mV425y",
    "formName": "Form",
    "createdAt": "2025-03-06T18:27:06.000Z",
    "fields": [
      {
        "key": "question_2B6KAg",
        "label": "Name",
        "type": "INPUT_TEXT",
        "value": "Lakshmi Hanuma Narra"
      },
      {
        "key": "question_oDj1BM_ac9ac848-9ffa-4df5-bdaa-002936bd9d59",
        "label": "tool_id",
        "type": "HIDDEN_FIELDS",
        "value": "154"
      },
      {
        "key": "question_ZoB2OA",
        "label": "Premium",
        "type": "INPUT_TEXT",
        "value": "100000"
      },
      {
        "key": "question_GKZ6JL",
        "label": "DOB",
        "type": "INPUT_DATE",
        "value": "2000-03-06"
      },
      {
        "key": "question_Ol6aJY",
        "label": "Policy Term",
        "type": "DROPDOWN",
        "value": [
          "aa746040-c324-429d-9026-fa699b1af97c"
        ],
        "options": [
          {
            "id": "aa746040-c324-429d-9026-fa699b1af97c",
            "text": "15 Years"
          },
          {
            "id": "988e6036-b466-4ac1-b8c1-5270adb94e35",
            "text": "25 Years"
          }
        ]
      },
      {
        "key": "question_VjKGMM",
        "label": "Premium Payment Term",
        "type": "DROPDOWN",
        "value": [
          "24faa818-75d9-4cc3-bbb5-9c3128c15bc3"
        ],
        "options": [
          {
            "id": "24faa818-75d9-4cc3-bbb5-9c3128c15bc3",
            "text": "7 Years"
          },
          {
            "id": "90ba85ed-2f13-4843-8bde-af3fa9c06955",
            "text": "14 Years"
          }
        ]
      },
      {
        "key": "question_PD7pXB",
        "label": "Premium Payment Frequency",
        "type": "MULTIPLE_CHOICE",
        "value": [
          "b72fa0eb-beba-4edd-a80c-6b2c93f7f066"
        ],
        "options": [
          {
            "id": "b72fa0eb-beba-4edd-a80c-6b2c93f7f066",
            "text": "Annual"
          },
          {
            "id": "053dabe9-c9c5-4fc0-ab62-a353df494567",
            "text": "Semi-Annual"
          },
          {
            "id": "633732ef-e835-40af-9a99-f1e728d42f3a",
            "text": "Quarterly"
          },
          {
            "id": "7bdfab24-82c9-4cf3-9594-8e2edb093618",
            "text": "Monthly"
          }
        ]
      }
    ]
  }
}

    result = process_calculation_logic(form_data, None, None)
    print(result)