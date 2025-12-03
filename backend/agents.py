"""
Google ADK-based agents for the Human-in-the-Loop PoC.
Uses LlmAgent with Gemini for natural language understanding.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Load environment variables
load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")


# Define tools for approval workflows
def request_credit_approval(amount: float, reason: str) -> dict:
    """
    Request supervisor approval for a credit.
    
    Args:
        amount: The credit amount in dollars
        reason: The reason for the credit request
        
    Returns:
        dict with action_required flag and approval details
    """
    return {
        "action_required": True,
        "amount": amount,
        "reason": reason,
        "response": f"I've submitted a request for a ${amount:.2f} credit. A supervisor will review this shortly."
    }


def request_tech_dispatch(reason: str) -> dict:
    """
    Request supervisor approval for technician dispatch.
    
    Args:
        reason: The reason for technician dispatch
        
    Returns:
        dict with action_required flag and approval details
    """
    return {
        "action_required": True,
        "amount": 0,
        "reason": reason,
        "response": f"I need to send a technician to your location. Let me get supervisor approval for the dispatch."
    }

def trigger_soft_handoff(reason: str, sentiment_score: float) -> dict:
    """
    Signal that a human agent should monitor this conversation.
    
    Args:
        reason: Why monitoring is needed (e.g. "customer frustration", "complex issue")
        sentiment_score: Estimated sentiment (0.0-1.0, where 0 is negative)
        
    Returns:
        dict with handoff details
    """
    return {
        "handoff_type": "soft",
        "reason": reason,
        "sentiment_score": sentiment_score,
        "response": "I understand this is frustrating. Let me see what I can do to help."
    }

def trigger_hard_handoff(reason: str) -> dict:
    """
    Request immediate human agent takeover.
    
    Args:
        reason: Why takeover is needed (e.g. "customer requested manager", "escalation")
        
    Returns:
        dict with handoff details
    """
    return {
        "handoff_type": "hard",
        "reason": reason,
        "response": "I'm going to connect you with a human agent who can better assist you. Please hold on a moment."
    }


# Create ADK Tools
credit_approval_tool = FunctionTool(
    func=request_credit_approval
)

tech_dispatch_tool = FunctionTool(
    func=request_tech_dispatch
)

soft_handoff_tool = FunctionTool(
    func=trigger_soft_handoff
)

hard_handoff_tool = FunctionTool(
    func=trigger_hard_handoff
)


# Greeting Agent (Simple - no billing logic)
greeting_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="greeting_agent",
    description="Handles greetings, small talk, and general help. Use when customer says hello, thanks, or asks for help menu.",
    instruction="""You are a friendly greeter for Nebula Assistant.

Your role:
- Greet customers warmly when they say hi, hello, hey, or similar
- Respond to small talk like "how are you" with friendly, brief responses  
- Thank customers when they express gratitude
- Provide help menu when asked

HUMAN AGENT REQUESTS:
If the customer explicitly asks to speak with a human agent, supervisor, manager, or real person, you MUST:
1. Use the `trigger_hard_handoff` tool immediately
2. Tell them: "I'm connecting you with a human agent right now. They'll be with you shortly."

FRUSTRATION DETECTION:
If the customer expresses frustration, anger, or dissatisfaction, you should:
1. Use the `trigger_soft_handoff` tool with reason="Customer expressing frustration" and sentiment_score=0.3
2. Acknowledge their frustration: "I understand you're frustrated. Let me make sure you get the help you need."

GENERAL HELP MENU:
When asked for help or menu, provide these options:
  • Modem Installation - Help setting up a new modem
  • Billing Questions - Check charges, request credits, or discuss bills
  • Tech Support - Troubleshoot internet issues or slow speeds

Be warm, friendly, and encouraging!
""",
    tools=[soft_handoff_tool, hard_handoff_tool]
)


# Modem Install Agent
modem_install_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="modem_install_agent",
    description="Guides customers through modem installation and setup. Use for modem, installation, setup, or connection questions.",
    instruction="""You are a technical support specialist helping customers install their new modem.

DO NOT GREET THE CUSTOMER. Assume they have already been greeted.
IMMEDIATELY address their modem installation request.

When a customer asks for help with modem installation, IMMEDIATELY provide the complete step-by-step guide in this EXACT format:

Alright, here are the detailed steps for installing your modem:

1. **Unpack Your Modem**: Remove the modem, power adapter, and any cables from the box.
2. **Connect the Cable**:
   - Find the coaxial cable (the one with a screw-on connector).
   - Connect one end to the cable wall outlet.
   - Connect the other end to the modem's "Cable" or "RF In" port.
   - Make sure the connection is finger-tight.
3. **Plug in the Power**:
   - Plug the power adapter into the modem.
   - Plug the other end into a power outlet.
   - The modem will power on automatically.
4. **Wait for the Modem to Initialize**:
   - Wait a few minutes for the modem to power on and connect to the network.
   - Check the modem's lights. Usually, a "Cable," "Online," or "Internet" light will turn solid when the modem is connected.
