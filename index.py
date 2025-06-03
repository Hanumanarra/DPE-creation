from flask import Flask, render_template, url_for, request, jsonify
import sys
import os
import json # For printing debugging info

# Add the parent directory (project root) to sys.path so sud can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import from sud.py
try:
    from sud import process_calculation_logic
except ImportError as e:
    print(f"Error importing sud: {e}", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    def process_calculation_logic(*args, **kwargs):
        return {"error": f"Failed to import sud module. Check paths and dependencies. {e}"}

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# This is your example form_data, can be used for GET requests or as a fallback
EXAMPLE_FORM_DATA = {
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
        "value": "50000"
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
        "value": [ "aa746040-c324-429d-9026-fa699b1af97c" ],
        "options": [
          { "id": "aa746040-c324-429d-9026-fa699b1af97c", "text": "15 Years" },
          { "id": "988e6036-b466-4ac1-b8c1-5270adb94e35", "text": "25 Years" }
        ]
      },
      {
        "key": "question_VjKGMM",
        "label": "Premium Payment Term",
        "type": "DROPDOWN",
        "value": [ "24faa818-75d9-4cc3-bbb5-9c3128c15bc3" ],
        "options": [
          { "id": "24faa818-75d9-4cc3-bbb5-9c3128c15bc3", "text": "7 Years" },
          { "id": "90ba85ed-2f13-4843-8bde-af3fa9c06955", "text": "14 Years" }
        ]
      },
      {
        "key": "question_PD7pXB",
        "label": "Premium Payment Frequency",
        "type": "MULTIPLE_CHOICE",
        "value": [ "b72fa0eb-beba-4edd-a80c-6b2c93f7f066" ],
        "options": [
          { "id": "b72fa0eb-beba-4edd-a80c-6b2c93f7f066", "text": "Annual" },
          { "id": "053dabe9-c9c5-4fc0-ab62-a353df494567", "text": "Semi-Annual" },
          { "id": "633732ef-e835-40af-9a99-f1e728d42f3a", "text": "Quarterly" },
          { "id": "7bdfab24-82c9-4cf3-9594-8e2edb093618", "text": "Monthly" }
        ]
      }
    ]
  }
}

@app.route('/', methods=['GET', 'POST'])
def home():
    form_data_to_process = EXAMPLE_FORM_DATA # Default

    if request.method == 'POST':
        try:
            # Tally.so sends data as JSON in the request body
            webhook_data = request.get_json()
            if webhook_data:
                # You might want to log the received data for debugging
                print("Received webhook data:", json.dumps(webhook_data, indent=2), file=sys.stderr)
                
                # Assuming the structure matches what process_calculation_logic expects.
                # Tally.so webhook data usually has a 'data' field containing form fields.
                # The EXAMPLE_FORM_DATA structure matches the expected Tally.so webhook structure.
                form_data_to_process = webhook_data
            else:
                print("POST request received, but no JSON data found.", file=sys.stderr)
                # Optionally, you could return an error here or fall back to EXAMPLE_FORM_DATA
                # return jsonify({"error": "No JSON data received"}), 400
        except Exception as e:
            print(f"Error processing POST request: {e}", file=sys.stderr)
            # Optionally, return an error or fall back
            # return jsonify({"error": f"Error processing request: {e}"}), 500
    
    elif request.method == 'GET':
        print("GET request received, using example data.", file=sys.stderr)
        # For GET requests, we'll use the EXAMPLE_FORM_DATA
        pass # form_data_to_process is already set to EXAMPLE_FORM_DATA

    # --- Actual Processing ---
    try:
        template_data = process_calculation_logic(form_data_to_process, None, None)
        if "error" in template_data:
            print(f"Error from process_calculation_logic: {template_data['error']}", file=sys.stderr)
            return f"An error occurred: {template_data['error']}", 500
    except Exception as e:
        print(f"Exception calling process_calculation_logic: {e}", file=sys.stderr)
        return f"An server error occurred during processing: {e}", 500

    # Render the sud.html template, passing the data to it
    # For a webhook, you might not always render HTML.
    # If Tally.so expects a specific response (e.g., a 200 OK), you'd return that.
    # However, if the goal is to *then show this page based on the webhook data*, rendering is fine.
    # If this endpoint is *only* for Tally.so to send data and not for a user to see a page immediately,
    # you might just return a success status.
    # For now, we'll assume you want to render the page with the processed data.
    return render_template('sud.html', **template_data)

# For Vercel, the 'app' variable is the entry point.
