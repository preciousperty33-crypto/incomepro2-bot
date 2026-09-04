from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 39002147
API_HASH = 'cab2974c1f00eb3d40a3794da7b6d43b'

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n\nYOUR USER_SESSION_STRING BELOW:\n")
    print(client.session.save())
    print("\nCopy the long text above and keep it safe!\n")
