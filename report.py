# report.py
"""
Отчёт по работе антибуллинг-бота.

Читает:
  - stats/events_YYYY-MM-DD.csv
  - stats/counters.json (если есть)

Печатает:
  1) Общую статистику по сообщениям, кнопкам и кризисным сигналам.
  2) Какие кнопки нажимали чаще всего.
  3) Динамику по дням.
  4) Несколько анонимизированных примеров кризисных сообщений.

Запуск:
  python report.py
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from textwrap import shorten

STATS_DIR = Path("stats")

# Человеческие названия кнопок
BUTTON_LABELS = {
    "p_self": "🙋 Я сталкиваюсь с буллингом",
    "p_witness": "👀 Я свидетель буллинга",
    "p_rights": "⚖️ Права и куда обратиться",
    "p_hotline": "🆘 Экстренная помощь",
    "chat_ai": "💬 Поговорить на другую тему (ИИ)",
}


def load_counters():
    path = STATS_DIR / "counters.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main():
    if not STATS_DIR.exists():
        print("⛔ Папка stats/ не найдена. Пока нет данных для отчёта.")
        return

    files = sorted(STATS_DIR.glob("events_*.csv"))
    if not files:
        print("⛔ В папке stats/ нет файлов events_YYYY-MM-DD.csv.")
        return

    # Совокупные счётчики
    total_by_type = Counter()          # message / message_ai / button / crisis / system
    button_counts = Counter()          # по кодам кнопок
    per_day = defaultdict(Counter)     # date -> Counter
    crisis_examples = []               # несколько текстов кризисных сообщений (анонимизированных)

    for f in files:
        date_str = f.stem.replace("events_", "")  # YYYY-MM-DD
        with f.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                ev_type = row.get("type", "")
                label = row.get("label", "")
                text = (row.get("text", "") or "").strip()

                total_by_type[ev_type] += 1
                per_day[date_str][ev_type] += 1

                if ev_type == "button" and label:
                    button_counts[label] += 1

                if ev_type == "crisis" and text:
                    if len(crisis_examples) < 5:
                        crisis_examples.append(shorten(text, width=120, placeholder="…"))

    counters_json = load_counters()

    # ---------- 1. Общая статистика ----------
    days_count = len(per_day)
    messages_total = total_by_type["message"] + total_by_type["message_ai"]
    ai_messages = total_by_type["message_ai"]
    crisis_total = total_by_type["crisis"]
    button_total = total_by_type["button"]

    print("📊 ОТЧЁТ О РАБОТЕ АНТИБУЛЛИНГ-БОТА")
    print("=" * 60)
    print(f"📅 Количество дней, за которые есть данные: {days_count}")
    print(f"💬 Всего пользовательских сообщений: {messages_total}")
    print(f"🤖 Из них в режиме ИИ: {ai_messages}")
    print(f"🔘 Всего нажатий кнопок: {button_total}")
    print(f"⚠️ Кризисных сигналов (фраз с сильным риском): {crisis_total}")
    print()

    if counters_json:
        print("ℹ️ Данные из counters.json (агрегированные):")
        try:
            b = counters_json.get("buttons", {})
            print(f"  • Сообщений всего: {counters_json.get('messages_total', messages_total)}")
            print(f"  • Сообщений в ИИ-режиме: {counters_json.get('ai_messages', ai_messages)}")
            print(f"  • Кризисных сигналов: {counters_json.get('crisis_detected', crisis_total)}")
        except Exception:
            print("  (не удалось корректно прочитать counters.json)")
        print()

    # ---------- 2. Какие кнопки нажимали чаще ----------
    if button_counts:
        print("🔘 КАКИЕ КНОПКИ ИСПОЛЬЗУЮТ ЧАЩЕ ВСЕГО")
        print("-" * 60)
        total_btn = sum(button_counts.values())
        for code, count in button_counts.most_common():
            title = BUTTON_LABELS.get(code, code)
            percent = (count / total_btn) * 100 if total_btn else 0
            print(f"{title:<40} — {count:>4} раз(а) ({percent:>5.1f}%)")
        print()
    else:
        print("🔘 Кнопки пока ни разу не нажимали.\n")

    # ---------- 3. Динамика по дням ----------
    print("📅 ДИНАМИКА ПО ДНЯМ")
    print("-" * 60)
    print("Дата         | Сообщений | ИИ-режим | Нажатий кнопок | Кризисные сигналы")
    print("-------------+-----------+----------+----------------+-------------------")
    for date in sorted(per_day.keys()):
        c = per_day[date]
        day_msg = c["message"] + c["message_ai"]
        day_ai = c["message_ai"]
        day_btn = c["button"]
        day_crisis = c["crisis"]
        print(f"{date} | {day_msg:9} | {day_ai:8} | {day_btn:14} | {day_crisis:17}")
    print()

    # ---------- 4. Примеры кризисных сообщений ----------
    if crisis_examples:
        print("⚠️ ПРИМЕРЫ КРИЗИСНЫХ СООБЩЕНИЙ (АНОНИМНЫЕ, СОКРАЩЁННЫЕ)")
        print("-" * 60)
        print("Эти фразы могут помочь школьному психологу понять, с какими\n"
              "переживаниями дети чаще всего приходят к боту.\n")
        for i, txt in enumerate(crisis_examples, start=1):
            print(f"{i}) {txt}")
        print()
    else:
        print("⚠️ За этот период не зафиксировано сообщений с явными кризисными фразами.\n")

    print("✅ Отчёт сформирован. Этот текст можно копировать в отчёты для школы/вузa,\n"
          "чтобы показать, как бот используется и где нужны дополнительные меры поддержки.")


if __name__ == "__main__":
    main()
