import sys
import os
import requests
import json
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from typing import Dict
from prompt import instruction

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import (
    REMOTE_1_AGENT_DATABASE_API_URL, 
    REMOTE_1_AGENT_DATABASE_DBNAME, 
    MODEL, 
    REMOTE_1_AGENT_NAME,
    )


def get_mongodb(collection: str, filter: str, limit: int) -> Dict:
    """
    Fetch data from MongoDB via the Node.js API using the provided query parameters.

    Args:
        collection (str): The name of the MongoDB collection (e.g., 'categories').
        filter (str): The filter criteria as a JSON string (e.g., '{"is_available": true}').
        limit (int): The maximum number of documents to return.

    Returns:
        dict: The data fetched from the MongoDB database via the API, or an error message.
    """
    # Parse JSON string for filter
    try:
        filter_dict = json.loads(filter)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON in filter: {str(e)}"}
    
    # Construct the query dictionary for the Node.js API
    query = {
        "dbname": REMOTE_1_AGENT_DATABASE_DBNAME,
        "collection": collection,
        "paginationinfo": {
            "pagelimit": limit,
            "filter": filter_dict
        }
    }
    
    # Send the query to the Node.js API
    api_url = REMOTE_1_AGENT_DATABASE_API_URL
    try:
        response = requests.post(api_url, json=query)
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses
        data = response.json()
        # Ensure the return value is always a dictionary
        if isinstance(data, list):
            return {"data": data}
        return data
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

# Create a FunctionTool without the 'declaration' parameter
get_mongodb_tool = FunctionTool(func=get_mongodb)


def create_agent() -> LlmAgent:
    """Constructs the ADK agent for RemoteAgent."""
    return LlmAgent(
        model=MODEL,
        name=REMOTE_1_AGENT_NAME,
        description="Specialized agent for querying MongoDB collections via Node.js API",
        instruction = instruction,
        tools=[get_mongodb_tool],
    )


# import requests
# import json
# import logging
# from datetime import datetime, timedelta
# from typing import Dict, Optional
# from google.adk.agents import LlmAgent
# from google.adk.tools import FunctionTool

# logger = logging.getLogger(__name__)

# # Default configuration
# DEFAULT_API_URL = "http://192.168.1.161:5001/listalltabledata"
# DEFAULT_LIMIT = 8
# MAX_LIMIT = 100


# def get_database_collection(collection: str, filter: str, limit: int, api_url: str = DEFAULT_API_URL) -> Dict:
#     """
#     Fetch data from MongoDB via the Node.js API using the provided query parameters.

#     Args:
#         collection (str): The name of the MongoDB collection (e.g., 'categories', 'users').
#         filter (str): The filter criteria as a JSON string (e.g., '{"is_available": true}').
#         limit (int): The maximum number of documents to return.
#         api_url (str): The API endpoint URL.

#     Returns:
#         dict: The data fetched from the MongoDB database via the API, or an error message.
#     """
#     # Validate inputs
#     if not collection or not isinstance(collection, str):
#         return {"error": "Collection name must be a non-empty string"}
    
#     if limit <= 0:
#         limit = DEFAULT_LIMIT
#     elif limit > MAX_LIMIT:
#         limit = MAX_LIMIT
    
#     # Parse and validate JSON filter
#     try:
#         filter_dict = json.loads(filter) if filter else {}
#     except json.JSONDecodeError as e:
#         logger.error(f"Invalid JSON in filter: {e}")
#         return {"error": f"Invalid JSON in filter: {str(e)}"}
    
#     # Construct the query dictionary for the Node.js API
#     query = {
#         "collection": collection,
#         "paginationinfo": {
#             "pagelimit": limit,
#             "filter": filter_dict
#         }
#     }
    
#     # Send the query to the Node.js API
#     try:
#         logger.info(f"Querying collection '{collection}' with filter: {filter_dict}")
#         response = requests.post(api_url, json=query, timeout=30)
#         response.raise_for_status()
        
#         data = response.json()
        
#         # Ensure the return value is always a dictionary
#         if isinstance(data, list):
#             return {"data": data, "count": len(data)}
#         elif isinstance(data, dict):
#             return data
#         else:
#             return {"data": data}
            
