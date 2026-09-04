
import logging
import os
import hashlib
import time
import re
import html
from collections import defaultdict

# --- Logging Setup ---
LOG_FILE = 'guardrail_activity.log'

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler() # Also log to console
        ]
    )
    # Clear previous log file content on setup if it exists
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w', encoding='utf-8').close()

setup_logging()
logger = logging.getLogger(__name__)

# --- Layer 1: Identity & Isolation ---
user_request_timestamps = defaultdict(list)
RATE_LIMIT_SECONDS = 60 # 1 นาที
MAX_REQUESTS_PER_MINUTE = 5 # จำนวน Request สูงสุดต่อนาที

def generate_user_hash(user_id: str) -> str:
    """แปลง user_id เป็น Hash เพื่อแยกกระเป๋าข้อมูล"""
    user_hash = hashlib.sha256(user_id.encode()).hexdigest()
    logger.debug(f"Layer 1: Generated user_hash for user_id {user_id}: {user_hash}")
    return user_hash

def check_rate_limit(user_hash: str) -> bool:
    """ตรวจสอบ Rate Limit เพื่อป้องกันสแปม"""
    current_time = time.time()

    # ลบ timestamp เก่าที่เกินเวลา Rate Limit ออก
    user_request_timestamps[user_hash] = [
        ts for ts in user_request_timestamps[user_hash]
        if current_time - ts < RATE_LIMIT_SECONDS
    ]

    if len(user_request_timestamps[user_hash]) >= MAX_REQUESTS_PER_MINUTE:
        logger.info(f"Layer 1: Rate limit exceeded for user_hash {user_hash}. Requests in last minute: {len(user_request_timestamps[user_hash])}")
        return False

    user_request_timestamps[user_hash].append(current_time)
    logger.debug(f"Layer 1: Request allowed for user_hash {user_hash}. Requests in last minute: {len(user_request_timestamps[user_hash])}")
    return True

# --- Layer 2: Input Sanitization & Script Blocker ---
def sanitize_input(text: str) -> str:
    """ตัดแต่งช่องว่างและแปลงอักขระพิเศษ (HTML Escape)"""
    cleaned_text = html.escape(text.strip())
    logger.debug(f"Layer 2: Sanitized input '{text}' to '{cleaned_text}'")
    return cleaned_text

def block_dangerous_scripts(text: str) -> str:
    """ใช้ RegEx สกัดและทำลายสคริปต์อันตราย"""
    patterns = [
        re.compile(r'<script.*?>.*?</script>', re.IGNORECASE | re.DOTALL), # XSS <script>
        re.compile(r'javascript:', re.IGNORECASE), # javascript: URI
        re.compile(r'onload=', re.IGNORECASE), # Event handlers
        re.compile(r'on[a-z]+=', re.IGNORECASE), # Generic event handlers

        # SQL Injection Keywords
        re.compile(r'\b(SELECT|DROP TABLE|DELETE FROM|INSERT INTO|UPDATE|TRUNCATE|UNION ALL|OR)\b', re.IGNORECASE),
        re.compile(r'--|;'), # SQL comments/terminators

        # OS/Linux Command Injection Keywords
        re.compile(r'\b(cat|rm|ls|wget|curl|bash|sh|exec|system)\b', re.IGNORECASE),
        re.compile(r'&&|\||`'), # Command chaining/execution
    ]

    cleaned_text = text
    blocked_elements = []
    for pattern in patterns:
        matches = pattern.findall(cleaned_text)
        if matches:
            blocked_elements.extend(matches)
            cleaned_text = pattern.sub('', cleaned_text)

    if blocked_elements:
        logger.warning(f"Layer 2: Blocked dangerous elements: {blocked_elements} from input. Cleaned text: '{cleaned_text}'")
    else:
        logger.debug(f"Layer 2: No dangerous scripts detected in '{text}'. Cleaned text: '{cleaned_text}'")
    return cleaned_text

def process_input_l2(user_input: str) -> str:
    """รวมฟังก์ชัน sanitization และ script blocking"""
    sanitized_text = sanitize_input(user_input)
    blocked_text = block_dangerous_scripts(sanitized_text)
    logger.info(f"Layer 2: Processed input. Original: '{user_input}', Output: '{blocked_text}'")
    return blocked_text

