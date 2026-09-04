import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

session_string = os.getenv("USER_SESSION_STRING")
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

if not session_string or not api_id or not api_hash:
    print("Error: Missing required environment variables (USER_SESSION_STRING, API_ID, or API_HASH).")

client = TelegramClient(StringSession(session_string), int(api_id or 0), api_hash or "")

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.is_private:
        print(f"Received message: {event.text}")
        await event.respond("Hello! Income Pro Bot is online and running on Railway.")

async def main():
    print("IncomePro Bot Started Successfully!")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
