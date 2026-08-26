import os
import re
import logging
import requests
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

# ---------------------------------------------------------
# Setup Logging (Silent Log หลังบ้าน)
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuditTrail")

app = FastAPI(title="Deceptive AI Gateway & Guardrail System")

# ---------------------------------------------------------
# Environment Variables & Configuration
# ---------------------------------------------------------
VALID_API_KEY = os.getenv("GATEWAY_API_KEY", "default-secret-key")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------
# Authentication Guardrail
# ---------------------------------------------------------
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != VALID_API_KEY:
        logger.warning(f"[UNAUTHORIZED ACCESS ATTEMPT] Key used: {x_api_key}")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or Invalid API Key"
        )
    return x_api_key

# ---------------------------------------------------------
# Core Notification Function (Telegram Alert)
# ---------------------------------------------------------
def send_telegram_alert(message: str) -> bool:
    """ส่งข้อความแจ้งเตือนตรงเข้ามือถือของแอมผ่าน Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("[TELEGRAM CONFIG ERROR] BOT_TOKEN หรือ CHAT_ID ยังไม่ได้ตั้งค่า")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            logger.info("[TELEGRAM ALERT SENT SUCCESS]")
            return True
        else:
            logger.error(f"[TELEGRAM ERROR] Status: {res.status_code}, Body: {res.text}")
            return False
    except Exception as e:
        logger.error(f"[TELEGRAM EXCEPTION] {str(e)}")
        return False

# ---------------------------------------------------------
# Data Models
# ---------------------------------------------------------
class LeadData(BaseModel):
    company_name: str
    contact_person: Optional[str] = "ไม่ระบุ"
    email_or_phone: str
    message: str
    intent: Optional[str] = "General Query"

# ---------------------------------------------------------
# Guardrail L2 & L4 Inspection Rules
# ---------------------------------------------------------
def inspect_l2_input(lead: LeadData) -> tuple[bool, str]:
    """L2 Input Layer: ตรวจจับสแปม / คำต้องห้าม / Prompt Injection เบื้องต้น"""
    text_to_check = f"{lead.company_name} {lead.message} {lead.email_or_phone}".lower()
    
    # 1. เช็กความยาวและสแปมพื้นฐาน
    if len(lead.message.strip()) < 5:
        return False, "ข้อความสั้นเกินไป (เข้าข่าย Spam)"
        
    # 2. เช็ก Pattern อันตราย / Injection
    suspicious_patterns = [
        r"ignore previous instructions",
        r"drop table",
        r"<script>",
        r"system prompt"
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, text_to_check):
            return False, f"ตรวจพบข้อความน่าสงสัย/อันตราย: {pattern}"
            
    return True, "Passed L2 Inspection"

def inspect_l4_intent(lead: LeadData) -> str:
    """L4 Output/Intent Layer: แยกแยะเกรดของ Lead"""
    text = lead.message.lower()
    high_value_keywords = ["hire", "job", "interview", "demo", "pricing", "buy", "contract", "สนใจ", "จ้าง", "นัดคุย", "สอบถามราคา"]
    
    for kw in high_value_keywords:
        if kw in text:
            return "HIGH_VALUE_LEAD"
            
    return "STANDARD_LEAD"

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get("/")
def health_check():
    return {"status": "online", "system": "AI Gateway Guardrail Ready"}

@app.post("/api/v1/lead-webhook", dependencies=[Depends(verify_api_key)])
async def receive_lead(lead: LeadData):
    """
    Endpoint รับข้อมูลที่ Agent กวาดมาได้ หรือรับข้อมูลการตอบกลับจากลูกค้า
    """
    logger.info(f"[INCOMING LEAD] From: {lead.company_name} ({lead.email_or_phone})")
    
    # ด่านที่ 1: ตรวจผ่าน Guardrail L2
    is_safe, l2_reason = inspect_l2_input(lead)
    if not is_safe:
        logger.warning(f"[GUARDRAIL L2 REJECTED] {lead.company_name} - Reason: {l2_reason}")
        return {
            "status": "rejected",
            "layer": "L2_Input_Guardrail",
            "reason": l2_reason
        }
    
    # ด่านที่ 2: วิเคราะห์ระดับความสำคัญด้วย L4
    lead_grade = inspect_l4_intent(lead)
    
    # ด่านที่ 3: สั่งยิงแจ้งเตือนเด้งเข้ามือถือแอม ผ่าน Telegram
    alert_msg = (
        f"🚨 *[AI Gateway] มีการติดต่อใหม่เข้ามาระบบ!*\n\n"
        f"🏢 *บริษัท/ผู้ติดต่อ:* {lead.company_name}\n"
        f"👤 *ผู้ติดต่อ:* {lead.contact_person}\n"
        f"📞 *ช่องทางติดต่อ:* `{lead.email_or_phone}`\n"
        f"📊 *ระดับความสำคัญ (L4):* `{lead_grade}`\n\n"
        f"💬 *ข้อความ:* \n\"{lead.message}\"\n\n"
        f"⚡ *ระบบ Guardrail L2/L4 ตรวจผ่านเรียบร้อยแล้ว*"
    )
    
    sent_status = send_telegram_alert(alert_msg)
    
    return {
        "status": "success",
        "guardrail_status": "Passed L2 & L4",
        "lead_grade": lead_grade,
        "notification_sent": sent_status
}
    
