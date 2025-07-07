# Prestige Genie CMS
This document describes a multi-agent application demonstrating how to orchestrate conversations between different agents to schedule a meeting.

This application contains agents as below:
*   **Host Agent**: The primary agent that orchestrates the scheduling task.
*   **CMS Agent**: An agent communicates with CMS database and retrive data according to user query.

## Setup and Deployment

### Prerequisites

Before running the application locally, ensure you have the following installed:

1. **python 3.12** Python 3.12 is required to run a2a-sdk 
2. **set up .env** 

Create a `.env` file in the root of the `a2a_friend_scheduling` directory with your Google API Key:
```
GOOGLE_API_KEY="your_api_key_here" 
DATABASE_API_URL="your_database_api_url_here"
GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

## Run the Agents

You will need to run all agent in a separate terminal window. by below commands

### Terminal 1: Run All Remote Agent
```bash
python run_all_agents.py
```

### Terminal 2: Run Host Agent
```bash
cd host_agent_adk
uv venv
source .venv/bin/activate
uv run --active adk web
```

## Interact with the Host Agent

Once all agents are running, the host agent will begin the process. You can view the interaction in the terminal output of the `host_agent`.
