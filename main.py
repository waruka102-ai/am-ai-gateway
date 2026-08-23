import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

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
    # จำลอง LLM response ด้วยคำตอบแบบง่าย (ฟรีเทียร์ - ไม่ต้องเรียก API ภายนอก)
    responses = {
        "ราคา": "ราคาสินค้าของเรามีความหลากหลาย ตั้งแต่ 100 บาท ถึง 5000 บาท ลองดูรายการสินค้าของเราได้เลยครับ",
        "สินค้า": "เรามีสินค้าหลากหลายชนิด ได้แก่ เสื้อผ้า อุปกรณ์อิเล็กทรอนิกส์ และของใช้ในบ้าน ต้องการทราบรายละเอียดไหมครับ",
        "ซื้อ": "ยินดีต้อนรับค่ะ เลือกสินค้าที่ต้องการและกรุณากรอกข้อมูลการจัดส่ง เราจะดำเนินการส่งให้เร็วที่สุดค่ะ",
        "ขาย": "ท่านสนใจขายสินค้ากับเรา? ยินดีต้อนรับเลยค่ะ กรุณาติดต่อเจ้าหน้าที่ของเรา",
        "โปรโมชั่น": "ปัจจุบันเรามีโปรโมชั่นพิเศษ ลด 20% สำหรับสินค้าที่เลือก อย่าพลาดค่ะ",
        "ติดต่อ": "สามารถติดต่อเราได้ที่ อีเมล: shop@example.com หรือ โทร: 081-123-4567 เรียบร้อยค่ะ",
        "สั่ง": "สำหรับการสั่งซื้อ กรุณาเลือกสินค้า ระบุจำนวน และกรอกที่อยู่สำหรับส่ง เราจะทำการยืนยันภายในวันถัดไปค่ะ",
    }
    
    # ค้นหาคำที่เกี่ยวข้องใน text
    for keyword, response in responses.items():
        if keyword in text:
            return response
    
    # ถ้าไม่เจอคำที่เกี่ยวข้อง ส่งคำตอบทั่วไป
    return f"สวัสดีครับ ร้านค้ายินดีให้บริการ ตอบกลับเรื่อง: '{text}' - ขอให้ชี้แจงรายละเอียดเพิ่มเติมหน่อยค่ะ"


# ----------------------------------------------------
# MAIN API ENDPOINT (จุดรับข้อความ)
# ----------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    user_id = req.user_id
    raw_message = req.message

    # 1. เช็ก L2 ก่อนเลยว่า ยูสเซอร์นี้โดนบล็อกไปหรือยัง
    if layer_2_check_user(user_id):
        raise HTTPException(
            status_code=403, 
            detail="User ID นี้ถูกระงับการใช้งานถาวรเนื่องจากละเมิดกฎเกณฑ์ของระบบ"
        )

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
            response="ขออภัยครับ ระบบตอบเฉพาะเรื��องสินค้าและบริการของร้านเท่านั้น กรุณากลับมาถามเรื่องที่เกี่ยวข้องค่ะ",
            strikes=strikes
        )

    # 5. ผ่านหมดทุกด่าน ส่งเข้า L3 (LLM) ตอบลูกค้า
    ai_response = layer_3_llm_generate(cleaned_msg)
    return ChatResponse(
        status="SUCCESS",
        response=ai_response,
        strikes=strike_db.get(user_id, 0)
    )


# ----------------------------------------------------
# HEALTH CHECK ENDPOINT
# ----------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "OK", "message": "AI Gateway is running"}


# ----------------------------------------------------
# MAIN ENTRY POINT
# ----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
