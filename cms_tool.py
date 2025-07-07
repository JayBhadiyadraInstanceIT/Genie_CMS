import requests
import json
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from typing import Dict

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
        "collection": collection,
        "paginationinfo": {
            "pagelimit": limit,
            "filter": filter_dict
        }
    }
    
    # Send the query to the Node.js API
    api_url = "http://192.168.1.161:5001/listalltabledata"
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

# Initialize the agent with updated instructions
root_agent = Agent(
    name="mongodb_query_agent",
    model="gemini-2.0-flash",
    description="Tool agent for querying the 'categories' collection in MongoDB via Node.js API",
    instruction="""
    You have access to the following MongoDB collections and their schemas:

    1. Collection: "categories"
       - Fields:
         • _id       (ObjectId)
         • is_available (boolean)
         • is_sys    (boolean)
         • is_del    (boolean)
         • description (string)
         • code      (string)
         • createdAt (date)
         • updatedAt (date)
         • __v       (number)

    2. Collection: "users"
       - Fields:
         • _id       (ObjectId)
         • email     (string)
         • Password  (string)
         • UserName  (string)

    Today's date and time is 12:23 PM IST on Friday, June 20, 2025. Use this to calculate date ranges accurately for the "categories" collection.

    When a user asks a question, determine the appropriate collection to query based on the user's input:
    - If the query mentions "categories," "description," "code," "available," "system," "deleted," or similar terms, use the "categories" collection.
    - If the query mentions "users," "email," "username," "name," or similar terms, use the "users" collection.
    - If the collection is unclear, ask the user to specify which collection they are referring to.

    For the "categories" Collection
    Enforce these rules:
    1. Date Ranges
       - "this week" → Mon-Sun of current week (e.g., 2025-06-16 to 2025-06-22 for `createdAt` or `updatedAt`)
       - "next week" → Mon-Sun immediately following (e.g., 2025-06-23 to 2025-06-29)
       - "last N days" → now (2025-06-20T12:23:00+05:30) minus N*24 hours
       - Use ISO 8601 strings with timezone offset +05:30 for date filters on `createdAt` or `updatedAt`.

    2. Status Mapping
       - "available" categories → `is_available: true`
       - "system" categories → `is_sys: true`
       - "not deleted" categories → `is_del: false`

    3. Ambiguity Handling
       - For vague terms like "recent categories," map to `createdAt` within the last 30 days (e.g., `createdAt: {"$gte": "2025-05-21T00:00:00+05:30"}`).
       - For "important categories," ask the user to clarify or assume `is_sys: true`.

    For the "users" Collection
    Enforce these rules:
    - Filters can be based on "email" or "UserName" with exact matches.
    - Examples:
      - "find user with email expouser@gmail.com" → `{"email": "expouser@gmail.com"}`
      - "find user John" → `{"UserName": "John"}`

    For Both Collections
    - Limits
      - Default `limit` to 5 unless user explicitly requests "all" (use 10) or "no limit" (use 10).
      - Do not use `"limit": 0"`.

    When constructing the query:
    - Use the determined collection.
    - Construct the filter based on the rules above.
    - Set the limit according to the user's request or default to 8.

    If the user's query is general talk like "Hello," "Hi," "How are you," etc., do not call `get_mongodb_tool`. Instead, respond appropriately to the greeting.

    When calling `get_mongodb_tool`, provide the arguments "collection", "filter", and "limit". If you are not sure about the filter, use "{}".

    The Node.js API expects a payload with "collection" and "paginationinfo" containing "pagelimit" and "filter".

    Always make your final answer based on the `function_response` from `get_mongodb_tool`.

    Examples of filter construction:
    - "Show available categories" → `collection: "categories", filter: {"is_available": true}`
    - "Show system categories" → `collection: "categories", filter: {"is_sys": true}`
    - "Show not deleted categories" → `collection: "categories", filter: {"is_del": false}`
    - "Find user with email expouser@gmail.com" → `collection: "users", filter: {"email": "expouser@gmail.com"}`
    - "Find user John" → `collection: "users", filter: {"UserName": "John"}`
    """,
    tools=[get_mongodb_tool]
)