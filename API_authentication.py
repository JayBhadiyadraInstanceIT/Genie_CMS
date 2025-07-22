import sys
import os
import requests
from typing import Dict
import jwt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import (
    ACCESSTOKEN_API_URL,
    ACCESS_TOKEN_HEADERS,
    ALGORITHM,
    TOKEN,
    AUDIENCE,
    )


def get_access_token() -> Dict[str, str]:
    url = ACCESSTOKEN_API_URL
    headers = ACCESS_TOKEN_HEADERS
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print("Raw token response:", data)
        token_data = data.get("data", {})  # Safely get the nested dict
        return {
            "token": None,  # No token is present; this might not be needed at all
            "uid": token_data.get("uid"),
            "unqkey": token_data.get("unqkey")
        }
    except requests.RequestException as e:
        return {"error": f"Access token fetch failed: {str(e)}"}


def load_public_key():
    with open("public_key.pem", "r") as f:
        return f.read()

algorithms=ALGORITHM
public_key = load_public_key()
token = TOKEN
audience=AUDIENCE

def validate_token(token: str, public_key: str, algorithms:str,audience:str) -> Dict:
    try:
        payload = jwt.decode(token, key=public_key, algorithms=algorithms,audience=audience
)
        return payload  # valid token
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError as e:
        return {"error": f"Invalid token: {str(e)}"}


#for sample testing   
if __name__ == "__main__":
    #Decode and validate token
    validated =validate_token(token, public_key, algorithms, audience)
    print("validated Token:", validated)

    if "error" in validated:
        print("Token is invalid. Exiting test.")
    else:
        #check for required fields
        required_fields = ["uid", "unqkey"]
        if all(field in validated for field in required_fields):
            #Send a test email using validated fields
            print("Token is valid.")
        else:
            print("validated token missing required fields. Exiting.")


def authenticate_and_get_claims():
    """
    Fetches an access token, validates it, and returns validated claims along with token, uid, and unqkey.
    Returns:
        dict: {
            "token": str,
            "uid": str,
            "unqkey": str,
            "claims": dict
        }
        OR
        dict: {
            "error": str
        }
    """
    access_info = get_access_token()
    if not access_info or "error" in access_info or not access_info.get("token"):
        return {"error": "Failed to retrieve access token."}
    token = access_info["token"]
    uid = access_info["uid"]
    unqkey = access_info["unqkey"]
    validated = validate_token(token, public_key, algorithms)
    if "error" in validated:
        return {"error": "Invalid token."}
    return {
        "token": token,
        "uid": uid,
        "unqkey": unqkey,
        "claims": validated
    }
