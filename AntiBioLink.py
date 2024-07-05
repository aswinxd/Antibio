import re
import asyncio
from collections import deque
from telethon import TelegramClient, events, functions
from telethon.tl import types
from telethon.tl.types import PeerUser
from telethon.errors import MessageDeleteForbiddenError, UserAdminInvalidError
from telethon.tl.custom import Button
from db import add_chatid, check_userid, add_userid, remove_userid
import time

privacy_responses = {
    "info_collect": "We collect the following user data:\n- First Name\n- Last Name\n- Username\n- User ID\n- Messages sent by users\n- User bio if it is visible to the public\n These are public Telegram details that everyone can see.",
    "why_collect": "The collected data is used solely for improving your experience with the bot and for processing the bot stats and to avoid spammers.",
    "what_we_do": "We use the data to personalize your experience and provide better services.",
    "what_we_do_not_do": "We do not share your data with any third parties.",
    "right_to_process": "You have the right to access, correct, or delete your data. [Contact us](t.me/drxew) for any privacy-related inquiries."
}

def check_string_regex(s):
    patterns_to_check = [r"@", r"https://", r"http://", r"t\.me//", r"t\.me"]
    for pattern in patterns_to_check:
        if re.search(pattern, s):
            return True
    return False

async def check_user_bio(client, event, user_cache, cache_duration):
    chat_id = event.chat_id
    data = await event.get_sender()
    user_id = data.id

    if user_id is None:
        return

    current_time = time.time()
    if user_id in user_cache:
        last_checked_time = user_cache[user_id]
        if current_time - last_checked_time < cache_duration:
            return

    try:
        result = await client(functions.users.GetFullUserRequest(id=user_id))
        user_bio = result.full_user.about or ''
        if check_string_regex(user_bio):
            try:
                await client.delete_messages(chat_id, [event.id])
            except MessageDeleteForbiddenError:
                pass
            try:
                await client.kick_participant(chat_id, user_id)
            except UserAdminInvalidError:
                return

            msg1 = f"You are kicked out from the group because your bio has a link"
            msg2 = f"User {user_id} was kicked out from the group because their bio had a link"
            try:
                await client.send_message(PeerUser(user_id), msg1)
            except:
                await client.send_message(chat_id, msg2)

        user_cache[user_id] = current_time

    except Exception as e:
        return

async def handle_start_command(event):
    instructions = (
        "Welcome! This is AntiBioLink.\n"
        "• Automatically checks new users' bios for links and kicks them if a link is found.\n"
        "• Sends notifications to users when they are kicked due to having links in their bio.\n"
        "• Use the /privacy command to view the privacy policy, and interact with your data.\n"
        "• Add bot to your group as admin with ban permission\n"
    )
    buttons = [
        [Button.url("Privacy policy", "https://t.me/CodecBots")],
        [Button.url("Updates", "https://t.me/CodecArchive")]
    ]
    await event.respond(instructions, buttons=buttons)

async def privacy_command(event):
    privacy_button = [
        [Button.inline("Privacy Policy", b"privacy_policy")]
    ]
    await event.respond("Select one of the below options for more information about how the bot handles your privacy.", buttons=privacy_button)

async def handle_callback_query(event):
    data = event.data.decode("utf-8")
    if data == "privacy_policy":
        buttons = [
            [Button.inline("What Information We Collect", b"info_collect")],
            [Button.inline("Why We Collect", b"why_collect")],
            [Button.inline("What We Do", b"what_we_do")],
            [Button.inline("What We Do Not Do", b"what_we_do_not_do")],
            [Button.inline("Right to Process", b"right_to_process")]
        ]
        await event.edit("Our contact details\nName: AntiBioLinkBot \nTelegram: https://t.me/CodecArchive\nThe bot has been made to protect and preserve privacy as best as possible.\nOur privacy policy may change from time to time. If we make any material changes to our policies, we will place a prominent notice on https://t.me/CodecBots.", buttons=buttons)
    elif data in privacy_responses:
        back_button = [
            [Button.inline("Back", b"privacy_policy")]
        ]
        await event.edit(privacy_responses[data], buttons=back_button)

async def worker(name, client, queue, user_cache, cache_duration):
    while True:
        event_batch = []
        for _ in range(100):  
            event = await queue.get()
            event_batch.append(event)
            queue.task_done()
            if queue.empty():
                break
        await asyncio.gather(*[check_user_bio(client, event, user_cache, cache_duration) for event in event_batch])

async def main():
    api_id = '12799559'
    api_hash = '077254e69d93d08357f25bb5f4504580'
    bot_token = '6415620700:AAHanvcDvYEIzfUd1E-V4BPuYcSrzq0vUQg'

    queue = asyncio.Queue()
    user_cache = {} 
    cache_duration = 500 

    async with TelegramClient('bot_session', api_id, api_hash) as client:
        await client.start(bot_token=bot_token)

        @client.on(events.NewMessage(pattern='/start'))
        async def handle_start(event):
            await handle_start_command(event)

        @client.on(events.NewMessage(pattern='/privacy'))
        async def handle_privacy(event):
            await privacy_command(event)

        @client.on(events.CallbackQuery)
        async def callback_query_handler(event):
            await handle_callback_query(event)

        @client.on(events.NewMessage)
        async def handle_new_message(event):
            await queue.put(event)

        num_workers = 1800
        tasks = []
        for i in range(num_workers):
            task = asyncio.create_task(worker(f'worker-{i}', client, queue, user_cache, cache_duration))
            tasks.append(task)

        await client.run_until_disconnected()
        await queue.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