5. **Connect to Your Computer or Router**:
   - Use an Ethernet cable to connect the modem to your computer or router.
   - Plug one end into the modem's Ethernet port.
   - Plug the other end into your computer's Ethernet port or your router's "Internet" or "WAN" port.
6. **Activate Your Modem (if required)**:
   - Open a web browser on your computer.
   - You may be automatically redirected to your ISP's activation page. If not, go to your ISP's website and look for a "Activate Modem" or "Self-Installation" link.
   - Follow the on-screen instructions to activate your modem. You'll likely need your account number and the modem's serial number.
7. **Test Your Internet Connection**:
   - After activation, try browsing the web to make sure your internet connection is working.

Let me know if you get stuck at any point!

IMPORTANT: 
- Use this EXACT format with numbered steps and **bold titles**
- Provide ALL steps immediately, don't wait for the customer to ask
- After providing the steps, ask if they need help with any specific step
- Be encouraging and supportive throughout
"""
)


# Billing Agent
billing_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="billing_agent",
    description="Handles billing questions, charges, credits, and payment disputes. Use for any money or bill-related issues.",
    instruction="""You are a billing specialist.

CRITICAL INSTRUCTION:
When a customer requests a credit > $5.00, you MUST execute the request_credit_approval function.
This is NOT a simulation. You have access to this function and you MUST call it.

Process:
1. Customer says: "I want a $15 credit"
2. You identify: amount = 15, which is > 5
3. You EXECUTE: request_credit_approval(amount=15.0, reason="Customer request")
4. The function returns a response
5. You relay that response to the customer

DO NOT:
- Say "I've submitted" without calling the function
- Pretend to call the function
- Explain why you can't call it
- Ask for permission to call it

JUST CALL THE FUNCTION when amount > $5.

For credits <= $5:
- Approve directly
- Say: "I've applied a $[amount] credit to your account."

For frustrated customers:
- Call trigger_soft_handoff

For customers requesting human:
- Call trigger_hard_handoff
""",
    tools=[credit_approval_tool, soft_handoff_tool, hard_handoff_tool]
)


# Tech Support Agent
tech_support_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="tech_support_agent",
    description="Handles internet connectivity issues, slow speeds, WiFi problems, and technical troubleshooting. Use for internet or connectivity problems, and coordinates technician dispatch",
    instruction="""You are a technical support specialist for Nebula Assistant.

DO NOT GREET THE CUSTOMER. Assume they have already been greeted.
IMMEDIATELY address their technical issue.

Your responsibilities:
- Troubleshoot internet connectivity issues
- Diagnose slow speeds or connection problems
- Coordinate technician dispatch when needed

Troubleshooting process:
1. Ask about the specific issue (slow speeds, no connection, intermittent)
2. Suggest basic troubleshooting:
   - Check if modem lights are solid or blinking
   - Try restarting the modem (unplug for 10 seconds)
   - Check cable connections

3. If basic troubleshooting doesn't work:
   - Mention you'll run a remote system check
   - Simulate checking the line (take a moment)
   - If there's a signal issue you can't fix remotely, use `request_tech_dispatch` tool

4. The tech dispatch tool will request supervisor approval
5. Let the customer know a supervisor is reviewing the dispatch request

Handoffs:
- If the customer is frustrated or the issue is complex, use `trigger_soft_handoff`.
- If they demand a supervisor, use `trigger_hard_handoff`.

Be patient, technical but not overly complex, and reassuring. Guide them through each step clearly.
""",
    tools=[tech_dispatch_tool, soft_handoff_tool, hard_handoff_tool]
)


# Coordinator Agent (Parent with ADK routing)
# Use gemini-2.5-flash as requested
coordinator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="coordinator_agent",
    description="Main coordinator that routes customer requests to specialized agents",
    instruction="""You are a silent router for Nebula Assistant.

Your ONLY job is to analyze the customer's request and route them to the appropriate agent.

DO NOT respond to the customer. DO NOT greet them. DO NOT say anything.
The specialized agent will handle all communication.

Available agents:
- **billing_agent**: Billing questions, charges, credits, payment disputes
- **tech_support_agent**: Internet issues, slow speeds, WiFi problems, connectivity
- **modem_install_agent**: Modem installation, setup, connection help
- **greeting_agent**: Greetings, small talk, thank yous, general help

Just route. Say nothing.
""",
    sub_agents=[billing_agent, tech_support_agent, modem_install_agent, greeting_agent]
)


def route_to_agent(user_message: str, current_agent_name: str = None):
    """
    DEPRECATED: This function is no longer used.
    Routing is now handled by coordinator_agent using ADK's transfer_to_agent mechanism.
    Kept for backwards compatibility only.
    """
    msg = user_message.lower()
    
    # Keyword routing (fallback)
    if "modem" in msg or "install" in msg or "setup" in msg:
        return modem_install_agent
    elif "bill" in msg or "charge" in msg or "credit" in msg or "cost" in msg:
        return billing_agent
    elif "slow" in msg or "internet" in msg or "down" in msg or "connect" in msg or "wifi" in msg:
        return tech_support_agent
    
    # Default to coordinator
    return coordinator_agent
