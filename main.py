# filename: anti_bullying_bot.py
import asyncio
import logging
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

import aiosqlite
from gpt4all import GPT4All
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# -----------------------
# LOAD ENV VARIABLES
# -----------------------
load_dotenv()  # загружаем .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") 

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не найден. Добавьте его в .env файл.")

# -----------------------
# DB CONFIG
# -----------------------
MODEL_NAME = "Meta-Llama-3-8B-Instruct.Q4_0.gguf"  # или путь к файлу .gguf
DB_PATH = "anti_bullying_logs.db"

# Crisis contacts (показываем в сообщении; для Словакии):
CRISIS_CONTACTS = (
    "Если вы в Словакии и у вас мысли о причинении вреда себе, пожалуйста, "
    "свяжитесь с экстренной помощью: 112.\n"
    "Горячая линия для молодежи (IPčko): 0800 500 333.\n"
    "Linka dôvery Nezábudka (24/7): 0800 800 566.\n"
    "Также можете найти международные службы на Befrienders Worldwide."
)

# Predefined categories
CATEGORIES = [
    ("bullying_school", "Буллинг в школе"),
    ("bullying_online", "Кибербуллинг / в сети"),
    ("want_die", "Я хочу умереть"),
    ("other", "Другая проблема"),
]

# -----------------------
# Logging
# -----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------
# MODELS / DB init
# -----------------------
# Create gpt4all model instance (blocking load can be slow, so we create lazily)
gpt_model = None


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anon_id TEXT,
                category TEXT,
                text TEXT,
                created_at TEXT
            )"""
        )
        await db.commit()


def make_buttons():
    kb = [
        [InlineKeyboardButton(label, callback_data=key)] for key, label in CATEGORIES
    ]
    return InlineKeyboardMarkup(kb)


# -----------------------
# Handlers
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Приветственное сообщение, уведомление о том что это ИИ и конфиденциальность.
    """
    anon_id = str(uuid.uuid4())
    context.user_data["anon_id"] = anon_id

    text = (
        "Привет! Это антибуллинг-бот, работающий на основе ИИ. Я — не реальный человек, "
        "а автоматический помощник. Вся информация, которую вы отправляете через этот бот, "
        "сохраняется анонимно и используется только для помощи и статистики.\n\n"
        "Выберите проблему из списка ниже — нажмите кнопку, соответствующую вашей ситуации."
    )
    await update.message.reply_text(text, reply_markup=make_buttons())


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка нажатий на кнопки категорий.
    """
    query = update.callback_query
    await query.answer()
    key = query.data
    anon_id = context.user_data.get("anon_id") or str(uuid.uuid4())
    context.user_data["anon_id"] = anon_id

    if key == "want_die":
        # логируем факт анонимно
        await log_event(anon_id, "want_die", "")
        # отправляем большой поддерживающий текст + номера помощи
        await query.message.reply_text(make_suicide_support_text())
        return

    elif key == "bullying_school":
        await log_event(anon_id, "bullying_school", "")
        text = (
            "Если вас травят в школе — вы не одни. Вот несколько идей:\n"
            "• Постарайтесь сохранить доказательства (скриншоты, сообщения).\n"
            "• Поговорите с доверенным взрослым (родителем, учителем, школьным психологом).\n"
            "• Если опасность физическая — сообщите в школу и, если нужно, в полицию.\n"
            "Если хотите, опишите ситуацию — и я постараюсь помочь конкретными шагами."
        )
        await query.message.reply_text(text)

    elif key == "bullying_online":
        await log_event(anon_id, "bullying_online", "")
        text = (
            "При кибербуллинге полезно:\n"
            "• Сохранить скриншоты/ссылки.\n"
            "• Заблокировать обидчика и изменить настройки приватности.\n"
            "• Сообщить в платформу (Telegram/Instagram/YouTube и т.д.).\n"
            "Опишите, что произошло, и я помогу составить сообщение/жалобу."
        )
        await query.message.reply_text(text)

    elif key == "other":
        # попросить пользователя описать проблему — этот текст пойдёт в gpt4all
        await log_event(anon_id, "other_button_clicked", "")
        await query.message.reply_text(
            "Опишите вашу проблему кратко — отправьте сообщение, и я постараюсь помочь."
        )
        # ставим флаг, что следующий текст — запрос к GPT
        context.user_data["awaiting_other_text"] = True

    else:
        await query.message.reply_text("Неизвестная команда — попробуйте ещё раз.")


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка обычных текстовых сообщений.
    Если user предварительно нажал 'Другая проблема', отправляем в модель gpt4all.
    """
    anon_id = context.user_data.get("anon_id") or str(uuid.uuid4())
    context.user_data["anon_id"] = anon_id
    text = update.message.text.strip()

    if context.user_data.get("awaiting_other_text"):
        # Снимаем флаг
        context.user_data["awaiting_other_text"] = False
        # логируем анонимно
        await log_event(anon_id, "other_problem", text)
        # отвечаем через модель gpt4all (локально)
        reply = await ask_local_model(text)
        await update.message.reply_text(reply)
    else:
        # Если просто пишет свободное сообщение — предлагаем выбрать кнопку
        await update.message.reply_text(
            "Спасибо за сообщение. Пожалуйста, выберите категорию проблемы из кнопок ( /start ).",
            reply_markup=make_buttons(),
        )


