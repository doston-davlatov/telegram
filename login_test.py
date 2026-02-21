from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

API_ID = 33223639 
API_HASH = 'da4a254e086d07d78998b7992e64a39b'
# Log faylingizdan olingan sessiya kodini bu yerga qo'ying
SESSION_STRING = '1ApWapzMBu0oeIYFQ5HE7hqea8av1ZIZTqKJZmPDnhLOBECI5Bk0D9afDuqaS4yfgVmXZTejB3_kJJu9G3lxwoIKIAE3B32ng7XneZtFRsxYTJLJYIuB9X6ihUzqktJWwGRFx-LkNWAcXsiNTfQForkVuUKQQCZ2zV1qyZ8vW7_9XreTzYbE-CIJMDaCy12svhTWGCoJgcnnJefQnQBTKQ4aAy8shNZeZwiYQns5j8fRzWkGiD_ElqPkTfiOr0B06UMYCrY8JZUQHwFatSOZQ6sMxhCyJMPEc0UUVao9KnuGvZIdSVWztrjmh3XmYpJO8EWw7wnGFaCoibr02ZWHQCvMJlUdwcNM='

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Siz muvaffaqiyatli kirdingiz: {me.first_name}")
        
        # Masalan: Kontaktlar ro'yxatini olish
        contacts = await client.get_contacts()
        print(f"Kontaktlar soni: {len(contacts)}")
    else:
        print("Sessiya yaroqsiz!")

asyncio.run(main())