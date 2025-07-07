import logging
import os
import sys

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import create_agent
from agent_executor import RealEstateAgentExecutor
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import (
    REMOTE_1_AGENT_NAME,
    REMOTE_1_AGENT_VERSION,
    REMOTE_1_AGENT_HOST,
    REMOTE_1_AGENT_PORT,
    REMOTE_1_AGENT_DEFAULT_USER_ID,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""
    pass


class DatabaseConnectionError(Exception):
    """Exception for database connection issues."""
    pass


def main():
    """Starts the agent server."""

    try:
        # Check for API key only if Vertex AI is not configured
        if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
            if not os.getenv("GOOGLE_API_KEY"):
                raise MissingAPIKeyError(
                    "GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
                )

        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="retrieve_information",
            name="Retrieve Real-Estate Project Data",
            description=(
                "Queries CMS database to fetch detailed real-estate project information. "
                "Supports tables: aboutus, projectamenities, projectattributes, "
                "projectcategory, projectgalleries, projecthighlights, projectlayouts, siteprogress, "
                "projectspecifications, projects, reraregistration, walkthroughs, brochures."
            ),
            tags=["Real-Estate", "Property", "Project-Details", "Amenities",
                  "Attributes", "Pricing", "Gallery", "Highlights", "Layouts",
                  "Progress", "Specifications", "RERA", "Walkthrough", "Brochure",
                  ],
            examples=["Give me details for Project X",
                      "List out the amenities for Project X",
                      "Show me starting_price for Project X",
                      "Get brochure list for Project Y",
                      "Fetch layout images for Project Z",
                      ],
        )
        agent_card = AgentCard(
            name=REMOTE_1_AGENT_NAME,
            description=(
                "An agent that retrieves comprehensive real-estate project data from CMS database "
                "including amenities, pricing, layouts, galleries, specifications, RERA info, progress, "
                "walkthroughs, and brochures."
            ),
            url=f"http://{REMOTE_1_AGENT_HOST}:{REMOTE_1_AGENT_PORT}/",
            version=REMOTE_1_AGENT_VERSION,
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            capabilities=capabilities,
            skills=[skill],
        )

        adk_agent = create_agent()
        runner = Runner(
            app_name=agent_card.name,
            agent=adk_agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            # session_service=DatabaseSessionService(db_url=db_url),
            memory_service=InMemoryMemoryService(),
        )
        agent_executor = RealEstateAgentExecutor(runner)

        request_handler = DefaultRequestHandler(
            agent_executor=agent_executor,
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=REMOTE_1_AGENT_HOST, port=REMOTE_1_AGENT_PORT)
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()



# import logging
# import os

# import uvicorn
# from a2a.server.apps import A2AStarletteApplication
# from a2a.server.request_handlers import DefaultRequestHandler
# from a2a.server.tasks import InMemoryTaskStore
# from a2a.types import (
#     AgentCapabilities,
#     AgentCard,
#     AgentSkill,
# )
# from agent import create_agent
# from agent_executor import DatabaseAgentExecutor  # Renamed for clarity
# from dotenv import load_dotenv
# from google.adk.artifacts import InMemoryArtifactService
# from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService

# load_dotenv()

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Constants
# AGENT_NAME = "CMS Agent"
# AGENT_VERSION = "1.0.0"
# HOST = "localhost"
# PORT = 10002
# DEFAULT_USER_ID = "database_agent_user"


# class MissingAPIKeyError(Exception):
#     """Exception for missing API key."""
#     pass


# class DatabaseConnectionError(Exception):
#     """Exception for database connection issues."""
#     pass


# def validate_environment():
#     """Validate required environment variables and configurations."""
#     # Check for API key only if Vertex AI is not configured
#     if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
#         if not os.getenv("GOOGLE_API_KEY"):
#             raise MissingAPIKeyError(
#                 "GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
#             )
    
#     # Validate database API endpoint
#     db_api_url = os.getenv("DATABASE_API_URL", "http://192.168.1.161:5001")
#     if not db_api_url:
#         raise DatabaseConnectionError("DATABASE_API_URL not configured")
    
#     return db_api_url


# def create_agent_card(host: str, port: int) -> AgentCard:
#     """Create and configure the agent card with capabilities and skills."""
#     capabilities = AgentCapabilities(streaming=True)
    
#     skill = AgentSkill(
#         id="retrieve_information",
#         name="Retrieve Real-Estate Project Data",
#         description=(
#                 "Queries CMS database to fetch detailed real-estate project information. "
#                 "Supports tables: about_us, project_amenities, project_attributes, "
#                 "proj_category, proj_galleries, proj_highlights, proj_layouts, site_progress, "
#                 "proj_specifications, projs, rera_registration, walkthroughs, brochures."
#             ),
#         tags=["Real-Estate", "Property", "Project-Details", "Amenities",
#                   "Attributes", "Pricing", "Gallery", "Highlights", "Layouts",
#                   "Progress", "Specifications", "RERA", "Walkthrough", "Brochure",
#                   ],
#         examples=[
#             "Show me starting_price for Project X",
#             "Get brochure list for Project Y",
#             "Fetch layout images for Project Z",
#             "Show me all available categories",
#         ],
#     )
    
#     return AgentCard(
#         name=AGENT_NAME,
#         description=(
#                 "An agent that retrieves comprehensive real-estate project data from CMS database "
#                 "including amenities, pricing, layouts, galleries, specifications, RERA info, progress, "
#                 "walkthroughs, and brochures."
#             ),
#         url=f"http://{host}:{port}/",
#         version=AGENT_VERSION,
#         defaultInputModes=["text/plain"],
#         defaultOutputModes=["text/plain"],
#         capabilities=capabilities,
#         skills=[skill],
#     )


# def create_runner_and_executor(agent_card: AgentCard, db_api_url: str):
#     """Create the ADK runner and agent executor."""
#     adk_agent = create_agent(db_api_url)
    
#     runner = Runner(
#         app_name=agent_card.name,
#         agent=adk_agent,
#         artifact_service=InMemoryArtifactService(),
#         session_service=InMemorySessionService(),
#         memory_service=InMemoryMemoryService(),
#     )
    
#     agent_executor = DatabaseAgentExecutor(
#         runner=runner,
#         default_user_id=DEFAULT_USER_ID
#     )
    
#     return runner, agent_executor


# def main():
#     """Starts the database query agent server."""
#     try:
#         # Validate environment and get configuration
#         db_api_url = validate_environment()
        
#         # Create agent card
#         agent_card = create_agent_card(HOST, PORT)
        
#         # Create runner and executor
#         runner, agent_executor = create_runner_and_executor(agent_card, db_api_url)
        
#         # Create request handler and server
#         request_handler = DefaultRequestHandler(
#             agent_executor=agent_executor,
#             task_store=InMemoryTaskStore(),
#         )
        
#         server = A2AStarletteApplication(
#             agent_card=agent_card, 
#             http_handler=request_handler
#         )
        
#         logger.info(f"Starting {AGENT_NAME} server on {HOST}:{PORT}")
#         uvicorn.run(server.build(), host=HOST, port=PORT)
        
#     except MissingAPIKeyError as e:
#         logger.error(f"Configuration Error: {e}")
#         exit(1)
#     except DatabaseConnectionError as e:
#         logger.error(f"Database Configuration Error: {e}")
#         exit(1)
#     except Exception as e:
#         logger.error(f"An error occurred during server startup: {e}")
#         exit(1)


# if __name__ == "__main__":
#     main()