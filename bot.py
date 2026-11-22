import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

BOT_TOKEN = "9183522235:AAEXlKHVmUNLPEIQORIBlmriITMFY4qHdew"

# Расписание конца уроков по МСК (часы, минуты, номер урока)
BELL_SCHEDULE = [
    (9, 10, 1),   # 1 урок: 8:30 - 9:10
    (10, 0, 2),   # 2 урок: 9:20 - 10:00
    (10, 50, 3),  # 3 урок: 10:10 - 10:50
    (11, 50, 4),  # 4 урок: 11:10 - 11:50
    (12, 50, 5),  # 5 урок: 12:10 - 12:50
    (13, 40, 6),  # 6 урок: 13:00 - 13:40
    (14, 30, 7),  # 7 урок: 13:50 - 14:30
]

SCHOOL_DAYS = "mon-fri"
TIMEZONE = "Europe/Moscow"
SUBSCRIBERS_FILE = "subscribers.json"


def load_subscribers() -> set:
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_subscribers(subs: set):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(subs), f)


subscribers = load_subscribers()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    subscribers.add(message.chat.id)
    save_subscribers(subscribers)
    await message.answer(
        "🔔 Уведомления о конце уроков **включены** (время МСК)!\n"
        "Отключить: /stop\n"
        "Посмотреть расписание звонков: /schedule",
        parse_mode="Markdown"
    )


@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    subscribers.discard(message.chat.id)
    save_subscribers(subscribers)
    await message.answer("🔕 Уведомления **отключены**.", parse_mode="Markdown")


@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    lines = ["📅 **Расписание звонков (МСК):**"]
    for hour, minute, lesson_num in BELL_SCHEDULE:
        lines.append(f"• {lesson_num}-й урок заканчивается в **{hour:02d}:{minute:02d}**")
    await message.answer("\n".join(lines), parse_mode="Markdown")


async def send_bell_notification(lesson_num: int):
    if not subscribers:
        return
    text = f"🔔 **Звонок!** {lesson_num}-й урок закончился! Перемена."
    for chat_id in list(subscribers):
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка отправки в {chat_id}: {e}")


async def main():
    logging.basicConfig(level=logging.INFO)
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    for hour, minute, lesson_num in BELL_SCHEDULE:
        scheduler.add_job(
            send_bell_notification,
            trigger=CronTrigger(day_of_week=SCHOOL_DAYS, hour=hour, minute=minute),
            args=[lesson_num]
        )
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
