import os
import json
import asyncio
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from adk import RouterAgent, AgentState
from agents import ModemInstallAgent, BillingDisputeAgent, TechSupportAgent

import database

app = FastAPI()

# Initialize Database
database.init_db()

# Store active connections and chat history in memory for active sessions
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_connections: List[WebSocket] = []
        self.session_messages: Dict[str, List[Dict]] = {} # Store messages for active sessions
        self.active_approvals: Dict[str, Dict] = {} # Store active approval requests
        self.active_agent_names: Dict[str, str] = {} # Track active agent per client

    async def connect(self, websocket: WebSocket, client_id: str, role: str):
        await websocket.accept()
        if role == "agent":
            self.agent_connections.append(websocket)
            # Sync state to new agent
            await websocket.send_json({
                "type": "sync_state",
                "active_chats": list(self.session_messages.keys()),
                "messages": self.session_messages,
                "approvals": self.active_approvals
            })
        else:
            self.active_connections[client_id] = websocket
            if client_id not in self.session_messages:
                self.session_messages[client_id] = []

    def disconnect(self, websocket: WebSocket, client_id: str, role: str):
        if role == "agent":
            if websocket in self.agent_connections:
                self.agent_connections.remove(websocket)
        else:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                # Auto-save on disconnect? Or wait for explicit end?
                # For now, let's keep it in memory until explicit end or maybe save on disconnect as "interrupted"
                # But user asked for "End Session" button to trigger save.
                # We will implement a specific "end_session" event.

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
        if 'timestamp' not in message or message['timestamp'] is None:
            import datetime
            message['timestamp'] = datetime.datetime.now().isoformat()
        self.session_messages[client_id].append(message)
        
    def add_approval(self, client_id: str, approval_data: dict):
        self.active_approvals[client_id] = approval_data
        
    def remove_approval(self, client_id: str):
        if client_id in self.active_approvals:
            del self.active_approvals[client_id]

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
            if client_id in self.active_connections:
                 # Optionally close connection or notify client
                 pass
        else:
            print(f"Session {client_id} not found in memory")

manager = ConnectionManager()

# Initialize ADK Agents
modem_agent = ModemInstallAgent()
billing_agent = BillingDisputeAgent()
tech_agent = TechSupportAgent()

# Initialize Router
router = RouterAgent({
    "modem_install": modem_agent,
    "billing": billing_agent,
    "tech_support": tech_agent,
    "default": tech_agent  # Default to tech support
})

@app.websocket("/ws/{client_id}/{role}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, role: str):
    await manager.connect(websocket, client_id, role)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if role == "customer":
                # 1. Store message
                msg_obj = {
                    "sender": "customer",
                    "content": message_data["content"],
                    "timestamp": message_data.get("timestamp")
                }
                manager.add_message(client_id, msg_obj)

                # 2. Broadcast customer message to agents
                await manager.broadcast_to_agents({
                    "type": "message",
                    "sender": "customer",
                    "content": message_data["content"],
                    "clientId": client_id,
                    "timestamp": msg_obj["timestamp"]
                })
                
                # 3. Route to appropriate agent
                active_agent_name = manager.active_agent_names.get(client_id)
                selected_agent = router.route(message_data["content"], active_agent_name)
                manager.active_agent_names[client_id] = selected_agent.name
                
                # 4. Process with selected agent
                # Check if agent is paused (waiting for approval)
                if selected_agent.state == AgentState.WAITING_FOR_APPROVAL:
                     response_content = "Waiting for supervisor approval..."
                     bot_msg = {"sender": "system", "content": response_content}
                     manager.add_message(client_id, bot_msg)
                     await manager.send_to_client(client_id, bot_msg)
                else:
                    # Get conversation context
                    context = manager.get_messages(client_id)
                    
                    # Process message with selected agent
                    if isinstance(selected_agent, TechSupportAgent):
                        # TechSupportAgent needs async processing
                        result = await selected_agent.process_async(message_data["content"], context)
                    else:
                        result = selected_agent.process(message_data["content"], context)
                    
                    if result.get("action_required"):
                        # Notify Agents of Approval Request
                        approval_data = {
                            "type": "approval_request",
                            "clientId": client_id,
                            "amount": result.get("amount"),
                            "reason": result.get("reason")
                        }
                        manager.add_approval(client_id, approval_data)
                        await manager.broadcast_to_agents(approval_data)
                        
                        response_content = result["response"]
                        bot_msg = {"sender": "bot", "content": response_content}
                        manager.add_message(client_id, bot_msg)
                        await manager.send_to_client(client_id, bot_msg)
                    else:
                        # Normal response
                        response_text = result["response"]
                        bot_msg = {"sender": "bot", "content": response_text}
                        manager.add_message(client_id, bot_msg)
                        
                        await manager.send_to_client(client_id, bot_msg)
                        await manager.broadcast_to_agents({
                            "type": "message",
                            "sender": "bot",
                            "content": response_text,
                            "clientId": client_id
                        })

            elif role == "agent":
                # Handle Agent Actions
                action_type = message_data.get("type")
                target_client_id = message_data.get("targetClientId")
                
                if action_type == "approval_response":
                    approved = message_data.get("approved")
                    manager.remove_approval(target_client_id) # Remove from active approvals
                    
                    # Reset the agent state for this client
                    active_agent_name = manager.active_agent_names.get(target_client_id)
                    if active_agent_name:
                        selected_agent = router.agents.get(active_agent_name)
                        if selected_agent:
                            selected_agent.state = AgentState.IDLE
                    
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
                     # For simplicity, we'll just send it if the previous message wasn't from an agent, 
                     # or we can rely on the frontend to show it once. 
                     # Better: Send a specific system message.
                     
                     # Let's just send the message. The user asked for "Agent Name has joined".
                     # We'll send a system message first.
                     # In a real app, we'd track if we already sent this.
                     # For this PoC, we'll send it if the last message wasn't from 'agent'.
                     messages = manager.get_messages(target_client_id)
                     last_sender = messages[-1]['sender'] if messages else None
                     
                     if last_sender != 'agent':
                         join_msg = {"sender": "system", "content": "Agent has joined the chat."}
                         manager.add_message(target_client_id, join_msg)
                         await manager.send_to_client(target_client_id, join_msg)
                     
                     agent_msg = {"sender": "agent", "content": message_data["content"]}
                     manager.add_message(target_client_id, agent_msg)
                     
                     await manager.send_to_client(target_client_id, agent_msg)
                
                elif action_type == "end_session":
                    print(f"Received end_session for {target_client_id}")
                    manager.end_session(target_client_id)
                    # Notify agents to remove from active list
                    await manager.broadcast_to_agents({
                        "type": "session_ended",
                        "clientId": target_client_id
                    })

    except WebSocketDisconnect:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
