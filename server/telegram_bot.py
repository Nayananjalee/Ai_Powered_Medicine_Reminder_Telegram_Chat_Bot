import os
import random
import asyncio
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from database import supabase
from google.generativeai import GenerativeModel, configure

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Gemini AI
configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = GenerativeModel("gemini-1.5-flash")

# Initialize Telegram bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def ensure_user_exists(user_id, user_name):
    """Ensure a user exists in the users table, create if not."""
    user_phone = f"tg_{user_id}"
    user_data = {
        "name": user_name,
        "phone": user_phone,
        "telegram_id": str(user_id)
    }
    try:
        existing_user = supabase.table("users").select("*").eq("telegram_id", user_data["telegram_id"]).execute().data
        if not existing_user:
            logger.info(f"Creating new user: {user_data}")
            supabase.table("users").insert(user_data).execute()
            logger.info(f"User created successfully: {user_phone}")
        else:
            logger.info(f"User already exists: {user_phone}")
        return user_phone
    except Exception as e:
        logger.error(f"Error creating user {user_phone}: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nickname = random.choice(["Bole", "Kukku Patto"])
    try:
        await ensure_user_exists(user.id, user.first_name)
        await update.message.reply_text(
            f"Hey {nickname}, my sweetest! I'm your loving Medication Reminder Bot! 💖\n"
            "Just tell me about your meds, like 'Fexet night 1' or 'Predni morning 2', and I'll set reminders.\n"
            "Here’s how I can pamper you:\n"
            "💊 /start - Get cozy with me\n"
            "💡 /help - See sweet examples\n"
            "📋 /status - Check your meds\n"
            "🗑️ /clear - Start fresh\n"
            "😘 /love - A little love note from me!"
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            f"Oh, {nickname}, something went wrong setting you up! 😔 Please try /start again or contact support. 💕"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = random.choice(["Bole", "Kukku Patto"])
    await update.message.reply_text(
        f"Hi {nickname}! Here’s how you can tell me about your meds:\n"
        "🌸 'Fexet night 1' → 1 Fexet at night\n"
        "🌸 'Moxikind every meal one' → 1 Moxikind with meals\n"
        "🌸 'Predni morning 2' → 2 Predni in the morning\n"
        "🌸 'Lisinopril 5mg twice a day before meals'\n"
        f"I'll confirm the times with you! Use /status to see your meds or /clear to start fresh. 😘"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    nickname = random.choice(["Bole", "Kukku Patto"])
    meds = supabase.table("medications").select("*").eq("user_phone", f"tg_{user_id}").execute().data
    if not meds:
        await update.message.reply_text(f"No meds yet, {nickname}! Tell me what you’re taking, and I’ll remind you with love. 💕")
        return
    response = f"Your meds, my dear {nickname}:\n"
    for med in meds:
        response += f"💊 {med['name']} - {med['quantity']} ({med['frequency']}, {med['meal_timing']} meal) at {med['time']}\n"
    await update.message.reply_text(response + f"You’re doing amazing, {nickname}! Keep it up! 🌟")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    nickname = random.choice(["Bole", "Kukku Patto"])
    supabase.table("medications").delete().eq("user_phone", f"tg_{user_id}").execute()
    await update.message.reply_text(f"All your meds are cleared, {nickname}. Ready for a fresh start? 😊")

async def love(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = random.choice(["Bole", "Kukku Patto"])
    prompt = f"Generate a short, loving message for {nickname}, using a warm and affectionate tone with emojis. Keep it sweet and under 50 words."
    try:
        response = gemini_model.generate_content(prompt)
        await update.message.reply_text(response.text.strip())
    except Exception as e:
        await update.message.reply_text(f"Just a little note, {nickname}, to say I adore you! 😘")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower().strip()
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    nickname = random.choice(["Bole", "Kukku Patto"])

    # Ensure user exists before processing
    try:
        user_phone = await ensure_user_exists(user_id, user_name)
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}")
        await update.message.reply_text(
            f"Oh, {nickname}, I had trouble setting you up! 😔 Please try /start again. 💕"
        )
        return

    # Check if user is confirming a previous medication
    if context.user_data.get("pending_medications"):
        pending_meds = context.user_data["pending_medications"]
        if user_message.startswith("yes"):
            for med_data in pending_meds:
                times = med_data.get("time", "08:00").split(",")
                for time in times:
                    med = {
                        "user_phone": user_phone,
                        "name": med_data["name"],
                        "quantity": med_data["quantity"],
                        "meal_timing": med_data["meal_timing"],
                        "frequency": med_data["frequency"],
                        "time": time.strip(),
                        "sent": False
                    }
                    logger.info(f"Inserting confirmed medication into Supabase: {med}")
                    try:
                        supabase.table("medications").insert(med).execute()
                    except Exception as e:
                        logger.error(f"Error inserting medication {med['name']}: {e}")
                        await update.message.reply_text(
                            f"Oh, {nickname}, I couldn’t save {med['name']}! 😔 Please try again. 💕"
                        )
                        return
            context.user_data["pending_medications"] = []
            await update.message.reply_text(
                f"All set, my dear {nickname}! Your meds are saved, and I’ll remind you with love. 💖 How are you feeling today? 😘"
            )
            return
        elif user_message.startswith("no"):
            # Extract new times if provided (e.g., "no, 09:00")
            new_times = user_message.replace("no", "").strip().split(",")
            if new_times and new_times[0]:
                for med_data in pending_meds:
                    med_data["time"] = ",".join(new_times)
                    med_data["confirmation"] = f"Is {','.join(new_times)} okay for {med_data['name']}, {nickname}?"
                context.user_data["pending_medications"] = pending_meds
                response = f"Okay, {nickname}, I’ve updated the times to {','.join(new_times)}. Is that right? 😊 Reply ‘yes’ or ‘no, <new time>’."
                await update.message.reply_text(response)
                return
            else:
                context.user_data["pending_medications"] = []
                await update.message.reply_text(f"No worries, {nickname}. Let’s try again. Tell me about your meds! 🌸")
                return

    # Use Gemini AI to parse new medication input
    prompt = f"""
    You are a loving medication reminder bot addressing the user as '{nickname}'. 
    From this message: "{user_message}"
    1. Extract medication details into a JSON array of objects, each with:
       - name (e.g., 'Fexet')
       - quantity (integer, default 1)
       - meal_timing ('before' or 'after', default 'before')
       - frequency ('daily' or 'every6hours', default 'daily')
       - time ('HH:MM', map phrases like 'morning' to '08:00', 'night' to '20:00', 'every meal' to '08:00,14:00,20:00', default '08:00')
       - confirmation (e.g., 'Is 20:00 okay for Fexet, {nickname}?')
    2. Generate a warm, affectionate response listing medications and asking for confirmation. Use emojis (💖, 🌸, 😘) and keep it under 100 words.
    3. If no medication details, return an empty array and ask a caring question (e.g., 'How are you feeling, {nickname}?').
    4. Return valid JSON only, no comments or extra text.
    Return format:
    {{
      "medication": [
        {{"name": "...", "quantity": 1, "meal_timing": "...", "frequency": "...", "time": "...", "confirmation": "..."}},
        ...
      ],
      "response": "..."
    }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        logger.info(f"Gemini raw response: {response.text}")
        # Strip JSON markers and parse safely
        response_text = response.text.strip()
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        result = json.loads(response_text)
        med_data_list = result.get("medication", [])
        bot_response = result.get("response", f"Hmm, {nickname}, I didn’t catch that. Could you tell me about your meds? 😊")

        if med_data_list:
            context.user_data["pending_medications"] = med_data_list
            logger.info(f"Pending medications for confirmation: {med_data_list}")
            await update.message.reply_text(
                f"{bot_response} Reply ‘yes’ to confirm or ‘no, <new time>’ to change. 💕"
            )
        else:
            context.user_data["pending_medications"] = []
            await update.message.reply_text(bot_response)

    except json.JSONDecodeError as je:
        logger.error(f"JSON parse error: {je} - Raw response: {response.text}")
        await update.message.reply_text(
            f"Oh, {nickname}, I got a bit confused! Could you tell me about your meds again? 😊"
        )
    except Exception as e:
        logger.error(f"Error processing message: {e} - Raw response: {response.text}")
        await update.message.reply_text(
            f"Oh, {nickname}, something went wrong: {str(e)}. Tell me about your meds again? 😘"
        )

def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("love", love))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"✅ Your loving bot is ready to care for {random.choice(['Bole', 'Kukku Patto'])}! 💖")
    app.run_polling(poll_interval=1)

if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        print(f"Error starting bot: {e}")