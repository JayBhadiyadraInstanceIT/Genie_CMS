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
