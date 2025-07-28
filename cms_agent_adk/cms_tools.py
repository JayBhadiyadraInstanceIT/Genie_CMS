import os
import sys
import requests
import json

from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from google.adk.tools import FunctionTool
from langfuse import observe, get_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import (
    REMOTE_1_AGENT_DATABASE_API_URL, 
    REMOTE_1_AGENT_DATABASE_DBNAME, 
    HEADERS,
    REMOTE_1_AGENT_EMAIL_API_URL,
    ALGORITHM,
    TOKEN,
    ISSUER,
    AUDIENCE,
    ACCESS_TOKEN_KEY,
)

from API_authentication import (
    validate_token,
    ACCESSTOKEN_API_URL,
    ACCESS_TOKEN_HEADERS,
)

load_dotenv()
langfuse = get_client()
headers = HEADERS

def fetch_new_token() -> Tuple[str, Dict[str, str]]:
    """
    POST to your ACCESSTOKEN_API_URL with the required headers:
      - key    (your API key)
      - issuer (your issuer string)
    Returns (new_token, {"uid":..., "unqkey":...})
    """
    headers = {
        "key": ACCESS_TOKEN_KEY,
        "issuer": ISSUER,
    }
    resp = requests.post(ACCESSTOKEN_API_URL, headers=headers)
    resp.raise_for_status()

    # the fresh JWT comes back in the response headers under "token"
    new_token = resp.headers.get("token")
    if not new_token:
        raise RuntimeError("accesstoken API did not return a token header")

    # uid/unqkey live in the JSON body at data.uid / data.unqkey
    body = resp.json()
    data = body.get("data", {})
    uid    = data.get("uid")
    unqkey = data.get("unqkey")
    if not uid or not unqkey:
        raise RuntimeError("accesstoken API did not return uid/unqkey in body")

    return new_token, {"uid": uid, "unqkey": unqkey}

def get_valid_token_and_payload() -> Tuple[str, Dict]:
    """
    1. Try your existing TOKEN constant.
    2. If it's expired → fetch_new_token().
    3. If it fails for any other reason → raise.
    """

    # try the current
    result = validate_token(
        token=TOKEN,
        algorithms=ALGORITHM,
        audience=AUDIENCE,
        issuer=ISSUER
    )

    if "error" not in result:
        return TOKEN, result

    err = result["error"].lower()
    if "expired" in err:
        # expired → get a fresh one
        fresh_token, extra_claims = fetch_new_token()

        # re-validate it
        new_payload = validate_token(
            token=fresh_token,
            algorithms=ALGORITHM,
            audience=AUDIENCE,
            issuer=ISSUER
        )
        if "error" in new_payload:
            raise RuntimeError(f"Refreshed token invalid: {new_payload['error']}")

        # merge in the uid/unqkey from the refresh response:
        new_payload.update(extra_claims)
        return fresh_token, new_payload

    # some other JWT error (bad audience, bad signature, etc.)
    raise RuntimeError(f"Token validation failed: {result['error']}")

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
    # validate token
    try:
        token, jwt_payload = get_valid_token_and_payload()
    except Exception as e:
        # Return the JWT error back to caller
        return {"error": str(e)}
    
    uid    = jwt_payload.get("uid")
    unqkey = jwt_payload.get("unqkey")
    # validate token
    # validation_result = validate_token(token=TOKEN, algorithms=ALGORITHM, audience=AUDIENCE, issuer=ISSUER)
    # print("validation_result", validation_result)
    # if "error" in validation_result:
    #     return {"error": f"Token validation failed: {validation_result['error']}"}

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
