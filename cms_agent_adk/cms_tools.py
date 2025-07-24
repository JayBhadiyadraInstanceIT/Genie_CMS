import os
import sys
import requests
import json

from typing import Dict, List, Any
from dotenv import load_dotenv
from google.adk.tools import FunctionTool
from langfuse import observe, get_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import (
    REMOTE_1_AGENT_DATABASE_API_URL, 
    REMOTE_1_AGENT_DATABASE_DBNAME, 
    HEADERS,
    REMOTE_1_AGENT_EMAIL_API_URL
)

load_dotenv()
langfuse = get_client()
headers = HEADERS

@observe(name="MongoDB fetch Tool", as_type="span")
def get_mongodb(collection: str, filter: str, projection: str, limit: int) -> Dict:
    """
    Fetch data from MongoDB via the Node.js API using the provided query parameters.

    Args:
        collection (str): The name of the MongoDB collection (e.g., 'categories').
        filter (str): The filter criteria as a JSON string (e.g., '{"is_available": true}').
        limit (int): The maximum number of documents to return.

    Returns:
        dict: The data fetched from the MongoDB database via the API, or an error message.
    """
    langfuse.update_current_span(level="DEBUG")
    # Parse JSON string for filter
    try:
        filter_dict = json.loads(filter)
        projection_dict = json.loads(projection)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON in filter: {str(e)}"}
    
    # Construct the query dictionary for the Node.js API
    query = {
        "isprod": 1,
        "dbname": REMOTE_1_AGENT_DATABASE_DBNAME,
        "collection": collection,
        "paginationinfo": {
            "pagelimit": limit,
            "filter": filter_dict,
            "projection": projection_dict
        }
    }
    
    # Send the query to the Node.js API
    api_url = REMOTE_1_AGENT_DATABASE_API_URL
    try:
        response = requests.post(api_url, json=query, headers=headers)
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses
        data = response.json()
        # Ensure the return value is always a dictionary
        if isinstance(data, list):
            return {"data": data}
        return data
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

@observe(name="Send_Email_Tool", as_type="span")
def send_email(to: str, cc: str, personname: str, subject: str, attachments: List[str]) -> Dict[str, Any]:
    """
    Send an email via your email-sending endpoint.

    Args:
        to (str): Recipient email address.
        cc (str): CC recipient(s), empty string if none.
        personname (str): Recipient's name for personalization.
        subject (str): Email subject.
        attachments (List[str]): List of attachment URLs.

    Returns:
        dict: Response from your email API or error info.
    """
    payload = {
        "to": to,
        "cc": cc,
        "personname": personname,
        "subject": subject,
        "attachments": attachments
    }
    try:
        resp = requests.post(REMOTE_1_AGENT_EMAIL_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        response_data = resp.json()
        
        if isinstance(response_data, list):
            return {"data": response_data}
        return response_data
    except requests.RequestException as e:
        return {"error": f"Email API request failed: {str(e)}"}
    

# Create a FunctionTool without the 'declaration' parameter
get_mongodb_tool = FunctionTool(func=get_mongodb)
send_email_tool = FunctionTool(func=send_email)
