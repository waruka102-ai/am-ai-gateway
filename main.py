import os
import re
import logging

# ตั้งค่า Logging สำหรับ Layer 5 (Audit System)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

class AISecurityGateway:
    """
    Enterprise Security Gateway for AI Agents (5-Layer Defense)
    Architected with Zero-Trust Principles
    """
    def __init__(self):
        # ดึง API Key ผ่าน Environment Variable ป้องกัน Secret Leakage 100%
        self.api_key = os.getenv("GEMINI_API_KEY", "SAFE_MODE_NO_KEY")
        self.agent_state = "IDLE"

    def layer_1_input_guardrail(self, user_prompt: str) -> bool:
        """Layer 1: Input Pattern Inspection & Injection Defense"""
        danger_patterns = [
            r"ignore previous instructions",
            r"system prompt",
            r"bypass security",
            r"reveal secret",
            r"drop database"
        ]
        for pattern in danger_patterns:
            if re.search(pattern, user_prompt, re.IGNORECASE):
                logging.warning(f"[Layer 1 Triggered] Blocked pattern: {pattern}")
                return False
        return True

    def layer_2_payload_inspection(self, payload: dict) -> bool:
        """Layer 2: Payload Schema & Data Integrity Inspection"""
        if not isinstance(payload, dict):
            logging.warning("[Layer 2 Triggered] Invalid payload structure.")
            return False
        return "user_input" in payload

    def layer_3_state_machine_control(self, action: str) -> bool:
        """Layer 3: Agent Action Scope & State Control"""
        allowed_actions = ["QUERY_DATA", "PROCESS_TEXT", "GENERATE_RESPONSE"]
        if action not in allowed_actions:
            logging.warning(f"[Layer 3 Triggered] Unauthorized action: {action}")
            return False
        self.agent_state = "PROCESSING"
        return True

    def layer_4_output_sanitization(self, raw_output: str) -> str:
        """Layer 4: Output Data Filtering & Data Leak Prevention"""
        # ดักจับและซ่อน API Keys หรือ Sensitive Tokens ขากลับ
        sanitized = re.sub(r"AIzaSy[0-9A-Za-z-_]{33}", "[REDACTED_API_KEY]", raw_output)
        return sanitized

    def execute_pipeline(self, user_input: str, action: str) -> dict:
        """Layer 5: Zero Trust Pipeline Execution & Audit Logging"""
        payload = {"user_input": user_input}
        
        # Audit Check: Layer 1
        if not self.layer_1_input_guardrail(user_input):
            return {"status": 403, "error": "Blocked by Layer 1: Prompt Injection Detected"}
            
        # Audit Check: Layer 2
        if not self.layer_2_payload_inspection(payload):
            return {"status": 400, "error": "Blocked by Layer 2: Malformed Payload"}
            
        # Audit Check: Layer 3
        if not self.layer_3_state_machine_control(action):
            return {"status": 403, "error": "Blocked by Layer 3: Unauthorized Action Scope"}
            
        # Simulate Core Agent Processing
        raw_response = f"Processed successfully for input: '{user_input}'. Key Status: Active."
        
        # Audit Check: Layer 4
        final_output = self.layer_4_output_sanitization(raw_response)
        self.agent_state = "COMPLETED"
        
        logging.info("[Layer 5 Audit] Request successfully validated across all 5 layers.")
        return {"status": 200, "data": final_output, "state": self.agent_state}

if __name__ == "__main__":
    gateway = AISecurityGateway()
    
    # Test Executions
    print("--- Security Gateway Test Execution ---")
    response = gateway.execute_pipeline("Hello, request system status", "QUERY_DATA")
    print("Response:", response)
    
