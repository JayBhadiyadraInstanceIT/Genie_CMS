import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
from google.adk.sessions import DatabaseSessionService
from host.agent import host_agent_instance
import json
from request_schema import (
    CreateSessionPayload, 
    ChatRequest
)

session_db_url = "sqlite:///./cms_host_agent_sessions.db"
app = FastAPI()
db_svc = DatabaseSessionService(db_url=session_db_url)

@app.get("/", tags=["CMS Agent"])
async def welcome():
    return {"message":"welcome to CMS Agent"}


@app.post("/create_user_session", tags=["CMS Agent"])
async def create_user_session(payload: CreateSessionPayload):
    """Create a new user session with optional initial state"""
    try:
        # Get or create user
        user = host_agent_instance._get_or_create_user(payload.user_id)
        
        # Generate session ID if not provided
        session_id = payload.session_id or str(uuid.uuid4())
        
        # Default state if not provided
        initial_state = payload.state or {
            "conversation_history": [],
            "pending_bookings": {},
            "friend_responses": {},
            "current_scheduling_task": None
        }
        
        # Create session in database
        session = await db_svc.create_session(
            app_name=host_agent_instance._agent.name,
            user_id=user.id,
            state=initial_state,
            session_id=session_id
        )
        
        return {
            "user_id": user.id,
            "session": session,
            "app_name": host_agent_instance._agent.name,
            "status": "created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")


@app.get("/get_user_sessions_list/{user_id}", tags=["CMS Agent"])
async def get_user_sessions(user_id: str):
    """Get all sessions for a specific user"""
    try:
        sessions = await db_svc.list_sessions(
            app_name=host_agent_instance._agent.name,
            user_id=user_id
        )
        
        if sessions is None or not sessions.sessions:
            return {"user_id": user_id, "sessions": []}
        
        session_list = []
        for session in sessions.sessions:
            session_list.append({
                "session_id": session.id,
            })
        
        return {"user_id": user_id, "sessions": session_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@app.get("/get_session_details/{user_id}/{session_id}", tags=["CMS Agent"])
async def get_session(user_id: str, session_id: str):
    """Get details of a specific session"""
    try:
        session = await db_svc.get_session(
            app_name=host_agent_instance._agent.name,
            user_id=user_id,
            session_id=session_id
        )
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "user_id": user_id,
            "session_id": session.id,
            "state": session.state,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")


@app.post("/run_custom", tags=["CMS Agent"])
async def run_custom(payload: ChatRequest):
    """Run agent with ADK-compatible format but with database persistence"""
    try:
        message_text = "".join(part.text for part in payload.new_message.parts)
        
        if not message_text:
            raise HTTPException(status_code=400, detail="No text found in message parts")
        
        # Check if session exists, create if not
        session = await db_svc.get_session(
            app_name=payload.app_name,
            user_id=payload.user_id,
            session_id=payload.session_id
        )
        
        if session is None:
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
            response_chunks.append(chunk)
        
        # Save conversation to database
        await save_conversation_to_db(
            payload.user_id,
            payload.session_id,
            message_text,
            response_chunks
        )
        
        # Return combined response
        full_response = "".join([chunk.get("content", "") for chunk in response_chunks])
        return {
            "user_id": payload.user_id,
            "session_id": payload.session_id,
            "response": full_response,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in run_custom: {str(e)}")


@app.post("/run_custom_sse", tags=["CMS Agent"])
async def run_custom_sse(payload: ChatRequest):
    """Stream agent response with ADK-compatible format"""
    try:
        message_text = "".join(part.text for part in payload.new_message.parts)
        
        if not message_text:
            raise HTTPException(status_code=400, detail="No text found in message parts")
        
        # Check if session exists, create if not
        session = await db_svc.get_session(
            app_name=payload.app_name,
            user_id=payload.user_id,
            session_id=payload.session_id
        )
        
        if session is None:
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
                    conversation_chunks.append(chunk)
                    chunk_data = json.dumps({"chunk": chunk, "type": "partial"})
                    yield f"data: {chunk_data}\n\n"
                
                # Send completion signal
                final_data = json.dumps({"type": "complete", "message": "Stream completed"})
                yield f"data: {final_data}\n\n"
                
                # Save conversation after streaming
                await save_conversation_to_db(
                    payload.user_id,
                    payload.session_id,
                    message_text,
                    conversation_chunks
                )
                
            except Exception as e:
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
        raise HTTPException(status_code=500, detail=f"Error in run_custom_sse: {str(e)}")


async def save_conversation_to_db(user_id: str, session_id: str, user_message: str, agent_responses: List[str]):
    """Save conversation to database"""
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
            
    except Exception as e:
        print(f"Error saving conversation to database: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
