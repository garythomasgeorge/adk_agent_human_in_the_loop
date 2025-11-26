"""
ADK-based specialized agents for the Human-in-the-Loop PoC.
Each agent handles a specific domain (modem installation, billing, tech support).
"""

import asyncio
import random
from typing import Dict, Any
from adk import Agent, AgentState


class GreetingAgent(Agent):
    """Handles greetings, small talk, and provides general help menu."""
    
    def __init__(self):
        super().__init__("Greeting")
    
    def process(self, message: str, context: list) -> dict:
        """Process greetings and small talk."""
        msg_lower = message.lower()
        
        # Greetings
        if any(greeting in msg_lower for greeting in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
            return {
                "response": "Hello! 👋 Welcome to Nebula Assistant. I'm here to help you with:\n\n• **Modem Installation** - Get your new modem set up\n• **Billing Questions** - Check charges or request credits\n• **Tech Support** - Troubleshoot internet issues\n\nWhat can I help you with today?"
            }
        
        # How are you / small talk
        if any(phrase in msg_lower for phrase in ["how are you", "how's it going", "what's up", "how do you do"]):
            return {
                "response": "I'm doing great, thank you for asking! 😊 I'm here and ready to help you with any questions about your service. What can I assist you with?"
            }
        
        # Thanks / gratitude
        if any(phrase in msg_lower for phrase in ["thank", "thanks", "appreciate"]):
            return {
                "response": "You're very welcome! Is there anything else I can help you with today?"
            }
        
        # Help / menu
        if "help" in msg_lower or "menu" in msg_lower or "options" in msg_lower:
            return {
                "response": "I can assist you with:\n\n• **Modem Installation** - Say 'install modem' for step-by-step setup\n• **Billing Questions** - Ask about charges, credits, or your bill\n• **Tech Support** - Report internet issues or slow speeds\n\nJust let me know what you need!"
            }
        
        # Goodbye
        if any(phrase in msg_lower for phrase in ["bye", "goodbye", "see you", "later"]):
            return {
                "response": "Goodbye! Have a great day! Feel free to come back anytime you need assistance. 👋"
            }
        
        # Default - offer help
        self.state = AgentState.IDLE
        return {
            "response": "I'm here to help! You can ask me about:\n\n• Modem installation\n• Billing questions\n• Internet troubleshooting\n\nWhat would you like help with?"
        }


class ModemInstallAgent(Agent):
    """Handles modem installation guided setup (soft handoff scenario)."""
    
    def __init__(self):
        super().__init__("ModemInstall")
        self.modem_steps = [
            "Great! Let's get your new modem set up. \n\n**Step 1:** Open the box and take out the modem and the power cord.",
            "**Step 2:** Connect the coax cable from the wall to the back of the modem. Make sure it's finger-tight.",
            "**Step 3:** Plug the power cord into the modem and then into an electrical outlet.",
            "**Step 4:** Wait for the 'Online' light to turn solid white. This might take up to 10 minutes.",
            "**Step 5:** Connect your devices to the WiFi using the Network Name (SSID) and Password printed on the bottom of the modem."
        ]
        self.current_step = -1
        self.in_flow = False
    
    def process(self, message: str, context: list) -> dict:
        """Process modem installation requests."""
        msg_lower = message.lower()
        
        # Start flow
        if "modem" in msg_lower and ("install" in msg_lower or "setup" in msg_lower or "set up" in msg_lower):
            self.in_flow = True
            self.current_step = 0
            self.state = AgentState.IDLE
            return {"response": self.modem_steps[0]}
        
        # In flow
        if self.in_flow:
            if "quit" in msg_lower or "stop" in msg_lower:
                self.in_flow = False
                self.current_step = -1
                self.state = AgentState.IDLE
                return {"response": "Modem setup cancelled. How else can I help?"}
            
            self.current_step += 1
            if self.current_step < len(self.modem_steps):
                self.state = AgentState.IDLE
                return {"response": self.modem_steps[self.current_step]}
            else:
                self.in_flow = False
                self.current_step = -1
                self.state = AgentState.IDLE
                return {"response": "Congratulations! Your modem should be all set up. Is there anything else?"}
        
        # Default
        self.state = AgentState.IDLE
        return {"response": "I can help you install a new modem. Just say 'install modem' to get started."}


class BillingDisputeAgent(Agent):
    """Handles billing disputes and credit requests (hard handoff scenario)."""
    
    def __init__(self):
        super().__init__("Billing")
        self.credit_threshold = 10.0
    
    def process(self, message: str, context: list) -> dict:
        """Process billing and credit requests."""
        msg_lower = message.lower()
        
        # Check for billing keywords
        if "bill" in msg_lower or "charge" in msg_lower or "credit" in msg_lower:
            # Check for movie rental dispute
            if "movie" in msg_lower or "rental" in msg_lower:
                # Check if user is disputing
                if "not" in msg_lower or "didn't" in msg_lower or "never" in msg_lower:
                    # Request credit (requires approval)
                    self.state = AgentState.WAITING_FOR_APPROVAL
                    return {
                        "response": "I understand you're disputing a movie rental charge. Let me request a credit for you.",
                        "action_required": True,
                        "amount": 14.99,
                        "reason": "Movie Rental Dispute - Customer claims unauthorized charge"
                    }
                else:
                    return {"response": "I see a movie rental charge of $14.99 on your account. Is this charge correct?"}
            
            # General billing inquiry
            return {"response": "I can help with billing questions. What would you like to know about your bill?"}
        
        # Default
        self.state = AgentState.IDLE
        return {"response": "I can help with billing and credit requests. What do you need assistance with?"}


class TechSupportAgent(Agent):
    """Handles internet troubleshooting and tech dispatch (hard handoff scenario)."""
    
    def __init__(self):
        super().__init__("TechSupport")
        self.current_step = 0
    
    async def process_async(self, message: str, context: list) -> dict:
        """Async version of process for system check simulation."""
        msg_lower = message.lower()
        
        # Check for internet issues
        if "internet" in msg_lower or "slow" in msg_lower or "down" in msg_lower or "connection" in msg_lower:
            # Reset flow
            if "reset" in msg_lower:
                self.current_step = 0
            
            if self.current_step == 0:
                self.current_step += 1
                self.state = AgentState.PROCESSING
                return {"response": "I'm sorry to hear about your internet issues. Let me run a remote system health check. This will take a few seconds..."}
            
            elif self.current_step == 1:
                # Simulate system check
                await asyncio.sleep(2)
                success = random.choice([True, False])
                
                if success:
                    self.current_step = 0
                    self.state = AgentState.IDLE
                    return {"response": "Good news! The system check cleared some temporary cache errors on your line. Your internet should be back to normal speed now. Please check it."}
                else:
                    self.current_step += 1
                    self.state = AgentState.WAITING_FOR_APPROVAL
                    return {
                        "response": "The system check detected a signal degradation that I can't fix remotely. We need to send a technician to your home.",
                        "action_required": True,
                        "amount": 0,
                        "reason": "Technician Dispatch Required (Signal Degradation)"
                    }
        
        # Default
        self.state = AgentState.IDLE
        return {"response": "I can help troubleshoot internet connection issues. Are you experiencing problems with your internet?"}
    
    def process(self, message: str, context: list) -> dict:
        """Synchronous wrapper for process_async."""
        # This will be called from sync context, so we need to handle it
        # For now, return a simple response and let the async version be called separately
        return asyncio.run(self.process_async(message, context))
