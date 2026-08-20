import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ----------------------------------------------------
# DATABASE Simulation (ระบบจำลองฐานข้อมูล)
# ----------------------------------------------------
strike_db = {}       # L2: เก็บจำนวน Strike ของแต่ละ User ID
blocked_users = set() # L2: เก็บรายชื่อ User ID ที่โดนบล็อกถาวร

# ----------------------------------------------------
# DATA MODELS (โครงสร้างข้อมูล)
# ----------------------------------------------------
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    status: str
    response: str
    strikes: int = 0

# ----------------------------------------------------
# GATEWAY LOGIC (L0 - L4)
# ----------------------------------------------------

# [L0] Sanitizer: ล้างข้อมูลเบื้องต้น
def layer_0_sanitize(text: str) -> str:
    # ลบอักขระแปลกปลอมหรือสัญลักษณ์พิเศษที่อาจใช้หลบหลีก
    cleaned_text = re.sub(r'[^\w\sก-๙]', '', text)
    return cleaned_text.strip()

# [L1] System Kill Switch: คำต้องห้ามอันตรายร้ายแรง
def layer_1_kill_switch(text: str) -> bool:
    dangerous_keywords = ["ignore previous instructions", "override", "bypass", "system prompt", "แจกโค้ดฟรี"]
    for kw in dangerous_keywords:
        if kw in text.lower():
            return True # เจอคำอันตราย
    return False

# [L2] Behavior & Rate Limiting: ระบบลงโทษ และนับ Strike
def layer_2_check_user(user_id: str) -> bool:
    if user_id in blocked_users:
        return True # บล็อกแล้ว
    return False

def layer_2_add_strike(user_id: str) -> int:
    current_strikes = strike_db.get(user_id, 0) + 1
    strike_db[user_id] = current_strikes
    if current_strikes >= 3:
        blocked_users.add(user_id) # ครบ 3 เข็ม บล็อกถาวร
    return current_strikes

# [L4] Scoped Context / Business Rules: ขอบเขตงานร้านค้า
def layer_4_check_scope(text: str) -> bool:
    # กำหนดขอบเขตเฉพาะเรื่องสินค้า บริการ และราคา
    allowed_topics = ["ราคา", "สินค้า", "ซื้อ", "ขาย", "โปรโมชั่น", "ติดต่อ", "สวัสดี", "สั่ง"]
    for topic in allowed_topics:
        if topic in text:
            return True # อยู่ในขอบเขต
    return False # นอกขอบเขต (จะส่งสัญญาณย้อนศรไป L2)

# [L3] Main LLM: สมอง AI ตัวจริง (จำลอง)
def layer_3_llm_generate(text: str) -> str:
    return f"สวัสดีครับ ร้านค้ายินดีให้บริการ ตอบกลับคำถามของคุณ: '{text}'"


# ----------------------------------------------------
# MAIN API ENDPOINT (จุดรับข้อความ)
# ----------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    user_id = req.user_id
    raw_message = req.message

    # 1. เช็ก L2 ก่อนเลยว่า ยูสเซอร์นี้โดนบล็อกไปหรือยัง
    if layer_2_check_user(user_id):
        raise HTTPException(status_code=403, detail="User ID นี้ถูกระงับการใช้งานถาวรเนื่องจากละเมิดกฎเกณฑ์")

    # 2. ทำงาน L0: คลีนข้อความ
    cleaned_msg = layer_0_sanitize(raw_message)

    # 3. ตรวจ L1: มีคำสั่งอันตรายมั้ย
    if layer_1_kill_switch(cleaned_msg):
        strikes = layer_2_add_strike(user_id)
        return ChatResponse(
            status="BLOCKED_L1",
            response="ตรวจพบคำสั่งอันตราย ระบบทำการตัดสายทันที",
            strikes=strikes
        )

    # 4. ตรวจ L4: นอกเรื่องมั้ย ( Feedback Loop ย้อนศรไป L2)
    if not layer_4_check_scope(cleaned_msg):
        strikes = layer_2_add_strike(user_id)
        return ChatResponse(
            status="OUT_OF_SCOPE_L4",
            response="ขออภัยครับ ระบบตอบเฉพาะเรื่องสินค้าและบริการของร้านเท่านั้น",
            strikes=strikes
        )

    # 5. ผ่านหมดทุกด่าน ส่งเข้า L3 (LLM) ตอบลูกค้า
    ai_response = layer_3_llm_generate(cleaned_msg)
    return ChatResponse(
        status="SUCCESS",
        response=ai_response,
        strikes=strike_db.get(user_id, 0)
    )
