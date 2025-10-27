import os
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен бота
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Ключевые слова для анализа сообщений ---
ALERT_WORDS = ["суицид", "умереть", "не хочу жить", "плохо", "депрессия", "тревога", "страшно", "паника"]
HUMAN_HELP_WORDS = ["психолог", "человек", "специалист", "консультант", "живой", "оператор", "реальный"]

# --- Наборы примерных ответов ---
SUPPORT_REPLIES = [
    "Мне очень жаль, что ты через это проходишь 💔. Помни: ты не один, и то, что ты чувствуешь — важно.",
    "Ты сделал(а) правильно, что написал(а). Иногда просто поговорить уже помогает немного отпустить боль 🌿.",
    "Каждый имеет право на уважение. Ты заслуживаешь поддержки и спокойствия ❤️.",
    "Это звучит тяжело... Пожалуйста, не держи это в себе. Я здесь, чтобы тебя выслушать.",
    "Ты не виноват(а) в том, что другие ведут себя плохо. Ты заслуживаешь доброты и понимания 💬.",
    "Иногда кажется, что выхода нет, но это чувство пройдёт. Давай попробуем разобраться вместе 🌱."
]

HELP_REPLIES = [
    "Похоже, тебе сейчас нужна поддержка специалиста 🧠. Пожалуйста, обратись за помощью:\n📞 8-800-2000-122 — бесплатная линия доверия.",
    "Я искусственный интеллект, но иногда лучше поговорить с настоящим человеком. Можно позвонить на 8-800-2000-122 или написать на https://чаты.доверие.рф 💬",
    "Думаю, сейчас будет правильно обратиться к психологу. Вот надёжные контакты:\n💬 https://чаты.доверие.рф\n📞 8-800-2000-122 (круглосуточно)."
]

SMALL_TALK = {
    "привет": [
        "Привет! Я рад, что ты написал(а) 💚 Как ты себя чувствуешь?",
        "Привет! 🌿 Что случилось, расскажи?",
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

# --- Если позже захочешь вернуть OpenAI, просто раскомментируй этот блок ---
"""
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def support_reply(message: str) -> str:
    prompt = f'''
Ты — эмпатичный ИИ-психолог. Отвечай мягко и с поддержкой.
Сообщение пользователя: "{message}"
'''
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return completion.choices[0].message.content.strip()
"""

# --- Основная логика без OpenAI ---
async def generate_local_reply(message: str) -> str:
    msg = message.lower().strip()

    # Приветствие / благодарность / прощание
    for key, options in SMALL_TALK.items():
        if key in msg:
            return random.choice(options)

    # Тревожные сигналы
    if any(word in msg for word in ALERT_WORDS):
        return (
            "Похоже, тебе сейчас тяжело 💔\n"
            "Пожалуйста, не оставайся один(одна). Вот, куда можно обратиться:\n"
            "📞 Линия доверия: 8-800-2000-122 (бесплатно, круглосуточно)\n"
            "💬 Онлайн-чат поддержки: https://чаты.доверие.рф"
        )

    # Просьба о реальной помощи
    if any(word in msg for word in HUMAN_HELP_WORDS):
        return random.choice(HELP_REPLIES)

    # Общая поддержка
    return random.choice(SUPPORT_REPLIES)


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Привет, {user.first_name or 'друг'}! 🌿\n\n"
        "Я — искусственный интеллект, созданный, чтобы поддерживать людей, "
        "которые столкнулись с кибербуллингом или тревогой.\n\n"
        "💬 Расскажи, пожалуйста, что случилось."
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    reply = await generate_local_reply(user_message)
    await update.message.reply_text(reply)


# --- Запуск бота ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
