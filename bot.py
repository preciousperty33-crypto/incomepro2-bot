import asyncio
import os
import re
import pytesseract
from PIL import Image
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

API_ID = int(os.environ.get("API_ID", "39002147"))
API_HASH = os.environ.get("API_HASH", "cab2974c1f00eb3d40a3794da7b6d43b")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8626089348:AAFX6HdxhRnGbFOBxc49EDTQ5Dn-3XQKe3Q")
USER_SESSION_STRING = os.environ.get("USER_SESSION_STRING", "")

CHANNEL_TARGET = -1004414227077
SOURCE_CHANNEL = -1003973061596

WEBSITE_LINK = "https://income-pro-ng.lovable.app/"

user_client = TelegramClient(StringSession(USER_SESSION_STRING), API_ID, API_HASH)
bot_client = TelegramClient('incomepro_bot_session', API_ID, API_HASH)

scheduler = AsyncIOScheduler(timezone="Africa/Lagos")

user_states = {}
registered_users = set()
user_msg_count = {}
admin_id = None
tutorial_video_msg = None

pending_posts = {}

schedule_data = {
    "morning_msgs": [],
    "evening_msgs": []
}

def remove_links(text):
    if not text:
        return ""
    link_pattern = r'(https?://\S+|www\.\S+|t\.me/\S+|\b[A-Za-z0-9.-]+\.(?:com|net|org|app|ng|io|me|co|info)\b\S*)'
    clean_text = re.sub(link_pattern, '', text, flags=re.IGNORECASE)
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    return "\n".join(lines)

