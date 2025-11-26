from abc import ABC, abstractmethod
from enum import Enum

class AgentState(Enum):
    IDLE = "idle"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    PROCESSING = "processing"

class Agent(ABC):
    """Abstract base class for all agents in the ADK framework."""
    
    def __init__(self, name: str):
        self.name = name
        self.state = AgentState.IDLE
    
    @abstractmethod
    def process(self, message: str, context: list) -> dict:
        """
        Process a message and return a response.
        
        Args:
            message: The user's message
            context: List of previous messages in the conversation
            
        Returns:
            dict with keys:
                - response: str - The agent's response
                - action_required: bool - Whether supervisor approval is needed
                - amount: float (optional) - Amount for approval
                - reason: str (optional) - Reason for approval request
        """
        pass

class RouterAgent:
    """Routes messages to the appropriate specialized agent based on keywords."""
    
    def __init__(self, agents: dict):
        """
        Initialize the router with a dictionary of agents.
        
        Args:
            agents: dict mapping agent names to Agent instances
        """
        self.agents = agents
        self.current_agent = None
    
    def route(self, message: str, active_agent_name: str = None) -> Agent:
        """
        Route a message to the appropriate agent.
        
        Args:
            message: The user's message
            active_agent_name: Name of currently active agent (if any)
            
        Returns:
            The Agent instance that should handle this message
        """
        message_lower = message.lower()
        
        # Check for strong topic switches
        if any(keyword in message_lower for keyword in ["install", "modem", "setup", "new modem"]):
            return self.agents.get("modem_install", self.agents.get("default"))
        
        if any(keyword in message_lower for keyword in ["bill", "charge", "credit", "refund", "movie", "rental"]):
            return self.agents.get("billing", self.agents.get("default"))
        
        if any(keyword in message_lower for keyword in ["internet", "slow", "connection", "wifi", "speed"]):
            return self.agents.get("tech_support", self.agents.get("default"))
        
        # If no strong topic switch, stick to current agent if it exists
        if active_agent_name and active_agent_name in self.agents:
            return self.agents[active_agent_name]
        
        # Default to first available agent or None
        return self.agents.get("default") or next(iter(self.agents.values()))
