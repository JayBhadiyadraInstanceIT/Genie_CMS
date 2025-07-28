import uuid
import re
import ast
import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from host.agent import host_agent_instance
import json
from schema import (
    CreateSessionPayload, 
    ChatRequest
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cms_agent")
# session_db_url = "sqlite:///./cms_host_agent_sessions.db"
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["key", "token", "unqkey", "domainname", "resheader"],
)
# db_svc = DatabaseSessionService(db_url=session_db_url)
db_svc = InMemorySessionService()

@app.get("/", tags=["CMS Agent"])
async def welcome():
    logger.info("GET / (welcome) called")
    return {"message":"welcome to CMS Agent"}


@app.post("/create_user_session", tags=["CMS Agent"])
async def create_user_session(payload: CreateSessionPayload):
    logger.info(f"POST /create_user_session called with payload: user_id={payload.user_id}, session_id={payload.session_id}")
    """Create a new user session with optional initial state"""
    try:
        # Get or create user
        user = host_agent_instance._get_or_create_user(payload.user_id)
        
        # Generate session ID if not provided
        session_id = payload.session_id or str(uuid.uuid4())
        
        # Default state if not provided
        # initial_state = payload.state or {
        #     "conversation_history": [],
        #     "pending_bookings": {},
        #     "friend_responses": {},
        #     "current_scheduling_task": None
        # }
        
        # Create session in database
        session = await db_svc.create_session(
            app_name=host_agent_instance._agent.name,
            user_id=user.id,
            state=payload.state or {},
            session_id=session_id
        )
        logger.info(f"Created session: user_id={user.id}, session_id={session_id}")

        resp = {
            "user_id": user.id,
            "session_id": session.id,
            "app_name": host_agent_instance._agent.name,
            "status": "created",
            "state": session.state if session.state else {}
        }

        return resp
        # return {
        #     "user_id": user.id,
        #     "session": session,
        #     "app_name": host_agent_instance._agent.name,
        #     "status": "created"
        # }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")


