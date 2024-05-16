import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from telethon.sync import TelegramClient, events, functions
from db import add_chatid, check_userid, add_userid,remove_userid


def check_string_regex(s):
    patterns_to_check = [r"@", r"https://", r"http://", r"t\.me//", r"t\.me"]
    for pattern in patterns_to_check:
        if re.search(pattern, s):
            return True
    return False

async def check_user_bio(client, event):
    chat_id = event.chat_id
    '''chat = await client.get_entity(chat_id)
    group_name = chat.title
    try:
        data2 = await client.get_participants(chat)
    except:
        pass
    try:
        member_count = data2.total
    except:
        member_count = 0'''
    '''if chat_id:
        add_chatid(chat_id)'''

    data = await event.get_sender()
    user_id = data.id
    if user_id is not None:
         try:
            result = await client(functions.users.GetFullUserRequest(
                id=user_id
            ))
            data_info = result.to_dict()
            user_bio = data_info.get('full_user', {}).get('about', '')
            data_meta = check_string_regex(user_bio)
        except Exception as e:
            print(f"Error fetching user data: {e}")
            data_meta = False
    else:
        print("User ID is None")
        data_meta = False

    if data_meta:
        await client.delete_messages(chat_id, [event.id])
        await client.kick_participant(chat_id, user_id)
        user_peer = await client.get_entity(user_id)
        msg1 = f"You are kicked out from the {chat_id} because your bio has a link"
        msg2 = f"{chat_id} is kicked out from the group because user had link in Bio"
        try:
            await client.send_message(user_id,msg1)
        except:
            data_r = await client.send_message(chat_id,msg2)
            await client.delete_messages(chat_id, [data_r.id])

async def handle_start_command(client, event):
    instructions = (
        "Welcome! I am your bot. Here are some commands you can use:\n"
        "/add - Add a user ID to the whitelist\n"
        "/removeuser - Remove a user ID from the whitelist"
    )
    await event.respond(instructions)

async def main():
    api_id = 
    api_hash = ""
    async with TelegramClient('bot_session', api_id, api_hash) as client:
        # Start threads for handling different events concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = [
                asyncio.create_task(client.start(bot_token="")),
                asyncio.create_task(client.run_until_disconnected()),
            ]

            # Register event handlers
            client.add_event_handler(lambda event: check_user_bio(client, event), events.NewMessage)
            #client.add_event_handler(lambda event: handle_add_request(client, event), events.NewMessage(pattern='/add'))
            #client.add_event_handler(lambda event: handle_remove_request(client, event), events.NewMessage(pattern='/removeuser'))
            client.add_event_handler(lambda event: handle_start_command(client, event), events.NewMessage(pattern='/start'))
            #client.add_event_handler(lambda event: handle_stat_command(client, event), events.NewMessage(pattern='/stats'))
            #client.add_event_handler(lambda event: handle_ping_command(client, event), events.NewMessage(pattern='/ping'))

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())