async def send_single_scheduled_post(msg_obj, post_type, time_str):
    try:
        if msg_obj.media:
            clean_caption = remove_links(msg_obj.message)
            await bot_client.send_file(CHANNEL_TARGET, msg_obj.media, caption=clean_caption)
        else:
            clean_msg = remove_links(msg_obj.message)
            await bot_client.send_message(CHANNEL_TARGET, clean_msg)
        print(f"✅ Posted {post_type} message scheduled for {time_str} to channel.")
    except FloodWaitError as e:
        print(f"🚨 Rate limited! Waiting {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"❌ Failed to post {post_type} message scheduled for {time_str}: {e}")
        if admin_id:
            await bot_client.send_message(admin_id, f"⚠️ Failed to post {post_type} message scheduled for {time_str}: {e}")

def update_job_schedule():
    scheduler.remove_all_jobs()
    try:
        for idx, item in enumerate(schedule_data["morning_msgs"]):
            time_str = item["time"]
            m_hour, m_min = map(int, time_str.split(":"))
            scheduler.add_job(
                send_single_scheduled_post,
                'cron',
                hour=m_hour,
                minute=m_min,
                args=[item["msg"], 'Morning', time_str],
                id=f'morning_job_{idx}'
            )

        for idx, item in enumerate(schedule_data["evening_msgs"]):
            time_str = item["time"]
            e_hour, e_min = map(int, time_str.split(":"))
            scheduler.add_job(
                send_single_scheduled_post,
                'cron',
                hour=e_hour,
                minute=e_min,
                args=[item["msg"], 'Evening', time_str],
                id=f'evening_job_{idx}'
            )

        print(f"📅 Schedule updated: {len(schedule_data['morning_msgs'])} Morning posts & {len(schedule_data['evening_msgs'])} Evening posts scheduled.")
    except Exception as e:
        print(f"❌ Error updating schedule: {e}")

@user_client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def auto_repost_handler(event):
    if event.photo or event.media:
        try:
            photo_path = await event.download_media()
            raw_caption = event.message.message or ""
            caption_text = raw_caption.lower()
            ocr_text = ""

            try:
                img = Image.open(photo_path)
                ocr_text = pytesseract.image_to_string(img).lower()
            except Exception:
                pass

            combined_text = caption_text + " " + ocr_text
            keywords = [
                "congrat", "congrats", "congratulation", "congratulations", "🎉", "🥳",
                "credit", "more winnings", "successful", "withdrawal"
            ]

            if any(kw in combined_text for kw in keywords):
                clean_caption = remove_links(raw_caption)
                await bot_client.send_file(CHANNEL_TARGET, photo_path, caption=clean_caption)

            if os.path.exists(photo_path):
                os.remove(photo_path)
        except Exception as e:
            if admin_id:
                await bot_client.send_message(admin_id, f"⚠️ Auto-repost error: {e}")

def get_admin_menu():
    return [
        [Button.inline(f"📊 Total Users: {len(registered_users)}", b"count_users")],
        [Button.inline("📹 Upload/Update Tutorial Video", b"set_tutorial_video")],
        [Button.inline("🌅 Add Morning Post", b"set_morning_post"), Button.inline("🌆 Add Evening Post", b"set_evening_post")],
        [Button.inline("🗑 Clear Morning Posts", b"clear_morning"), Button.inline("🗑 Clear Evening Posts", b"clear_evening")],
        [Button.inline("📋 View Current Schedule", b"view_schedule")]
    ]

def get_main_menu(show_support=False):
    menu = [
        [Button.inline("📜 Show Menu", b"show_menu")],
        [Button.inline("📤 Send Withdrawal Screenshot", b"send_withdrawal")],
        [Button.inline("📹 Watch Video Tutorial", b"send_video")]
    ]
    if show_support:
        menu.append([Button.inline("💬 Chat with Live Customer Support", b"live_support")])
    return menu

async def deliver_video_tutorial(target_id):
    global tutorial_video_msg
    show_support = user_msg_count.get(target_id, 0) >= 5
    if tutorial_video_msg and tutorial_video_msg.media:
        caption_text = tutorial_video_msg.message or "📹 **Income Pro Video Tutorial**\nWatch this carefully before proceeding."
        await bot_client.send_file(target_id, tutorial_video_msg.media, caption=caption_text, buttons=get_main_menu(show_support))
    else:
        await bot_client.send_message(
            target_id,
            f"📹 **Income Pro Video Tutorial:**\n\n"
            f"Please click the link below to watch the video tutorial on our official portal:\n"
            f"{WEBSITE_LINK}",
            buttons=get_main_menu(show_support)
        )

@bot_client.on(events.NewMessage)
async def direct_message_handler(event):
    if not event.is_private:
        return

    sender_id = event.sender_id
    text = (event.raw_text or "").strip().lower()
    registered_users.add(sender_id)

    user_msg_count[sender_id] = user_msg_count.get(sender_id, 0) + 1
    show_support = user_msg_count[sender_id] >= 5

    global admin_id, tutorial_video_msg
    if text == "/setadmin":
        admin_id = sender_id
        await event.respond("✅ You are now set as the Owner/Admin of this bot.")
        return

    if sender_id == admin_id and text == "/admin1211":
        await event.respond(f"👑 **Admin Panel**\n👥 Total Users: {len(registered_users)}\nConfigure channel posts and bot parameters below:", buttons=get_admin_menu())
        return

    if sender_id == admin_id:
        state = user_states.get(sender_id)
        if state == "WAITING_TUTORIAL_VIDEO":
            if event.media:
                tutorial_video_msg = event.message
                user_states[sender_id] = None
                await event.respond("✅ **Tutorial video saved successfully!** Users will now receive this video instantly when requested.")
            else:
                await event.respond("❌ Please send or forward a message with a video.")
            return

        elif state == "WAITING_MORNING_POST":
            pending_posts[sender_id] = event.message
            user_states[sender_id] = "WAITING_MORNING_TIME"
            await event.respond("⏰ Enter the EXACT time for this Morning post in 24-hour format (e.g. 08:00, 08:15, or 09:30):")
            return

        elif state == "WAITING_MORNING_TIME":
            if re.match(r'^\d{1,2}:\d{2}$', text):
                post_msg = pending_posts.pop(sender_id, None)
                if post_msg:
                    schedule_data["morning_msgs"].append({"msg": post_msg, "time": text})
                    update_job_schedule()
                    user_states[sender_id] = None
                    await event.respond(f"✅ Morning post #{len(schedule_data['morning_msgs'])} scheduled for **{text}**! Tap /admin1211 to add another.")
            else:
                await event.respond("❌ Invalid format! Please enter time as HH:MM (e.g. 08:30).")
            return

        elif state == "WAITING_EVENING_POST":
            pending_posts[sender_id] = event.message
            user_states[sender_id] = "WAITING_EVENING_TIME"
            await event.respond("⏰ Enter the EXACT time for this Evening post in 24-hour format (e.g. 18:00, 19:45, or 21:00):")
            return

        elif state == "WAITING_EVENING_TIME":
            if re.match(r'^\d{1,2}:\d{2}$', text):
                post_msg = pending_posts.pop(sender_id, None)
                if post_msg:
                    schedule_data["evening_msgs"].append({"msg": post_msg, "time": text})
                    update_job_schedule()
                    user_states[sender_id] = None
                    await event.respond(f"✅ Evening post #{len(schedule_data['evening_msgs'])} scheduled for **{text}**! Tap /admin1211 to add another.")
            else:
                await event.respond("❌ Invalid format! Please enter time as HH:MM (e.g. 20:15).")
            return

    state = user_states.get(sender_id)
    if state == "ASKED_TUTORIAL":
        if text in ["no", "n", "i have not", "haven't", "haven't watched", "no i have not"]:
            user_states[sender_id] = None
            await deliver_video_tutorial(sender_id)
            return
        elif text in ["yes", "y", "i have", "yes i have"]:
            user_states[sender_id] = None
            await event.respond("Great! If you have made your payment, send your payment screenshot here.", buttons=get_main_menu(show_support))
            return

    if event.photo:
        user_states[sender_id] = "RECEIPT_PROCESSING"
        await event.respond("Hold on...")
        await asyncio.sleep(120)

        photo_path = await event.download_media()
        ocr_text = ""
        try:
            img = Image.open(photo_path)
            ocr_text = pytesseract.image_to_string(img).lower()
            if os.path.exists(photo_path):
                os.remove(photo_path)
        except Exception:
            if os.path.exists(photo_path):
                os.remove(photo_path)

        if "payout key" in ocr_text:
            await event.respond("Hold on let me work on it...")
            await asyncio.sleep(600)
            await event.respond("Couldn't find your payment. Please you have to remake the payment.", buttons=get_main_menu(show_support))
        else:
            await event.respond(
                "The reason your payment failed is that you did not put any narrative while making your payment. "
                "How will Income Pro know the reason you are making this payment for?\n\n"
                "If you watch the video tutorial, I put my narrative payout key while making the payment. "
                "What you are going to do now: you have to remake your payment and put your narrative on it.",
                buttons=get_main_menu(show_support)
            )
        user_states[sender_id] = None
        return

    if any(k in text for k in ["registered", "register", "video tutorial", "tutorial", "video"]):
        user_states[sender_id] = "ASKED_TUTORIAL"
        buttons = [
            [Button.inline("Yes, I watched it", b"tutorial_yes"), Button.inline("No, send it", b"tutorial_no")]
        ]
        await event.respond("Have you registered and watched the video tutorial?", buttons=buttons)
        return

    if any(k in text for k in ["update", "need update"]):
        await event.respond(
            f"📢 **Latest Update Information:**\n\n"
            f"For all active platform updates, daily tasks, and guidelines, please check our official portal:\n"
            f"{WEBSITE_LINK}",
            buttons=get_main_menu(show_support)
        )
        return

    if any(k in text for k in ["made payment", "make my payment", "i paid", "payment i made"]):
        user_states[sender_id] = "WAITING_RECEIPT"
        await event.respond(
            "💳 **Payment Verification:**\n\n"
            "Please send your payment screenshot here now for processing.",
            buttons=get_main_menu(show_support)
        )
        return

    if any(k in text for k in ["not working", "problem", "issue"]):
        await event.respond(
            f"🛠 **Technical Support:**\n\n"
            f"If you are facing any issues, kindly visit our official website for full instructions and guides:\n"
            f"{WEBSITE_LINK}\n\n"
            f"If it is related to a payment, please send your payment screenshot directly here.",
            buttons=get_main_menu(show_support)
        )
        return

    if "borrow" in text:
        await event.respond(
            "⚠️ **Borrow Inquiry:**\n\n"
            "We do not offer loan or borrow options. All withdrawals and earnings require active participation on our platform.",
            buttons=get_main_menu(show_support)
        )
        return

    if any(k in text for k in ["is it real", "is it legit", "legit"]):
        await event.respond(
            f"✅ **100% Verified & Authentic Platform:**\n\n"
            f"Income Pro is reliable and secure. You can visit our platform here to learn more:\n"
            f"{WEBSITE_LINK}",
            buttons=get_main_menu(show_support)
        )
        return

    if text in ["/start", "hello", "hi", "hey"]:
        await event.respond("How can I help you?", buttons=get_main_menu(show_support))
        return

    await event.respond(
        f"Hello! Welcome to Income Pro. Visit our platform for guidance: {WEBSITE_LINK}\n\n"
        f"If you are asking about an update, type 'update'. If you made a payment, send your payment screenshot here.",
        buttons=get_main_menu(show_support)
    )

@bot_client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data
    user_id = event.sender_id
    show_support = user_msg_count.get(user_id, 0) >= 5

    if data == b"send_withdrawal":
        user_states[user_id] = "WAITING_RECEIPT"
        await event.respond("Please send your payment screenshot now.")
        return
    elif data == b"show_menu":
        await event.respond("How can I help you?", buttons=get_main_menu(show_support))
        return
    elif data == b"send_video" or data == b"tutorial_no":
        user_states[user_id] = None
        await deliver_video_tutorial(user_id)
        return
    elif data == b"tutorial_yes":
        user_states[user_id] = None
        await event.respond("Great! If you have made your payment, send your payment screenshot here.", buttons=get_main_menu(show_support))
        return
    elif data == b"live_support":
        if admin_id:
            try:
                admin_entity = await bot_client.get_entity(admin_id)
                admin_username = admin_entity.username
                if admin_username:
                    await event.respond(f"🎧 **Live Support Agent:**\n\nYou can chat directly with our official support here: @{admin_username}")
                else:
                    await event.respond("🎧 **Live Support Agent:**\n\nPlease send your inquiry here directly, and our support admin will attend to you.")
            except Exception:
                await event.respond("🎧 **Live Support Agent:**\n\nPlease send your inquiry here directly, and our support admin will attend to you.")
        else:
            await event.respond("🎧 **Live Support Agent:**\n\nPlease send your inquiry here directly, and our support admin will attend to you.")
        return

    if user_id == admin_id:
        if data == b"count_users":
            await event.respond(f"👥 **Total Active Bot Users:** {len(registered_users)}")
            return
        elif data == b"set_tutorial_video":
            user_states[user_id] = "WAITING_TUTORIAL_VIDEO"
            await event.respond("📹 Send or forward the video tutorial to this chat now.")
            return
        elif data == b"set_morning_post":
            user_states[user_id] = "WAITING_MORNING_POST"
            await event.respond("Send/forward the message or photo for your MORNING slot:")
        elif data == b"set_evening_post":
            user_states[user_id] = "WAITING_EVENING_POST"
            await event.respond("Send/forward the message or photo for your EVENING slot:")
        elif data == b"clear_morning":
            schedule_data["morning_msgs"] = []
            update_job_schedule()
            await event.respond("🗑 All morning messages cleared.")
        elif data == b"clear_evening":
            schedule_data["evening_msgs"] = []
            update_job_schedule()
            await event.respond("🗑 All evening messages cleared.")
        elif data == b"view_schedule":
            morning_list = "\n".join([f"  • Post #{i+1} ⏰ {item['time']}" for i, item in enumerate(schedule_data["morning_msgs"])]) or "  None"
            evening_list = "\n".join([f"  • Post #{i+1} ⏰ {item['time']}" for i, item in enumerate(schedule_data["evening_msgs"])]) or "  None"
            
            await event.respond(
                f"📅 **Scheduled Posts:**\n\n"
                f"🌅 **Morning Slot ({len(schedule_data['morning_msgs'])} posts):**\n{morning_list}\n\n"
                f"🌆 **Evening Slot ({len(schedule_data['evening_msgs'])} posts):**\n{evening_list}"
            )

async def main():
    if USER_SESSION_STRING:
        await user_client.connect()
        if not await user_client.is_user_authorized():
            print("⚠️ User session string provided is not authorized or expired.")
    else:
        print("⚠️ USER_SESSION_STRING is empty. User client disabled.")

    await bot_client.start(bot_token=BOT_TOKEN)
    update_job_schedule()
    scheduler.start()
    print("IncomePro Script Active!")
    
    if USER_SESSION_STRING:
        await asyncio.gather(
            user_client.run_until_disconnected(),
            bot_client.run_until_disconnected()
        )
    else:
        await bot_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