@app.get("/get_user_sessions_list/{user_id}", tags=["CMS Agent"])
async def get_user_sessions(user_id: str):
    """Get all sessions for a specific user"""
    logger.info(f"GET /get_user_sessions_list for user_id={user_id}")
    try:
        sessions = await db_svc.list_sessions(
            app_name=host_agent_instance._agent.name,
            user_id=user_id
        )
        
        if sessions is None or not sessions.sessions:
            logger.info(f"Found sessions count={len(session_list)} for user_id={user_id}")
            return {"user_id": user_id, "sessions": []}
        
        session_list = []
        for session in sessions.sessions:
            session_list.append({
                "session_id": session.id,
            })
        logger.info(f"Found sessions count={len(session_list)} for user_id={user_id}")
        return {"user_id": user_id, "sessions": session_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@app.get("/get_session_details/{user_id}/{session_id}", tags=["CMS Agent"])
async def get_session(user_id: str, session_id: str):
    """Get details of a specific session"""
    logger.info(f"GET /get_session_details user_id={user_id}, session_id={session_id}")
    try:
        session = await db_svc.get_session(
            app_name=host_agent_instance._agent.name,
            user_id=user_id,
            session_id=session_id
        )
        
        if session is None:
            logger.warning(f"Session not found: user_id={user_id}, session_id={session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        logger.info(f"Retrieved session details for session_id={session_id}")
        
        resp = {
            "user_id": user_id,
            "session_id": session.id,
            "state": session.state if session.state else {}
        }

        logger.info(f"Retrieved session details for session_id={session_id}: state keys = {list(resp['state'].keys())}")
        return resp
        # return {
        #     "user_id": user_id,
        #     "session_id": session.id,
        #     "state": session.state,
        # }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session details: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")


@app.post("/chat", tags=["CMS Agent"])
async def run_custom(payload: ChatRequest):
    logger.info(f"POST /run_custom called by user={payload.user_id}, session={payload.session_id}")
    """Run agent with ADK-compatible format but with database persistence"""
    try:
        message_text = "".join(part.text for part in payload.new_message.parts)
        logger.info(f"User message text: {message_text!r}")
        if not message_text:
            logger.warning("No text found in message parts")
            raise HTTPException(status_code=400, detail="No text found in message parts")
        
        # Check if session exists, create if not
        session = await db_svc.get_session(
            app_name=payload.app_name,
            user_id=payload.user_id,
            session_id=payload.session_id
        )
        
        if session is None:
            logger.info("Session not found, creating new session")
            # Create session if it doesn't exist
            initial_state = {
                "conversation_history": [],
                "pending_bookings": {},
                "friend_responses": {},
                "current_scheduling_task": None
            }
            session = await db_svc.create_session(
                app_name=payload.app_name,
                user_id=payload.user_id,
                state=initial_state,
                session_id=payload.session_id
            )
        
        # Collect all response chunks
        response_chunks = []
        async for chunk in host_agent_instance.stream( 
            message_text,
            payload.session_id, 
        ):
            logger.info(f"Received chunk: {chunk}")
            response_chunks.append(chunk)
        
        # Save conversation to database
        await save_conversation_to_db(
            payload.user_id,
            payload.session_id,
            message_text,
            response_chunks
        )
        
        # Return combined response
        # full_response = "".join([chunk.get("content", "") for chunk in response_chunks])
        # full_response = "".join(str(chunk.get("content", "")) for chunk in response_chunks)
        # 1) raw concatenation
        raw = "".join(str(chunk.get("content", "")) for chunk in response_chunks)
        logger.info(f"Full response: {raw!r}")

        # 2) extract JSON substring
        # match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        # cleaned = match.group(0) if match else raw
        # logger.info(f"Cleaned JSON candidate: {cleaned}")

        # 3) parse
        try:
            data = json.loads(raw)
            logger.info(f"JSON loads: {data}")
        #     json_str = json.dumps(data, ensure_ascii=False)
        #     logger.info(f"JSON string: {json_str}")
        # except json.JSONDecodeError:
        #     logger.error("JSON parse failed, falling back to raw text")
        #     data = {"text": cleaned, "project_inquiry": False}
        #     json_str = json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError:
            logger.warning("JSON.loads failed, trying ast.literal_eval")
            try:
                data = ast.literal_eval(raw)
                logger.info(f"ast.literal_eval done: {data}")
            except Exception as e:
                logger.error(f"ast.literal_eval also failed: {e}")
                data = {"text": raw}
        return {
            "user_id": payload.user_id,
            "session_id": payload.session_id,
            "response": data,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in run_custom: {e}")
        raise HTTPException(status_code=500, detail=f"Error in run_custom: {str(e)}")


@app.post("/chat_sse", tags=["CMS Agent"])
async def run_custom_sse(payload: ChatRequest):
    """Stream agent response with ADK-compatible format"""
    logger.info(f"POST /run_custom_sse called: user={payload.user_id}, session={payload.session_id}")
    try:
        message_text = "".join(part.text for part in payload.new_message.parts)
        logger.info(f"SSE user message: {message_text!r}")
        if not message_text:
            logger.warning("No text found in message parts for SSE")
            raise HTTPException(status_code=400, detail="No text found in message parts")
        
        # Check if session exists, create if not
        session = await db_svc.get_session(
            app_name=payload.app_name,
            user_id=payload.user_id,
            session_id=payload.session_id
        )
        
        if session is None:
            logger.info("Session not found for SSE; creating new one")
            initial_state = {
                "conversation_history": [],
                "pending_bookings": {},
                "friend_responses": {},
                "current_scheduling_task": None
            }
            session = await db_svc.create_session(
                app_name=payload.app_name,
                user_id=payload.user_id,
                state=initial_state,
                session_id=payload.session_id
            )
        
        conversation_chunks = []

        async def event_generator():
            try:
                async for chunk in host_agent_instance.stream( 
                    message_text,
                    payload.session_id, 
                ):
                    logger.info(f"SSE chunk: {chunk}")
                    conversation_chunks.append(chunk)
                    chunk_data = json.dumps({"chunk": chunk, "type": "partial"})
                    yield f"data: {chunk_data}\n\n"
                
                # Send completion signal
                final_data = json.dumps({"type": "complete", "message": "Stream completed"})
                logger.info("SSE stream completed")
                yield f"data: {final_data}\n\n"
                
                # Save conversation after streaming
                await save_conversation_to_db(
                    payload.user_id,
                    payload.session_id,
                    message_text,
                    conversation_chunks
                )
                logger.info("Conversation saved after SSE")
                
            except Exception as e:
                logger.error(f"Error in SSE streaming: {e}")
                error_data = json.dumps({"type": "error", "error": str(e)})
                yield f"data: {error_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in run_custom_sse: {e}")
        raise HTTPException(status_code=500, detail=f"Error in run_custom_sse: {str(e)}")


async def save_conversation_to_db(user_id: str, session_id: str, user_message: str, agent_responses: List[str]):
    """Save conversation to database"""
    logger.info(f"Saving conversation to DB for user={user_id}, session={session_id}")
    try:
        # Get current session
        session = await db_svc.get_session(
            app_name=host_agent_instance._agent.name,
            user_id=user_id,
            session_id=session_id
        )
        
        if session:
            # Update conversation history in session state
            current_state = session.state or {}
            if "conversation_history" not in current_state:
                current_state["conversation_history"] = []
            
            # Add new conversation turn
            conversation_turn = {
                "timestamp": "2024-01-01T00:00:00",  # You might want to use actual timestamp
                "user_message": user_message,
                "agent_response": "".join(agent_responses),
                "chunks": agent_responses
            }
            current_state["conversation_history"].append(conversation_turn)
            
            # Update session state
            await db_svc.append_event(
                app_name=host_agent_instance._agent.name,
                user_id=user_id,
                session_id=session_id,
                state=current_state
            )
            logger.info("Conversation appended to session state")
    except Exception as e:
        logger.error(f"Error saving conversation to database: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="192.168.1.14", port=9000, log_level="info")