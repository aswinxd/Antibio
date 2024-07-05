import re
import asyncio
from collections import deque
from telethon import TelegramClient, events, functions
from telethon.tl import types
from telethon.tl.types import PeerUser
from db import add_chatid, check_userid, add_userid, remove_userid
#import logging
import time


#logging.basicConfig(level=logging.INFO)
#logger = logging.getLogger(__name__)

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
            await client.delete_messages(chat_id, [event.id])
            await client.kick_participant(chat_id, user_id)
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
        "Welcome! This is AntiBioLink. Here are some commands you can use:\n"
        "Features:\n"
        "1. Automatically checks new users' bios for links and kicks them if a link is found.\n"
        "4. Sends notifications to users when they are kicked due to having links in their bio.\n"
        "5. Add bot to your group as admin with ban permission\n"
    )
    buttons = [
        [types.KeyboardButtonUrl("Support", "https://CodecArchive.t.me"), types.KeyboardButtonUrl("Updates", "https://Codecbots.t.me")]
    ]
    await event.respond(instructions, buttons=buttons)

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
    bot_token = '6415620700:AAEFMGPt3ntPt8Dai5Oa7U5TVvsJtk57HRI'

    queue = asyncio.Queue()
    user_cache = {} 
    cache_duration = 500 

    async with TelegramClient('bot_session', api_id, api_hash) as client:
        await client.start(bot_token=bot_token)

        @client.on(events.NewMessage)
        async def handle_new_message(event):
            await queue.put(event)

        @client.on(events.NewMessage(pattern='/start'))
        async def handle_start(event):
            await handle_start_command(event)

        num_workers = 700
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