# -----------------------
# Helper: log to DB (anonymous)
# -----------------------
async def log_event(anon_id: str, category: str, text: str):
    # text can be empty for simple category clicks
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (anon_id, category, text, created_at) VALUES (?, ?, ?, ?)",
            (anon_id, category, text, datetime.utcnow().isoformat()),
        )
        await db.commit()


# -----------------------
# Helper: call local gpt4all model
# -----------------------
async def ask_local_model(prompt: str, max_tokens: int = 512) -> str:
    global gpt_model
    loop = asyncio.get_event_loop()

    if gpt_model is None:
        # Инициализация модели (может быть медленной — выполняется в отдельном потоке)
        def load_model():
            nonlocal gpt_model
            # Создаём экземпляр модели (платный файл/имя модели загружается, если нужно)
            m = GPT4All(MODEL_NAME)
            return m

        # Блокируем не в основном потоке
        gpt_model = await loop.run_in_executor(None, load_model)

    def generate_sync(prompt_text: str):
        # используем chat_session чтобы сохранить контекст в сессии, но для простоты — одноразовый вызов
        with gpt_model.chat_session() as sess:
            # можно настраивать системную подсказку
            # короткая инструкция: отвечать поддерживающе, давать практические шаги, без клинической диагностики
            system_prompt = (
                "Ты — помощник антибуллинг-бота. Отвечай кратко и поддерживающе. "
                "Если пользователь пишет о суицидальных мыслях — призови обратиться к профессионалам и покажи экстренные номера."
            )
            sess.system(system_prompt)
            sess.user(prompt_text)
            out = sess.generate(max_tokens=max_tokens)
            return out

    # Генерация в отдельном потоке
    response = await loop.run_in_executor(None, generate_sync, prompt)
    # Ограничим длину и вернём
    return response if response else "Извините, я не смог сформировать ответ — попробуйте сформулировать иначе."


# -----------------------
# Supportive message для 'Я хочу умереть'
# -----------------------
def make_suicide_support_text() -> str:
    text = (
        "Я слышу, что вы испытываете очень тяжёлые чувства. Мне очень жаль, что вам так тяжело.\n\n"
        "Если вы думаете о том, чтобы причинить себе вред или прекратить жизнь, важно как можно скорее обратиться за помощью:\n\n"
        f"{CRISIS_CONTACTS}\n\n"
        "Пожалуйста, если вы в опасности прямо сейчас — немедленно позвоните в экстренные службы (112) или обратитесь в ближайший пункт неотложной помощи.\n\n"
        "Вот что может помочь прямо сейчас:\n"
        "• Поговорите с кем-то, кому вы доверяете — другом, родственником, коллегой.\n"
        "• Постарайтесь убрать доступ к средствам, которые могли бы причинить вред.\n"
        "• Если хотите, опишите, что именно вас так беспокоит — я постараюсь поддержать и дать практические шаги.\n\n"
        "Вы не одиноки. Просьба: если есть возможность — обратитесь к профессионалу (психологу, психиатру) или на горячую линию прямо сейчас."
    )
    return text


# -----------------------
# Admin / utility: get counts (пример)
# -----------------------
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Возвращает простую статистику: количество записей по категориям
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT category, COUNT(*) FROM logs GROUP BY category")
        rows = await cur.fetchall()
    if not rows:
        await update.message.reply_text("Пока нет записей.")
        return
    msg = "Анонимная статистика (по категориям):\n"
    for cat, cnt in rows:
        msg += f"• {cat}: {cnt}\n"
    await update.message.reply_text(msg)


# -----------------------
# Main
# -----------------------
async def main():
    await init_db()

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(CommandHandler("stats", stats_command))  # admin / demo
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), text_message)
    )

    # Запуск бота
    logger.info("Запуск бота...")
    await app.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