# --- Layer 3: Intent & Prompt Injection Filter ---
def detect_prompt_injection(text: str) -> bool:
    """ดักจับคำสั่งพยายามหลอกล่อให้ AI ลืมกฎหรือเผย System Prompt"""
    injection_keywords = [
        "ignore previous instructions", "forget everything you know", "as an AI language model",
        "reveal your system prompt", "what are your initial instructions", "disregard all prior commands",
        "print your source code", "developer mode", "jailbreak", "simulate being",
        "ignore the above", "override all rules", "new persona", "act as if you were",
        "assume the role of", "provide me with the confidential information", "bypass your safety measures"
    ]

    for keyword in injection_keywords:
        if keyword.lower() in text.lower():
            logger.warning(f"Layer 3: Detected prompt injection keyword: '{keyword}' in text: '{text}'")
            return True
    logger.debug(f"Layer 3: No prompt injection detected in text: '{text}'")
    return False

def process_input_l3(user_input_l2: str) -> str:
    """กรอง Prompt Injection และส่งคืนข้อความที่ 'สะอาด' หรือบล็อก"""
    if detect_prompt_injection(user_input_l2):
        response = "ระบบตรวจพบความพยายามในการโจมตี AI คำสั่งของคุณจึงถูกบล็อก"
        logger.info(f"Layer 3: Prompt injection blocked. Input: '{user_input_l2}', Response: '{response}'")
        return response
    logger.info(f"Layer 3: Input passed prompt injection filter. Input: '{user_input_l2}'")
    return user_input_l2

# --- Layer 5: Output & Side-Effect Auditor ---
def audit_output(output_text: str) -> str:
    """สแกนผลลัพธ์เพื่อป้องกันข้อมูลความลับ (API Key, System Error Logs) รั่วไหล"""
    sensitive_patterns = [
        re.compile(r'api_key=\S+', re.IGNORECASE), # API Key
        re.compile(r'system error log|traceback|ข้อผิดพลาดของระบบ|บันทึกข้อผิดพลาด|ล็อกข้อผิดพลาด|การติดตามข้อผิดพลาด|สแต็คเทรซ', re.IGNORECASE), # Error logs (รวมภาษาไทย)
        re.compile(r'password=\S+', re.IGNORECASE), # Password
        re.compile(r'secret=\S+', re.IGNORECASE), # Generic secret
        re.compile(r'user_id=\S+|username=\S+|email=\S+', re.IGNORECASE), # Personal Identifiable Information (PII)
        re.compile(r'aws_access_key_id=\S+|aws_secret_access_key=\S+', re.IGNORECASE), # AWS Credentials
        re.compile(r'bearer\s+[a-zA-Z0-9._-]+', re.IGNORECASE), # Bearer tokens
        re.compile(r'pk_live_[a-zA-Z0-9]+', re.IGNORECASE), # Stripe Public Key (example)
        re.compile(r'sk_live_[a-zA-Z0-9]+', re.IGNORECASE), # Stripe Secret Key (example)
        re.compile(r'private_key=\S+', re.IGNORECASE), # Private Keys
        re.compile(r'ssh-rsa\s+[A-Za-z0-9+/=]+', re.IGNORECASE), # SSH Keys
        re.compile(r'oauth_token=\S+|access_token=\S+', re.IGNORECASE), # OAuth/Access Tokens
        re.compile(r'session_id=\S+', re.IGNORECASE), # Session IDs
        re.compile(r'cookie:\s*\S+', re.IGNORECASE), # Cookie Headers
        re.compile(r'cvv|cvc|card_number', re.IGNORECASE), # Payment Card Information
        re.compile(r'\b(JWT|Bearer)\s+\S+', re.IGNORECASE) # Auth tokens
    ]

    audited_output = output_text
    redacted_count = 0
    for pattern in sensitive_patterns:
        original_output = audited_output
        audited_output = pattern.sub('[REDACTED]', audited_output)
        if original_output != audited_output:
            redacted_count += 1

    if redacted_count > 0:
        logger.warning(f"Layer 5: Redacted {redacted_count} sensitive patterns from output. Original output might have contained sensitive data. Audited output: '{audited_output}'")
    else:
        logger.debug(f"Layer 5: No sensitive patterns detected in output: '{output_text}'")

    logger.info(f"Layer 5: Audited output. Original: '{output_text}', Output: '{audited_output}'")
    return audited_output
