# TODO: Move each command to separate module.
# TODO: Change q! option on other format (maybe button)
# TODO: Add logic on incomes
# TODO: Add logic on aims
# TODO: Add logic on affordable spending
# TODO: Check safety of current creds usage (can we check user data in spreadsheet?)
import asyncio
import json
import os
import re
import zoneinfo
from collections import defaultdict
from datetime import datetime

import dotenv
from telethon.sync import Button, TelegramClient, events
from telethon.tl.custom import Conversation
from telethon.tl.types import User

from spreadsheet import Spreadsheet

dotenv.load_dotenv()

api_id = eval(os.environ["API_ID"])
api_hash = os.environ["API_HASH"]
bot_token = os.environ["BOT_TOKEN"]
bot = TelegramClient("getbudbot", api_id, api_hash).start(bot_token=bot_token)

with open("google_api_credentials.json") as f:
    GOOGLE_API_CREDENTIALS = json.load(f)

with open("spreadsheets_db.json") as f:
    d = json.load(f)
    temp_d = {}
    for k in d.keys():
        temp_d[int(k)] = d[k]
    SHEETS = defaultdict(list, temp_d)


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


async def yes(conv: Conversation):
    sent_yes = False
    while True:
        response = await conv.get_response()
        if response.text in ["no", "n", "N", "Not"]:
            break
        elif response.text in ["yes", "y", "Y", "Yes"]:
            sent_yes = True
            break
        else:
            await conv.send_message("Please, enter yes or no.")
            continue
    return sent_yes


# TODO: Rebuild as decorator.
async def dont_know(conv: Conversation, sender: User) -> bool:
    if sender.id not in SHEETS:
        await conv.send_message(
            "I don't know you, sorry 👀. \nLet's get to know each other by /start command! ☺️"
        )
        return True
    return False


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    # Start conversation.
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        if str(sender.id) in SHEETS:
            await conv.send_message(
                f"I'm already known you, {sender.first_name} {sender.last_name}! 👻"
            )
            return

        # Conversation welcome message.
        template_spreadsheet_id = os.environ["TEMPLATE_URL"].split("/")[5]
        await conv.send_message(
            "**Welcome to the budget bot!**\n\n"
            "I will help you to track your budget 😎💵\n\n\n"
            "Firstly, you should take a few steps❗️\n\n"
            f"1️⃣ Make a copy of [this file]({os.environ['TEMPLATE_URL']}) "
            "to your [Google Drive](https://drive.google.com/drive/)\n\n"
            "2️⃣ Share your copy with this Google service email (add as Editor):\n"
            f"{GOOGLE_API_CREDENTIALS['client_email']}\n"
            "It's secure, because it can't be used by other users.\n\n"
            "3️⃣ Send me a copy of your Google Sheet IP to me.\n"
            "It is after `/spreadsheets/d/` between slashes in url of your sheet.\n\n"
            f"For example, from [url]({os.environ['TEMPLATE_URL']}):\n"
            "--------------------------------\n"
            f"`{template_spreadsheet_id}`\n"
            "--------------------------------\n"
        )

        counter = 0
        while True:
            response = await responser(conv)
            if not response:
                return

            if response.text == "q!":
                await conv.send_message("See you!")
                return

            if response.text == template_spreadsheet_id or response.text == (
                "`" + template_spreadsheet_id + "`"
            ):
                await conv.send_message("Please, don't use template id! Try again :)")
                continue

            try:
                Spreadsheet(spreadsheet_id=response.text, sheet_name="Timeline")
            except Exception:
                counter += 1
                await conv.send_message("Oops! I can't come in :( \nPlease try again!")
                if counter > 2:
                    await conv.send_message("You can write 'q!', if you want to quit")

            SHEETS[sender.id].append(response.text)
            with open("SHEETS.json", "w") as f:
                json.dump(SHEETS, f)

            await conv.send_message(
                "Great, I remembered you! \nYou can continue with adding /timezone info."
            )
            break


@bot.on(events.NewMessage(pattern="/timezone"))
async def timezone(event):
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        if await dont_know(conv, sender):
            return

        sheet = Spreadsheet(
            spreadsheet_id=SHEETS[sender.id][0], sheet_name="Timezone"
        ).get_spreadsheet_as_df()
        if not sheet.empty:
            cur_tz = sheet.loc[0, "Timezone"]
            await conv.send_message(
                f"Your current timezone name: `{cur_tz}`\n"
                f"And your current time is: {datetime.now(tz=zoneinfo.ZoneInfo(cur_tz)).strftime('%H:%M')}\n\n"
                "Do you want to change your timezone?\n[yes/no]"
            )
            if not await yes(conv):
                await conv.send_message("Good bye! 👋")
                return

        await conv.send_message(
            "**Time zone information** 🌍\n\n"
            "Enter your current time in format HH:MM.\n"
            "Example: 21:12. \n"
            "I need it for the correct data recordings ✏️\n"
            "If you want to quit, enter: q!"
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

            if not await yes(conv):
                continue

            for spreadsheet_id in SHEETS[sender.id]:
                sheet = Spreadsheet(
                    spreadsheet_id=spreadsheet_id, sheet_name="Timezone"
                )
                sheet_df = sheet.get_spreadsheet_as_df()
                sheet_df.loc[0, "Timezone"] = user_timezones[0]
                sheet.push_df_to_spreadsheet(sheet_df)
            await conv.send_message("Yay, now I know your timezone! 🕑")
            break


@bot.on(events.NewMessage(pattern="/spreadsheets"))
async def spreadsheets(event):
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        if await dont_know(conv, sender):
            return

        # TODO: кнопки: добавить, удалить или выйти
        keyboard = [
            [Button.inline("First option", b"1"), Button.inline("Second option", b"2")],
            [Button.inline("Third option", b"3"), Button.inline("Fourth option", b"4")],
            [Button.inline("Fifth option", b"5")],
        ]
        m = "Here are your spreadsheets:\n"
        for spreadsheet_id in SHEETS[sender.id]:
            m += f"[{spreadsheet_id}](https://docs.google.com/spreadsheets/d/{spreadsheet_id})\n"
        await conv.send_message(m, buttons=keyboard)

        # TODO: перед добавлением показать небольшую инструкции (ссылку, например)
        # TODO: save


@bot.on(events.NewMessage(pattern="/categories"))
async def categories(event):
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        if await dont_know(conv, sender):
            return
    # TODO: show categories
    # TODO: предложить добавить, удалить или выйти
    # TODO: если удалить или добавить, то вводим просто название. Если при удалении не нашли, то пишем wring category!
    pass


@bot.on(events.NewMessage(pattern="/add"))
async def add_payment(event):
    sender = await event.get_sender()
    async with bot.conversation(sender) as conv:
        if await dont_know(conv, sender):
            return
    # TODO: Должна быть проверка на наличие timezone, хотя бы одной категории
    await event.reply("Are you sure you want to add a payment?")


try:
    print("(Press Ctrl+C to stop this)")
    bot.run_until_disconnected()
finally:
    bot.disconnect()
