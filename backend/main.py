import os
import json
import asyncio
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Google ADK imports
from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.genai.types import Content, Part, Blob, Modality

# Import agents
from agents import (
    greeting_agent,
    modem_install_agent as modem_agent,
    billing_agent,
    tech_support_agent,
    route_to_agent
)

import database

# Load environment variables
load_dotenv()

app = FastAPI()

# Initialize Database
database.init_db()

# Note: We will initialize InMemoryRunner dynamically in the websocket endpoint
# to support different agents per session

# Store active connections and chat history in memory for active sessions
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_connections: List[WebSocket] = []
        self.session_messages: Dict[str, List[Dict]] = {} # Store messages for active sessions
        self.active_approvals: Dict[str, Dict] = {} # Store active approval requests
        self.active_agent_names: Dict[str, str] = {} # Track active agent per client
        self.session_metadata: Dict[str, Dict] = {} # Track session status and metadata

    async def connect(self, websocket: WebSocket, client_id: str, role: str):
        await websocket.accept()
        if role == "agent":
            self.agent_connections.append(websocket)
            # Sync state to new agent
            await websocket.send_json({
                "type": "sync_state",
                "active_chats": list(self.session_messages.keys()),
                "messages": self.session_messages,
                "approvals": self.active_approvals,
                "metadata": self.session_metadata
            })
        else:
            self.active_connections[client_id] = websocket
            if client_id not in self.session_messages:
                self.session_messages[client_id] = []
                # Initialize metadata
                self.session_metadata[client_id] = {
                    "status": "bot_only",
                    "last_activity": None,
                    "sentiment_score": 0.0,
                    "requires_approval": False
                }

    def disconnect(self, websocket: WebSocket, client_id: str, role: str):
        if role == "agent":
            if websocket in self.agent_connections:
                self.agent_connections.remove(websocket)
        else:
            if client_id in self.active_connections:
                del self.active_connections[client_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_agents(self, message: dict):
        for connection in self.agent_connections:
            try:
                await connection.send_json(message)
            except:
                pass

    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
            
    def add_message(self, client_id: str, message: dict):
        if client_id not in self.session_messages:
            self.session_messages[client_id] = []
        # Add timestamp if missing or None
        import datetime
        if 'timestamp' not in message or message['timestamp'] is None:
            message['timestamp'] = datetime.datetime.now().isoformat()
        self.session_messages[client_id].append(message)
        
        # Update last activity
        if client_id in self.session_metadata:
            self.session_metadata[client_id]["last_activity"] = message['timestamp']
        
    def add_approval(self, client_id: str, approval_data: dict):
        self.active_approvals[client_id] = approval_data
        if client_id in self.session_metadata:
            self.session_metadata[client_id]["requires_approval"] = True
            # Approval implies hard handoff/blocking
            self.session_metadata[client_id]["status"] = "hard_handoff"
        
    def remove_approval(self, client_id: str):
        if client_id in self.active_approvals:
            del self.active_approvals[client_id]
        if client_id in self.session_metadata:
            self.session_metadata[client_id]["requires_approval"] = False
            # If status was hard_handoff due to approval, revert to bot_only or keep as is?
            # Usually after approval, bot continues, so maybe revert to bot_only unless agent took over
            if self.session_metadata[client_id]["status"] == "hard_handoff":
                 self.session_metadata[client_id]["status"] = "bot_only"

    def update_session_status(self, client_id: str, status: str, sentiment: float = None):
        if client_id in self.session_metadata:
            self.session_metadata[client_id]["status"] = status
            if sentiment is not None:
                self.session_metadata[client_id]["sentiment_score"] = sentiment

    def get_messages(self, client_id: str) -> List[Dict]:
        return self.session_messages.get(client_id, [])
        
    def end_session(self, client_id: str):
        print(f"Ending session for {client_id}. Available sessions: {list(self.session_messages.keys())}")
        if client_id in self.session_messages:
            messages = self.session_messages[client_id]
            print(f"Saving {len(messages)} messages for {client_id}")
            database.save_chat_session(client_id, client_id, messages, "completed")
            # Clean up memory
            del self.session_messages[client_id]
            if client_id in self.active_approvals:
                del self.active_approvals[client_id]
            if client_id in self.active_agent_names:
                del self.active_agent_names[client_id]
            if client_id in self.session_metadata:
                del self.session_metadata[client_id]
            if client_id in self.active_connections:
                 # Optionally close connection or notify client
                 pass
        else:
            print(f"Session {client_id} not found in memory")

manager = ConnectionManager()

# Simple keyword-based routing (can be enhanced with LLM later)
def route_to_agent(message: str, current_agent_name: str = None):
    """Route message to appropriate agent based on keywords."""
    msg_lower = message.lower()
    
    # Check for strong topic switches
    if any(keyword in msg_lower for keyword in ["install", "modem", "setup", "set up"]):
        return modem_install_agent
    
    if any(keyword in msg_lower for keyword in ["bill", "charge", "credit", "refund", "movie", "rental"]):
        return billing_agent
    
    if any(keyword in msg_lower for keyword in ["internet", "slow", "connection", "wifi", "speed", "down"]):
        return tech_support_agent
    
    # If no strong topic, stick to current agent if it exists
    if current_agent_name:
        agents_map = {
            "greeting_agent": greeting_agent,
            "modem_install_agent": modem_install_agent,
            "billing_agent": billing_agent,
            "tech_support_agent": tech_support_agent
        }
        return agents_map.get(current_agent_name, greeting_agent)
    
    # Default to greeting agent
    return greeting_agent


async def agent_to_client_messaging(websocket: WebSocket, live_events, client_id: str):
    """Forward agent events to WebSocket client"""
    print(f"Starting agent_to_client_messaging for {client_id}")
    try:
        accumulated_response = ""
        async for event in live_events:
            print(f"Received event from agent: {event}")
            try:
                # Extract text from event and accumulate
                if event.content and hasattr(event.content, 'parts'):
                    text_parts = [part.text for part in event.content.parts if part.text]
                    if text_parts:
                        response_text = "".join(text_parts)
                        print(f"Agent response text: {response_text} (partial={event.partial}, turn_complete={event.turn_complete})")
                        # Accumulate the response
                        accumulated_response = response_text
                
                # Send accumulated response when turn is complete
                if event.turn_complete and accumulated_response:
                    print(f"Sending complete response: {accumulated_response}")
                    
                    # Create message object with timestamp
                    bot_msg = {
                        "sender": "bot",
                        "content": accumulated_response,
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    }
                    
                    # Add to session history FIRST
                    manager.add_message(client_id, bot_msg)
                    
                    # Send to customer
                    await websocket.send_json({
                        "sender": "bot",
                        "content": accumulated_response
                    })
                    
                    # Broadcast to agents (for monitoring/history)
                    await manager.broadcast_to_agents({
                        "type": "message",
                        "sender": "bot",
                        "content": accumulated_response,
                        "clientId": client_id,
                        "timestamp": bot_msg["timestamp"]
                    })
                    
                    # Reset accumulator for next turn
                    accumulated_response = ""
                
                # Check for tool calls / approval requests
                if event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if part.function_call:
                            print(f"Function call detected: {part.function_call.name}")
                            # Check if it's an approval request
                            if part.function_call.name == "request_credit_approval":
                                approval_data = {
                                    "type": "approval_request",
                                    "clientId": client_id,
                                    "amount": part.function_call.args.get("amount"),
                                    "reason": part.function_call.args.get("reason")
                                }
                                manager.add_approval(client_id, approval_data)
                                await manager.broadcast_to_agents(approval_data)
                            elif part.function_call.name == "request_tech_dispatch":
                                approval_data = {
                                    "type": "approval_request",
                                    "clientId": client_id,
                                    "amount": 0,
                                    "reason": part.function_call.args.get("reason")
                                }
                                manager.add_approval(client_id, approval_data)
                                await manager.broadcast_to_agents(approval_data)
                            elif part.function_call.name == "trigger_soft_handoff":
                                handoff_data = {
                                    "type": "soft_handoff",
                                    "clientId": client_id,
                                    "reason": part.function_call.args.get("reason"),
                                    "sentimentScore": part.function_call.args.get("sentiment_score")
                                }
                                manager.update_session_status(client_id, "soft_handoff", part.function_call.args.get("sentiment_score"))
                                await manager.broadcast_to_agents(handoff_data)
                                await manager.send_to_client(client_id, {"type": "status_change", "status": "soft_handoff"})
                            elif part.function_call.name == "trigger_hard_handoff":
                                handoff_data = {
                                    "type": "hard_handoff",
                                    "clientId": client_id,
                                    "reason": part.function_call.args.get("reason")
                                }
                                manager.update_session_status(client_id, "hard_handoff")
                                await manager.broadcast_to_agents(handoff_data)
                                await manager.send_to_client(client_id, {"type": "status_change", "status": "hard_handoff"})

            except Exception as e:
                print(f"Error processing event: {e}")
    except Exception as e:
        print(f"Error in agent_to_client_messaging loop: {e}")
    finally:
        print(f"Exiting agent_to_client_messaging for {client_id}")

async def client_to_agent_messaging(websocket: WebSocket, live_request_queue: LiveRequestQueue, client_id: str):
    """Forward client messages to ADK agent"""
    print(f"Starting client_to_agent_messaging for {client_id}")
    while True:
        try:
            data = await websocket.receive_text()
            print(f"Received message from client {client_id}: {data}")
            message_data = json.loads(data)
            
            # Store message in history
            msg_obj = {
                "sender": "customer",
                "content": message_data["content"],
                "timestamp": message_data.get("timestamp")
            }
            manager.add_message(client_id, msg_obj)

            # Broadcast customer message to agents
            await manager.broadcast_to_agents({
                "type": "message",
                "sender": "customer",
                "content": message_data["content"],
                "clientId": client_id,
                "timestamp": msg_obj["timestamp"]
            })
            
            # Create Content object
            content = Content(
                role="user",
                parts=[Part.from_text(text=message_data["content"])]
            )
            
            # Send to agent via queue
            print(f"Sending content to agent queue: {content}")
            live_request_queue.send_content(content=content)
            
        except WebSocketDisconnect:
            print(f"WebSocket disconnected in client_to_agent_messaging for {client_id}")
            break
        except Exception as e:
            print(f"Error in client_to_agent_messaging: {e}")
            break

@app.websocket("/ws/{client_id}/{role}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, role: str):
    await manager.connect(websocket, client_id, role)
    
    try:
        if role == "agent":
            # Agent logic remains simple (receive broadcasts)
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle Agent Actions
                action_type = message_data.get("type")
                target_client_id = message_data.get("targetClientId")
                
                if action_type == "approval_response":
                    approved = message_data.get("approved")
                    manager.remove_approval(target_client_id) # Remove from active approvals
                    
                    if approved:
                        response = "Supervisor approved your request."
                    else:
                        response = "Supervisor declined your request."
                    
                    bot_msg = {"sender": "bot", "content": response}
                    manager.add_message(target_client_id, bot_msg)
                    
                    await manager.send_to_client(target_client_id, bot_msg)
                    # Echo back to agents to update UI
                    await manager.broadcast_to_agents({
                        "type": "message",
                        "sender": "bot",
                        "content": response,
                        "clientId": target_client_id
                    })
                    
                elif action_type == "takeover_message":
                     # Check if this is the first agent message to send "Joined" notification
                     messages = manager.get_messages(target_client_id)
                     last_sender = messages[-1]['sender'] if messages else None
                     
                     if last_sender != 'agent':
                         # Update session status to agent_active
                         manager.update_session_status(target_client_id, "agent_active")
                         
                         # Send system message to customer
                         join_msg = {
                             "sender": "system", 
                             "content": "Agent has joined the chat.",
                             "timestamp": datetime.datetime.now().strftime("%H:%M")
                         }
                         manager.add_message(target_client_id, join_msg)
                         await manager.send_to_client(target_client_id, join_msg)
                         
                         # Broadcast to other agents
                         await manager.broadcast_to_agents({
                             "type": "message",
                             "sender": "system",
                             "content": "Agent has joined the chat.",
                             "clientId": target_client_id,
                             "timestamp": join_msg["timestamp"]
                         })
                         
                         # Update customer app status
                         await manager.send_to_client(target_client_id, {
                             "type": "status_change", 
                             "status": "agent_active"
                         })
                     
                     # Create agent message with timestamp
                     agent_msg = {
                         "sender": "agent", 
                         "content": message_data["content"],
                         "timestamp": datetime.datetime.now().strftime("%H:%M")
                     }
                     manager.add_message(target_client_id, agent_msg)
                     
                     # Send to customer
                     await manager.send_to_client(target_client_id, agent_msg)
                     
                     # Broadcast to other agents
                     await manager.broadcast_to_agents({
                         "type": "message",
                         "sender": "agent",
                         "content": message_data["content"],
                         "clientId": target_client_id,
                         "timestamp": agent_msg["timestamp"]
                     })
                
                elif action_type == "end_session":
                    print(f"Received end_session for {target_client_id}")
                    
                    # Send system message to customer before ending
                    end_msg = {
                        "sender": "system",
                        "content": "Agent has ended the chat. Thank you!",
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    }
                    manager.add_message(target_client_id, end_msg)
                    await manager.send_to_client(target_client_id, end_msg)
                    
                    # End the session
                    manager.end_session(target_client_id)
                    
                    # Notify agents to remove from active list
                    await manager.broadcast_to_agents({
                        "type": "session_ended",
                        "clientId": target_client_id,
                        "reason": "agent_closed"
                    })
        
        elif role == "customer":
            # 1. Determine initial agent (Greeting)
            active_agent_name = manager.active_agent_names.get(client_id, "Greeting Agent")
            selected_agent = greeting_agent # Default
            
            # 2. Initialize Runner for this session
            runner = InMemoryRunner(
                app_name="human_in_the_loop_poc",
                agent=selected_agent
            )
            
            # 3. Create Session
            session = await runner.session_service.create_session(
                app_name="human_in_the_loop_poc",
                user_id=client_id,
                session_id=client_id
            )
            
            # 4. Create LiveRequestQueue
            live_request_queue = LiveRequestQueue()
            
            # 5. Configure Run
            run_config = RunConfig(
                response_modalities=[Modality.TEXT]
            )
            
            # 6. Start Live Streaming
            print(f"Starting run_live for {client_id}")
            live_events = runner.run_live(
                session=session,
                live_request_queue=live_request_queue,
                run_config=run_config
            )
            
            # 7. Start bidirectional tasks
            agent_task = asyncio.create_task(agent_to_client_messaging(websocket, live_events, client_id))
            client_task = asyncio.create_task(client_to_agent_messaging(websocket, live_request_queue, client_id))
            
            # Wait for disconnection
            await asyncio.wait([agent_task, client_task], return_when=asyncio.FIRST_EXCEPTION)
            
            # Cleanup
            live_request_queue.close()

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id, role)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_id, role)

