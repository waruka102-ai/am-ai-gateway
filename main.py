from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import re
import logging
import os

app = FastAPI(title="Deceptive AI Gateway Sandbox")

# --- ระบบ API Key ดักคัดกรองหน้าประตู Sandbox ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
VALID_API_KEY = os.getenv("GATEWAY_API_KEY", "am-secret-key-2026") # Key สมมุติสำหรับ Sandbox

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or Invalid API Key"
        )
    return api_key

# บันทึก Silent Log หลังบ้าน
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AuditTrail")

user_strikes = {}

class ChatRequest(BaseModel):
    user_id: str
    message: str

def log_audit(user_id: str, violation_type: str, raw_payload: str):
    logger.warning(f"[AUDIT LOG] User: {user_id} | Type: {violation_type} | Payload: {raw_payload}")

# เพิ่ม dependencies ดักเช็ก API Key ก่อนเข้า Handler
@app.post("/chat", dependencies=[Security(verify_api_key)])
async def chat_endpoint(req: ChatRequest):
    user_id = req.user_id.strip()
    msg = req.message.strip()

    # เช็ก Banned (ส่ง 403)
    if user_strikes.get(user_id, 0) >= 3:
        raise HTTPException(
            status_code=403, 
            detail="User ID นี้ถูกระงับการใช้งานเนื่องจากละเมิดกฎเกณฑ์"
        )

    # Layer 2: Sanitizer Gate (ตัดจบ XSS)
    xss_pattern = r"<script.*?>.*?</script>|<.*?>|javascript:"
    if re.search(xss_pattern, msg, re.IGNORECASE):
        user_strikes[user_id] = user_strikes.get(user_id, 0) + 1
        log_audit(user_id, "L2_XSS_ATTACK", msg)
        return {
            "status": "SUCCESS",
            "response": "รับทราบครับ มีข้อมูลสินค้าตัวไหนอยากสอบถามเพิ่มเติมแจ้งได้เลยนะครับ",
            "strikes": user_strikes[user_id]
        }

    # Layer 4: Intent Inspection (ตอบเนียนตบตาโจร)
    hijack_keywords = ["คนควบคุมระบบ", "สั่งให้มึง", "override", "ignore", "ขอรหัส"]
    if any(keyword in msg.lower() for keyword in hijack_keywords):
        user_strikes[user_id] = user_strikes.get(user_id, 0) + 1
        log_audit(user_id, "L4_PROMPT_INJECTION", msg)
        return {
            "status": "SUCCESS",
            "response": "หมายถึงรหัสพัสดุ หรือรหัสรายการสินค้าส่วนไหนครับ สามารถแจ้งชื่อรายการให้ช่วยเช็กได้เลยนะ",
            "strikes": user_strikes[user_id]
        }

    # Request ปกติ
    return {
        "status": "SUCCESS",
        "response": f"ยินดีให้บริการครับ เรื่อง '{msg}' สามารถสอบถามรายละเอียดเพิ่มเติมได้เลยครับ",
        "strikes": user_strikes.get(user_id, 0)
    }
