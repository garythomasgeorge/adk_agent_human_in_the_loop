import asyncio
import random
from enum import Enum
from typing import Dict, Any, Optional

class AgentState(Enum):
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.state = AgentState.IDLE

    async def process(self, message: str) -> Dict[str, Any]:
        raise NotImplementedError

class TechSubAgent(BaseAgent):
    def __init__(self):
        super().__init__("TechSubAgent")
        # Existing troubleshooting steps
        self.troubleshoot_steps = ["Restart Modem", "Check Coax", "Schedule Tech"]
        self.current_troubleshoot_idx = 0
        
        # Modem Installation Steps
        self.modem_steps = [
            "Great! Let's get your new modem set up. \n\n**Step 1:** Open the box and take out the modem and the power cord.",
            "**Step 2:** Connect the coax cable from the wall to the back of the modem. Make sure it's finger-tight.",
            "**Step 3:** Plug the power cord into the modem and then into an electrical outlet.",
            "**Step 4:** Wait for the 'Online' light to turn solid white. This might take up to 10 minutes.",
            "**Step 5:** Connect your devices to the WiFi using the Network Name (SSID) and Password printed on the bottom of the modem."
        ]
        self.current_modem_idx = -1 # -1 means not in modem flow
        self.in_modem_flow = False

    async def process(self, message: str) -> Dict[str, Any]:
        self.state = AgentState.PROCESSING
        msg_lower = message.lower()
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        # --- Modem Installation Flow ---
        if "modem" in msg_lower and ("install" in msg_lower or "setup" in msg_lower or "set up" in msg_lower):
            self.in_modem_flow = True
            self.current_modem_idx = 0
            self.state = AgentState.IDLE
            return {"response": self.modem_steps[0]}
            
        if self.in_modem_flow:
            if "quit" in msg_lower or "stop" in msg_lower:
                self.in_modem_flow = False
                self.current_modem_idx = -1
                self.state = AgentState.IDLE
                return {"response": "Modem setup cancelled. How else can I help?"}
                
            self.current_modem_idx += 1
            if self.current_modem_idx < len(self.modem_steps):
                self.state = AgentState.IDLE
                return {"response": self.modem_steps[self.current_modem_idx]}
            else:
                self.in_modem_flow = False
                self.current_modem_idx = -1
                self.state = AgentState.COMPLETED
                return {"response": "Congratulations! Your modem should be all set up. Is there anything else?"}

        # --- System Check / Tech Dispatch Flow ---
        if "internet" in msg_lower or "slow" in msg_lower or "down" in msg_lower:
             # If we are just starting or restarting
             if "reset" in msg_lower:
                 self.current_troubleshoot_idx = 0
                 
             if self.current_troubleshoot_idx == 0:
                 self.current_troubleshoot_idx += 1
                 self.state = AgentState.IDLE
                 return {"response": "I'm sorry to hear about your internet issues. Let's try to fix it. First, I'm going to run a remote system health check. This will take a few seconds..."}
             
             elif self.current_troubleshoot_idx == 1:
                 # Simulate system check
                 await asyncio.sleep(2) # Extra wait for "system check"
                 success = random.choice([True, False])
                 
                 if success:
                     self.current_troubleshoot_idx = 0 # Reset
                     self.state = AgentState.IDLE
                     return {"response": "Good news! The system check cleared some temporary cache errors on your line. Your internet should be back to normal speed now. Please check it."}
                 else:
                     self.current_troubleshoot_idx += 1
                     self.state = AgentState.WAITING_FOR_APPROVAL
                     return {
                         "response": "The system check detected a signal degradation that I can't fix remotely. We need to send a technician to your home.",
                         "action_required": True,
                         "amount": 0, # No cost, but needs approval/scheduling
                         "reason": "Technician Dispatch Required (Signal Degradation)"
                     }
        
        # Default / Fallback
        self.state = AgentState.IDLE
        return {"response": "I can help with Internet troubleshooting or Modem installation. Just let me know what you need."}

