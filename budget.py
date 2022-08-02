import asyncio
import os
import json
import re
import zoneinfo
from datetime import datetime

import dotenv
from telethon.sync import TelegramClient, events
from telethon.tl.custom import Conversation

dotenv.load_dotenv()

api_id = eval(os.environ["API_ID"])
api_hash = os.environ["API_HASH"]
bot_token = os.environ["BOT_TOKEN"]
bot = TelegramClient("getbudbot", api_id, api_hash).start(bot_token=bot_token)

with open("google_api_credentials.json") as f:
    GOOGLE_API_CREDENTIALS = json.load(f)


async def responser(conv: Conversation):
    try:
        # Wait for the response from user.
        response = await conv.get_response()
        return response
    except asyncio.exceptions.TimeoutError:
        await conv.send_message(
            "Your response time has expired 👀. You can re-enter your command at any time :)"
        )
        return False


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    # TODO: Если user вызвал опять команду, то сказать шо уже знакомы
    # Start conversation.
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        # Conversation welcome message.
        await conv.send_message(
            "**Welcome to the budget bot!**\n\n"
            "I will help you to track your budget 😎💵\n\n\n"
            "Firstly, you should take a few steps❗️\n\n"
            f"1️⃣ Make a copy of [this file]({os.environ['TEMPLATE_URL']}) "
            "to your [Google Drive](https://drive.google.com/drive/)\n\n"
            "2️⃣ Share your copy with this Google service email (add as Editor):\n"
            f"{GOOGLE_API_CREDENTIALS['client_email']}\n"
            "It's secure, because it can't be used by other users.\n\n"
            "3️⃣ Send me your copy Google Sheet IP to me "
            "(it is after /spreadsheets/d/ between slashes in url of your sheet)."
        )
        response = await responser(conv)
        if not response:
            return


@bot.on(events.NewMessage(pattern="/timezone"))
async def timezone(event):
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        # TODO: Может быть должна быть отдельная команда
        # TODO: Разобрать на функции
        await conv.send_message(
            "🕖 Enter your current time in format HH:MM.\n"
            "Example: 21:12. \n"
            "I need it for the correct data recordings ✏️\n"
            "If you want quit, enter: q!"
        )
        while True:
            response = await responser(conv)
            if not response:
                break

            # Quit.
            if response.text == "q!":
                await conv.send_message("Good bye! 👋")
                break

            # Check correct time format.
            if not re.match(
                r"[0-1][0-9]:[0-5][0-9]$|[2][0-4]:[0-5][0-9]$", response.text
            ):
                await conv.send_message("❌ Wrong time format! Please, try again.")
                continue

            # Find timezone.
            t = datetime.now()
            user_timezones = []
            for tz in zoneinfo.available_timezones():
                if response.text == t.astimezone(zoneinfo.ZoneInfo(tz)).strftime(
                    "%H:%M"
                ):
                    user_timezones.append(tz)

            # Suggest to try again if not found.
            if len(user_timezones) == 0:
                await conv.send_message(
                    "I didn't find any timezone information 😞. Please, try again 🥹."
                )
                continue

            # Make sure the timezone is correct.
            s = "**Here are your available timezone names:**\n\n"
            for tz in user_timezones:
                s += tz + "\n"
            s += "\nIs it correct?\n[yes/no]"
            await conv.send_message(s)

            sent_yes = False
            while True:
                response = await conv.get_response()
                if response.text in ["no", "n", "N", "Not"]:
                    await conv.send_message("Well, let's try again! 🔄")
                    break
                elif response.text in ["yes", "y", "Y", "Yes"]:
                    sent_yes = True
                    break
                else:
                    await conv.send_message("Please, enter yes or no.")
                    continue
            if not sent_yes:
                continue
            
            break

    raise events.StopPropagation


@bot.on(events.NewMessage(pattern="/credentials"))
async def set_google_creds(event):
    # TODO: показать cred names
    # TODO: кнопки: добавить, удалить или выйти
    # TODO: перед добавлением показать небольшую инструкции (ссылку, например)
    # TODO: при добавлении ввести имя, а потом все остальные переменные
    # TODO: после добавления, удалить сообщение с кредами, чтобы нескомпрометировать челика
    # TODO: save credentials to DB with encryption
    pass


@bot.on(events.NewMessage(pattern="/categories"))
async def categories(event):
    # TODO: show categories
    # TODO: предложить добавить, удалить или выйти
    # TODO: если удалить или добавить, то вводим просто название. Если при удалении не нашли, то пишем wring category!
    pass


@bot.on(events.NewMessage(pattern="/add"))
async def add_payment(event):
    # TODO: Должна быть проверка на наличие timezone, google creds, хотя бы одной категории
    await event.reply("Are you sure you want to add a payment?")


try:
    print("(Press Ctrl+C to stop this)")
    bot.run_until_disconnected()
finally:
    bot.disconnect()
