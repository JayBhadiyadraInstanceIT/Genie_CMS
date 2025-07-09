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
    # Parse JSON string for filter
    try:
        filter_dict = json.loads(filter)
        projection_dict = json.loads(projection)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON in filter: {str(e)}"}
    
    # Construct the query dictionary for the Node.js API
    query = {
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