class BillingSubAgent(BaseAgent):
    def __init__(self):
        super().__init__("BillingSubAgent")
        self.approval_threshold = 5.0
        self.dispute_stage = 0 # 0: Idle, 1: Identified Charge, 2: Customer Denied

    async def process(self, message: str) -> Dict[str, Any]:
        self.state = AgentState.PROCESSING
        msg_lower = message.lower()
        
        # --- Movie Rental Dispute Flow ---
        if "bill" in msg_lower or "movie" in msg_lower or "rental" in msg_lower or "charge" in msg_lower:
            if self.dispute_stage == 0:
                self.dispute_stage = 1
                await asyncio.sleep(1)
                self.state = AgentState.IDLE
                return {"response": "I see a charge of $19.99 for the movie rental 'Gladiator II' on Nov 24th. Is this the charge you are asking about?"}
            
            elif self.dispute_stage == 1:
                # Customer responds (likely denying it)
                if "yes" in msg_lower or "correct" in msg_lower or "didn't" in msg_lower or "not me" in msg_lower:
                     self.dispute_stage = 2
                     await asyncio.sleep(1)
                     self.state = AgentState.IDLE
                     return {"response": "Our records show this was rented from the Living Room TV box. Did anyone else in your household perhaps rent it?"}
            
            elif self.dispute_stage == 2:
                 # Customer denies again
                 self.dispute_stage = 0 # Reset
                 self.state = AgentState.WAITING_FOR_APPROVAL
                 return {
                     "response": "I understand. Since you're a valued customer, I can request a one-time courtesy credit for this rental. I just need supervisor approval.",
                     "action_required": True,
                     "amount": 19.99,
                     "reason": "One-time courtesy credit for disputed movie rental (Gladiator II)"
                 }

        # --- Existing Credit Logic (Fallback) ---
        # Simple parsing for credit requests like "credit $10" or "refund 5"
        amount = 0.0
        words = message.split()
        for word in words:
            clean_word = word.replace('$', '')
            try:
                val = float(clean_word)
                amount = val
                break
            except ValueError:
                continue
        
        if amount > 0:
            if amount <= self.approval_threshold:
                await asyncio.sleep(1)
                self.state = AgentState.IDLE
                return {"response": f"I have approved your credit of ${amount}."}
            else:
                self.state = AgentState.WAITING_FOR_APPROVAL
                return {
                    "response": "I need supervisor approval for this amount. Please wait...",
                    "action_required": True,
                    "amount": amount,
                    "reason": "Credit request exceeds threshold"
                }
        
