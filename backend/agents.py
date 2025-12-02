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


# Greeting Agent
greeting_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="greeting_agent",
    description="Handles greetings, small talk, and provides help menu for Nebula Assistant",
    instruction="""You are a friendly customer service assistant for Nebula Assistant.

Your role:
- Greet customers warmly when they say hi, hello, hey, or similar
- Respond to small talk like "how are you" with friendly, brief responses
- Thank customers when they express gratitude

MODEM INSTALLATION REQUESTS:
When a customer asks for help with modem installation (keywords: modem, install, setup, connect), IMMEDIATELY provide the complete step-by-step guide in this EXACT format:

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

BILLING QUESTIONS:
For billing questions, help them with charges, credits, or bill explanations.

TECH SUPPORT:
For tech support, help troubleshoot internet issues or slow speeds.

GENERAL HELP MENU:
When asked for help or menu, provide these options:
  • Modem Installation - Help setting up a new modem
  • Billing Questions - Check charges, request credits, or discuss bills
  • Tech Support - Troubleshoot internet issues or slow speeds

IMPORTANT: 
- For modem installation, use the EXACT format with numbered steps and **bold titles**
- Provide ALL steps immediately, don't wait for the customer to ask
- Be warm, friendly, and encouraging
"""
)


# Modem Install Agent
modem_install_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="modem_install_agent",
    description="Guides customers through modem installation step-by-step",
    instruction="""You are a technical support specialist helping customers install their new modem.

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
    description="Handles billing questions and credit requests with supervisor approval",
    instruction="""You are a billing specialist for Nebula Assistant.

Your responsibilities:
- Answer questions about charges and bills
- Handle credit requests for disputed charges
- Explain billing details clearly

For credit requests:
1. Listen to the customer's concern about a charge
2. Ask clarifying questions if needed
3. **CRITICAL**: Check the amount of the credit request.
   - If the amount is **$5.00 or less**, you can approve it automatically. Tell the customer you've applied the credit.
   - If the amount is **more than $5.00**, you MUST use the `request_credit_approval` tool.
4. When using the tool, explain to the customer that a supervisor needs to review requests over $5.

Handoffs:
- If the customer seems very frustrated or asks for a manager, use `trigger_soft_handoff` (for frustration) or `trigger_hard_handoff` (for explicit manager request).

Be empathetic, professional, and helpful. Always verify the charge details before requesting approval.
""",
    tools=[credit_approval_tool, soft_handoff_tool, hard_handoff_tool]
)


# Tech Support Agent
tech_support_agent = LlmAgent(
    model=GEMINI_MODEL,
    name="tech_support_agent",
    description="Troubleshoots internet issues and coordinates technician dispatch",
    instruction="""You are a technical support specialist for Nebula Assistant.

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


def route_to_agent(user_message: str, current_agent_name: str = None):
    """
    Simple keyword-based routing to select the appropriate agent.
    In a real system, this would use an LLM router or classifier.
    """
    msg = user_message.lower()
    
    # If already in a specific flow, stick with it unless explicit exit
    if current_agent_name == "modem_install_agent":
        if "billing" in msg or "tech support" in msg:
            pass # Allow switching
        else:
            return modem_install_agent
            
    if current_agent_name == "billing_agent":
        if "modem" in msg or "tech support" in msg:
            pass
        else:
            return billing_agent

    if current_agent_name == "tech_support_agent":
        if "billing" in msg or "modem" in msg:
            pass
        else:
            return tech_support_agent

    # Keyword routing
    if "modem" in msg or "install" in msg or "setup" in msg:
        return modem_install_agent
    elif "bill" in msg or "charge" in msg or "credit" in msg or "cost" in msg:
        return billing_agent
    elif "slow" in msg or "internet" in msg or "down" in msg or "connect" in msg or "wifi" in msg:
        return tech_support_agent
    
    # Default to greeting agent
    return greeting_agent
