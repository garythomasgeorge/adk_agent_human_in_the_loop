# Nebula AI - Human-in-the-Loop Customer Service PoC

A proof-of-concept application demonstrating human-in-the-loop AI customer service using the Google ADK (Agent Development Kit) framework. This system showcases intelligent agent routing, soft/hard handoffs, and supervisor approval workflows.

## Features

- **🤖 ADK Framework Integration**: Built on Google's Agent Development Kit with specialized agents for different domains
- **🔄 Intelligent Routing**: Automatic routing to appropriate agents based on customer intent
- **👥 Human-in-the-Loop**: Seamless handoffs between AI and human agents
- **✅ Approval Workflows**: Supervisor approval for high-value actions (credits, tech dispatch)
- **💬 Real-time Communication**: WebSocket-based bidirectional messaging
- **✨ Rich Chat UI**: Interactive step-by-step cards with progressive reveal and markdown support
- **📊 Chat History**: SQLite-based persistence with session management
- **🎨 Modern UI**: React-based customer and agent interfaces with Tailwind CSS

## Architecture

### ADK Framework

The application uses a modular agent architecture:

```
┌─────────────────┐
│  RouterAgent    │  ← Routes messages to appropriate agent
└────────┬────────┘
         │
    ┌────┴────┬────────────┬─────────────┐
    │         │            │             │
┌───▼────┐ ┌─▼──────┐ ┌──▼────────┐   │
│ Modem  │ │Billing │ │   Tech    │   │
│Install │ │Dispute │ │  Support  │   │
└────────┘ └────────┘ └───────────┘   │
                                       │
                              ┌────────▼────────┐
                              │ Default Handler │
                              └─────────────────┘
```

### Components

#### Backend (`/backend`)
- **`adk.py`**: ADK framework base classes (Agent, RouterAgent, AgentState)
- **`agents.py`**: Specialized agents (ModemInstallAgent, BillingDisputeAgent, TechSupportAgent)
- **`main.py`**: FastAPI server with WebSocket endpoints
- **`database.py`**: SQLite chat history persistence

#### Frontend Customer (`/frontend-customer`)
- React + Vite + Tailwind CSS
- Real-time chat interface
- **`StepCard.jsx`**: Interactive component for step-by-step guides
- Visual differentiation for bot/agent/system messages
- "End Chat" functionality

#### Frontend Agent (`/frontend-agent`)
- React + Vite + Tailwind CSS (dark mode)
- Live chat monitoring with alerts
- Approval modal for supervisor requests
- Chat history viewer
- Take-over functionality

## Mock Scenarios

### 1. Modem Installation (Visual Guide)
**Trigger**: "install modem"
**Flow**: Interactive step-by-step cards with images and progressive reveal
**Type**: Automated guidance with visual aids

### 2. Movie Rental Dispute (Hard Handoff)
**Trigger**: "bill movie" → "not me"
**Flow**: Credit request requiring supervisor approval
**Type**: Hard handoff - requires explicit approval

### 3. Internet Troubleshooting (Hard Handoff)
**Trigger**: "internet slow" → "next"
**Flow**: System check → Random success/failure → Tech dispatch approval
**Type**: Hard handoff - requires approval for technician dispatch

## Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/garythomasgeorge/adk_agent_human_in_the_loop.git
   cd adk_agent_human_in_the_loop
   ```

2. **Run the application**
   ```bash
   ./scripts/local_run.sh
   ```

   This script will:
   - Install Python dependencies
   - Build both frontend applications
   - Start the FastAPI server on `http://localhost:8080`

3. **Access the applications**
   - Customer App: `http://localhost:8080`
   - Agent Dashboard: `http://localhost:8080/agent`

### Manual Setup

If you prefer to run components separately:

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

# Frontend - Customer (separate terminal)
cd frontend-customer
npm install
npm run build

# Frontend - Agent (separate terminal)
cd frontend-agent
npm install
npm run build
```

## Deployment

### Google Cloud Run

```bash
./scripts/deploy.sh
```

This will:
- Build a multi-stage Docker image
- Deploy to Google Cloud Run
- Configure for public access on port 8080

## API Reference

### WebSocket Endpoints

#### Customer Connection
```
ws://localhost:8080/ws/{client_id}/customer
```

**Message Format (Customer → Server)**:
```json
{
  "content": "user message text",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Message Format (Server → Customer)**:
```json
{
  "sender": "bot|agent|system",
  "content": "response text",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Agent Connection
```
ws://localhost:8080/ws/{agent_id}/agent
```

**Sync State (Server → Agent on connect)**:
```json
{
  "type": "sync_state",
  "active_chats": ["client_id_1", "client_id_2"],
  "messages": {
    "client_id_1": [...]
  },
  "approvals": {
    "client_id_1": {
      "amount": 14.99,
      "reason": "Movie Rental Dispute"
    }
  }
}
```

**Approval Request (Server → Agent)**:
```json
{
  "type": "approval_request",
  "clientId": "client_id",
  "amount": 14.99,
  "reason": "Credit request reason"
}
```

**Approval Response (Agent → Server)**:
```json
{
  "type": "approval_response",
  "targetClientId": "client_id",
  "approved": true
}
```

**Take Over (Agent → Server)**:
```json
{
  "type": "takeover_message",
  "targetClientId": "client_id",
  "content": "agent message"
}
```

**End Session (Customer/Agent → Server)**:
```json
{
  "type": "end_session",
  "clientId": "client_id"  // only for agent
}
```

### REST Endpoints

#### Get Chat History
```
GET /api/history
```

Returns all completed chat sessions.

#### Get Session Details
```
GET /api/history/{session_id}
```

Returns messages for a specific session.

## Project Structure

```
.
├── backend/
│   ├── adk.py              # ADK framework base classes
│   ├── agents.py           # Specialized agents
│   ├── main.py             # FastAPI server
│   ├── database.py         # SQLite persistence
│   ├── requirements.txt    # Python dependencies
│   └── static/             # Built frontend assets
├── frontend-customer/
│   ├── public/
│   │   └── images/         # Static images (modem steps)
│   ├── src/
│   │   ├── App.jsx         # Customer chat UI
│   │   ├── StepCard.jsx    # Step-by-step card component
│   │   ├── StepCard.css    # Card styling
│   │   └── index.css       # Tailwind styles
│   ├── package.json
│   └── vite.config.js
├── frontend-agent/
│   ├── src/
│   │   ├── App.jsx         # Agent dashboard UI
│   │   └── index.css       # Tailwind styles (dark)
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── local_run.sh        # Local development script
│   └── deploy.sh           # Cloud Run deployment
├── Dockerfile              # Multi-stage build
└── README.md
```

## Technologies

- **Backend**: Python, FastAPI, WebSockets, SQLite
- **Frontend**: React, Vite, Tailwind CSS
- **Icons**: Lucide React
- **Deployment**: Docker, Google Cloud Run

## License

MIT

## Contributing

This is a proof-of-concept project. For production use, consider:
- Authentication and authorization
- Rate limiting
- Persistent message queue (e.g., Redis)
- Production-grade database (PostgreSQL)
- Monitoring and logging
- Error handling and retry logic
- Load balancing for multiple agents
