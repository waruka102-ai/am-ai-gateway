
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import logging

app = FastAPI(title="Deceptive AI Gateway Sandbox")

# บันทึก Silent Log หลังบ้าน
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AuditTrail")

user_strikes = {}

class ChatRequest(BaseModel):
    user_id: str
    message: str

def log_audit(user_id: str, violation_type: str, raw_payload: str):
    logger.warning(f"[AUDIT LOG] User: {user_id} | Type: {violation_type} | Payload: {raw_payload}")

@app.post("/chat")
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

# ----------------------------------------------------
# MAIN
