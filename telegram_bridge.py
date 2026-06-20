import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    print("MESSAGE RECEIVED:", text)

    if text.lower().startswith("add "):
        text = text[4:].strip()

    try:
        response = requests.post(
            "http://127.0.0.1:5000/telegram-agent/run",
            json={"command": text},
            timeout=120
        )

        data = response.json()

        if data.get("success"):

            mode = data.get("mode")

            if mode == "query":
                reply = (
                    f"📚 Word: {data.get('word')}\n"
                    f"📖 Meaning: {data.get('chinese_meaning')}\n"
                    f"🔤 Pinyin: {data.get('pinyin')}\n"
                    f"🗣 Pronunciation: {data.get('phonetic')}\n\n"
                    f"Example:\n{data.get('example_sentence')}"
                )

            elif mode == "review":
                reply = (
                    f"🧠 Review Word\n\n"
                    f"Word: {data.get('word')}\n"
                    f"Meaning: {data.get('chinese_meaning')}\n"
                    f"Pinyin: {data.get('pinyin')}\n"
                    f"Pronunciation: {data.get('phonetic')}"
                )

            elif mode == "quiz":
                options = data.get("options", [])

                reply = (
                    f"📝 Quiz\n\n"
                    f"Meaning: {data.get('meaning')}\n"
                    f"Pinyin: {data.get('pinyin')}\n\n"
                    f"Choose the correct word:\n\n"
                    f"1. {options[0] if len(options) > 0 else ''}\n"
                    f"2. {options[1] if len(options) > 1 else ''}\n"
                    f"3. {options[2] if len(options) > 2 else ''}\n"
                    f"4. {options[3] if len(options) > 3 else ''}\n\n"
                    f"✅ Correct Answer: {data.get('correct_answer')}"
                )

            else:
                reply = (
                    f"✅ Word: {data.get('word')}\n"
                    f"📖 Meaning: {data.get('chinese_meaning')}\n"
                    f"🔤 Pinyin: {data.get('pinyin')}\n"
                    f"🗣 Pronunciation: {data.get('phonetic')}"
                )

        else:
            reply = f"❌ {data.get('error')}"

    except Exception as e:
        reply = f"Server error: {str(e)}"

    await update.message.reply_text(reply)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Telegram bridge started...")
    app.run_polling()


if __name__ == "__main__":
    main()