class UnifiedAgent(BaseAgent):
    def __init__(self):
        super().__init__("UnifiedAgent")
        # Tech State
        self.troubleshoot_steps = ["Restart Modem", "Check Coax", "Schedule Tech"]
        self.current_troubleshoot_idx = 0
        self.modem_steps = [
            "Great! Let's get your new modem set up. \n\n**Step 1:** Open the box and take out the modem and the power cord.",
            "**Step 2:** Connect the coax cable from the wall to the back of the modem. Make sure it's finger-tight.",
            "**Step 3:** Plug the power cord into the modem and then into an electrical outlet.",
            "**Step 4:** Wait for the 'Online' light to turn solid white. This might take up to 10 minutes.",
            "**Step 5:** Connect your devices to the WiFi using the Network Name (SSID) and Password printed on the bottom of the modem."
        ]
        self.current_modem_idx = -1
        self.in_modem_flow = False
        
        # Billing State
        self.approval_threshold = 5.0
        self.dispute_stage = 0

    async def process(self, message: str) -> Dict[str, Any]:
        self.state = AgentState.PROCESSING
        msg_lower = message.lower()
        await asyncio.sleep(1)

        # --- Modem Installation Flow ---
        if "modem" in msg_lower and ("install" in msg_lower or "setup" in msg_lower or "set up" in msg_lower):
            self.in_modem_flow = True
            self.current_modem_idx = 0
            self.state = AgentState.IDLE
            return {"response": self.modem_steps[0]}
            
        if self.in_modem_flow:
            if "quit" in msg_lower or "stop" in msg_lower:
                self.in_modem_flow = False
                self.current_modem_idx = -1
                self.state = AgentState.IDLE
                return {"response": "Modem setup cancelled. How else can I help?"}
                
            self.current_modem_idx += 1
            if self.current_modem_idx < len(self.modem_steps):
                self.state = AgentState.IDLE
                return {"response": self.modem_steps[self.current_modem_idx]}
            else:
                self.in_modem_flow = False
                self.current_modem_idx = -1
                self.state = AgentState.COMPLETED
                return {"response": "Congratulations! Your modem should be all set up. Is there anything else?"}

        # --- System Check / Tech Dispatch Flow ---
        if "internet" in msg_lower or "slow" in msg_lower or "down" in msg_lower:
             if "reset" in msg_lower:
                 self.current_troubleshoot_idx = 0
                 
             if self.current_troubleshoot_idx == 0:
                 self.current_troubleshoot_idx += 1
                 self.state = AgentState.IDLE
                 return {"response": "I'm sorry to hear about your internet issues. Let's try to fix it. First, I'm going to run a remote system health check. This will take a few seconds..."}
             
             elif self.current_troubleshoot_idx == 1:
                 await asyncio.sleep(2)
                 success = random.choice([True, False])
                 
                 if success:
                     self.current_troubleshoot_idx = 0
                     self.state = AgentState.IDLE
                     return {"response": "Good news! The system check cleared some temporary cache errors on your line. Your internet should be back to normal speed now. Please check it."}
                 else:
                     self.current_troubleshoot_idx += 1
                     self.state = AgentState.WAITING_FOR_APPROVAL
                     return {
                         "response": "The system check detected a signal degradation that I can't fix remotely. We need to send a technician to your home.",
                         "action_required": True,
                         "amount": 0,
                         "reason": "Technician Dispatch Required (Signal Degradation)"
                     }

        # --- Movie Rental Dispute Flow ---
        if "bill" in msg_lower or "movie" in msg_lower or "rental" in msg_lower or "charge" in msg_lower:
            if self.dispute_stage == 0:
                self.dispute_stage = 1
                self.state = AgentState.IDLE
                return {"response": "I see a charge of $19.99 for the movie rental 'Gladiator II' on Nov 24th. Is this the charge you are asking about?"}
            
            elif self.dispute_stage == 1:
                if "yes" in msg_lower or "correct" in msg_lower or "didn't" in msg_lower or "not me" in msg_lower:
                     self.dispute_stage = 2
                     self.state = AgentState.IDLE
                     return {"response": "Our records show this was rented from the Living Room TV box. Did anyone else in your household perhaps rent it?"}
            
            elif self.dispute_stage == 2:
                 self.dispute_stage = 0
                 self.state = AgentState.WAITING_FOR_APPROVAL
                 return {
                     "response": "I understand. Since you're a valued customer, I can request a one-time courtesy credit for this rental. I just need supervisor approval.",
                     "action_required": True,
                     "amount": 19.99,
                     "reason": "One-time courtesy credit for disputed movie rental (Gladiator II)"
                 }

        # --- General Credit Logic ---
        amount = 0.0
        words = message.split()
        for word in words:
            clean_word = word.replace('$', '')
            try:
                val = float(clean_word)
                amount = val
                break
            except ValueError:
                continue
        
        if amount > 0:
            if amount <= self.approval_threshold:
                self.state = AgentState.IDLE
                return {"response": f"I have approved your credit of ${amount}."}
            else:
                self.state = AgentState.WAITING_FOR_APPROVAL
                return {
                    "response": "I need supervisor approval for this amount. Please wait...",
                    "action_required": True,
                    "amount": amount,
                    "reason": "Credit request exceeds threshold"
                }
        
        self.state = AgentState.IDLE
        return {"response": "I can help with Internet troubleshooting, Modem installation, or Billing questions. How can I help you today?"}