# API Endpoints for History
@app.get("/api/history")
async def get_history():
    return database.get_all_sessions()

@app.get("/api/history/{session_id}")
async def get_session_history(session_id: str):
    session = database.get_session_details(session_id)
    if not session:
        return {"error": "Session not found"}
    return session

# Static Files Mounting
# We need to check if directories exist to avoid errors during initial dev before build
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Mount static files if they exist (will be populated by build script)
if os.path.exists(os.path.join(static_dir, "customer", "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "customer", "assets")), name="customer_assets")

if os.path.exists(os.path.join(static_dir, "customer", "images")):
    app.mount("/images", StaticFiles(directory=os.path.join(static_dir, "customer", "images")), name="customer_images")

if os.path.exists(os.path.join(static_dir, "agent", "assets")):
    app.mount("/agent/assets", StaticFiles(directory=os.path.join(static_dir, "agent", "assets")), name="agent_assets")

# Serve React Apps
@app.get("/agent")
@app.get("/agent/{full_path:path}")
async def serve_agent(full_path: str = ""):
    agent_index = os.path.join(static_dir, "agent", "index.html")
    if os.path.exists(agent_index):
        return FileResponse(agent_index)
    return {"error": "Agent app not built"}

@app.get("/")
@app.get("/{full_path:path}")
async def serve_customer(full_path: str = ""):
    # API routes should be handled above this catch-all
    # If it's a file request that wasn't caught by static mounts (e.g. favicon), try to serve it?
    # For now, just serve index.html for SPA routing
    customer_index = os.path.join(static_dir, "customer", "index.html")
    if os.path.exists(customer_index):
        return FileResponse(customer_index)
    return {"error": "Customer app not built"}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_inactive_sessions())

async def check_inactive_sessions():
    """Background task to archive inactive sessions."""
    while True:
        try:
            await asyncio.sleep(60) # Check every minute
            
            current_time = datetime.datetime.now()
            inactive_threshold = datetime.timedelta(minutes=15)
            
            # Create a list of clients to remove to avoid modifying dict during iteration
            clients_to_archive = []
            
            for client_id, metadata in manager.session_metadata.items():
                # Only archive bot_only sessions automatically
                if metadata.get("status") == "bot_only":
                    last_activity_str = metadata.get("last_activity")
                    if last_activity_str:
                        last_activity = datetime.datetime.fromisoformat(last_activity_str)
                        if current_time - last_activity > inactive_threshold:
                            clients_to_archive.append(client_id)
            
            for client_id in clients_to_archive:
                print(f"Auto-archiving inactive session: {client_id}")
                manager.end_session(client_id)
                # Notify agents
                await manager.broadcast_to_agents({
                    "type": "session_ended",
                    "clientId": client_id,
                    "reason": "inactivity"
                })
                
        except Exception as e:
            print(f"Error in auto-archive task: {e}")
            await asyncio.sleep(60) # Wait before retrying

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