#     except requests.RequestException as e:
#         logger.error(f"API request failed: {e}")
#         return {"error": f"Database API request failed: {str(e)}"}
#     except json.JSONDecodeError as e:
#         logger.error(f"Invalid JSON response: {e}")
#         return {"error": f"Invalid response from database API: {str(e)}"}
#     except Exception as e:
#         logger.error(f"Unexpected error: {e}")
#         return {"error": f"Unexpected error occurred: {str(e)}"}


# def create_agent(api_url: str = DEFAULT_API_URL) -> LlmAgent:
#     """
#     Constructs the ADK agent for database querying.
    
#     Args:
#         api_url (str): The database API endpoint URL.
        
#     Returns:
#         LlmAgent: Configured agent for database operations.
#     """
#     # Create the function tool with the API URL
#     def get_database_collection_with_url(collection: str, filter: str, limit: int) -> Dict:
#         return get_database_collection(collection, filter, limit, api_url)
    
#     # Create a FunctionTool
#     database_tool = FunctionTool(func=get_database_collection_with_url)
    
#     # Get current date for context
#     current_date = datetime.now()
#     current_date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
    
#     return LlmAgent(
#         model="gemini-2.0-flash",
#         name="database_query_agent",
#         description="Specialized agent for querying MongoDB collections via Node.js API",
#         instruction=f"""
#             You are a database query agent that helps users retrieve information from MongoDB collections.

#             CURRENT DATE AND TIME: {current_date_str} IST (Indian Standard Time)

#             AVAILABLE COLLECTIONS AND SCHEMAS:

#             1. Collection: "categories"
#             Fields:
#             • _id (ObjectId) - Unique identifier
#             • is_available (boolean) - Whether category is available
#             • is_sys (boolean) - Whether category is system-generated
#             • is_del (boolean) - Whether category is deleted
#             • description (string) - Category description
#             • code (string) - Category code
#             • createdAt (date) - Creation timestamp
#             • updatedAt (date) - Last update timestamp
#             • __v (number) - Version number

#             2. Collection: "users"
#             Fields:
#             • _id (ObjectId) - Unique identifier
#             • email (string) - User email address
#             • Password (string) - User password (hashed)
#             • UserName (string) - User display name

#             QUERY PROCESSING RULES:

#             1. COLLECTION DETERMINATION:
#             - For queries about categories, descriptions, codes, availability, system flags, etc. → use "categories"
#             - For queries about users, emails, usernames, etc. → use "users"
#             - If unclear, ask the user to specify the collection

#             2. FILTER CONSTRUCTION:
#             Categories Collection:
#             - "available categories" → {{"is_available": true}}
#             - "system categories" → {{"is_sys": true}}
#             - "not deleted categories" → {{"is_del": false}}
#             - "categories with code X" → {{"code": "X"}}
#             - "categories containing description Y" → {{"description": {{"$regex": "Y", "$options": "i"}}}}
            
#             Users Collection:
#             - "user with email X" → {{"email": "X"}}
#             - "user named Y" → {{"UserName": "Y"}}
#             - "users with email containing Z" → {{"email": {{"$regex": "Z", "$options": "i"}}}}

#             3. DATE HANDLING:
#             - Use ISO format with timezone: "YYYY-MM-DDTHH:MM:SS+05:30"
#             - "today" → from start of today
#             - "yesterday" → from start of yesterday
#             - "last N days" → from N days ago to now
#             - "this week" → from Monday to Sunday of current week
#             - "last week" → from Monday to Sunday of previous week

#             4. LIMITS:
#             - Default limit: {DEFAULT_LIMIT}
#             - If user asks for "all" or "everything": use {MAX_LIMIT}
#             - Maximum allowed: {MAX_LIMIT}
#             - Never use limit 0

#             5. RESPONSE HANDLING:
#             - Always call get_database_collection_with_url for data queries
#             - For greetings/general conversation, respond normally without calling the function
#             - Base your final answer on the function response
#             - If the function returns an error, explain it to the user
#             - Format results in a clear, readable way

#             EXAMPLES:
#             - "Show me available categories" → collection="categories", filter='{{"is_available": true}}', limit=8
#             - "Find user john@example.com" → collection="users", filter='{{"email": "john@example.com"}}', limit=8
#             - "Get all system categories" → collection="categories", filter='{{"is_sys": true}}', limit=8

#             Remember: Always provide helpful, clear responses and handle errors gracefully.
#                     """,
#         tools=[database_tool],
#     )