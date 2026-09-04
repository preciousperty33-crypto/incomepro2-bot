import os
from telethon import TelegramClient
from telethon.sessions import StringSession

session_string = os.getenv("USER_SESSION_STRING")
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

client = TelegramClient(StringSession(session_string), int(api_id) if api_id else 0, api_hash or "")

async def main():
    print("IncomePro Bot Started Successfully!")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
