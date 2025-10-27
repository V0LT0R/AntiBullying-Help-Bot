import os
import random
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Ключевые слова ---
ALERT_WORDS = ["суицид", "умереть", "не хочу жить", "плохо", "депрессия", "тревога", "страшно", "паника"]
HUMAN_HELP_WORDS = ["психолог", "человек", "специалист", "консультант", "живой", "оператор", "реальный"]

# --- Готовые ответы ---
SUPPORT_REPLIES = [
    "Мне очень жаль, что ты через это проходишь 💔. Помни: ты не один, и то, что ты чувствуешь — важно.",
    "Ты сделал(а) правильно, что написал(а). Иногда просто поговорить уже помогает немного отпустить боль 🌿.",
    "Каждый имеет право на уважение. Ты заслуживаешь поддержки и спокойствия ❤️.",
    "Это звучит тяжело... Пожалуйста, не держи это в себе. Я здесь, чтобы тебя выслушать.",
    "Ты не виноват(а) в том, что другие ведут себя плохо. Ты заслуживаешь доброты и понимания 💬.",
    "Иногда кажется, что выхода нет, но это чувство пройдёт. Давай попробуем разобраться вместе 🌱."
]

HELP_REPLIES = [
    "Похоже, тебе сейчас нужна поддержка специалиста 🧠. Обратись за помощью:\n📞 8-800-2000-122 — бесплатная линия доверия.",
    "Я искусственный интеллект, но иногда лучше поговорить с настоящим человеком.\n📞 8-800-2000-122\n💬 https://чаты.доверие.рф",
    "Думаю, сейчас будет правильно обратиться к психологу. Надёжные контакты:\n💬 https://чаты.доверие.рф\n📞 8-800-2000-122 (круглосуточно)."
]

SELF_HELP = [
    "Попробуй сделать глубокий вдох и медленно выдохнуть 🌿. Повтори это несколько раз.",
    "Иногда помогает записать всё, что тревожит, на бумагу. Это немного освобождает разум ✍️.",
    "Если можешь — выйди на улицу и подыши воздухом 🌤. Даже короткая прогулка помогает.",
    "Послушай спокойную музыку или помедитируй — это помогает телу и уму восстановиться 🕊."
]

SMALL_TALK = {
    "привет": [
        "Привет! 💚 Как ты себя чувствуешь?",
        "Привет 🌿 Что случилось?",
        "Здравствуйте! Я здесь, чтобы выслушать вас 💬."
    ],
    "спасибо": [
        "Пожалуйста 💚. Ты сделал(а) важный шаг, обратившись за поддержкой.",
        "Рада помочь 🌿. Не забывай заботиться о себе.",
        "Всегда пожалуйста 💬. Главное — не оставайся один(одна)."
    ],
    "пока": [
        "Береги себя 🌱. Если станет тяжело — я всегда рядом.",
        "Хорошего тебе дня 💚",
        "До скорого 🌿"
    ]
}


# --- Функция генерации ответа ---
async def generate_local_reply(message: str) -> str:
    msg = message.lower().strip()

    for key, options in SMALL_TALK.items():
        if key in msg:
            return random.choice(options)

    if any(word in msg for word in ALERT_WORDS):
        return (
            "Похоже, тебе сейчас тяжело 💔\n"
            "Пожалуйста, не оставайся один(одна). Вот, куда можно обратиться:\n"
            "📞 Линия доверия: 8-800-2000-122\n"
            "💬 Онлайн-чат: https://чаты.доверие.рф"
        )

    if any(word in msg for word in HUMAN_HELP_WORDS):
        return random.choice(HELP_REPLIES)

    return random.choice(SUPPORT_REPLIES)


# --- Кнопки ---
def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["💬 Поговорить с ботом", "🧠 Обратиться к профессионалу"],
            ["📘 Советы по самопомощи", "🕊 О проекте"]
        ],
        resize_keyboard=True
    )


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Привет, {user.first_name or 'друг'}! 🌿\n\n"
        "Я — искусственный интеллект, созданный, чтобы помогать людям, "
        "которые столкнулись с кибербуллингом, тревогой или стрессом.\n\n"
        
    )
    await update.message.reply_text(text, reply_markup=main_menu())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if "профессионал" in text:
        reply = random.choice(HELP_REPLIES)
    elif "советы" in text:
        reply = random.choice(SELF_HELP)
    elif "о проекте" in text:
        reply = (
            "🌿 *О проекте*\n\n"
            "Этот бот создан как часть платформы психологической поддержки жертв кибербуллинга.\n"
            "Он помогает людям делиться своими переживаниями и при необходимости "
            "направляет к специалистам.\n\n"
            "Автор: Белощицкий Евгений и Белощицкий Артем 💚"
        )
    else:
        reply = (
            "💬 Расскажи, пожалуйста, что случилось."
        )

    await update.message.reply_text(reply, reply_markup=main_menu(), parse_mode="Markdown")


# --- Запуск бота ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
