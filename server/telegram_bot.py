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
from datetime import datetime
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Gemini AI
configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = GenerativeModel("gemini-2.0-flash")

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

async def save_conversation(user_phone, user_message, bot_response):
    """Save conversation to Supabase."""
    try:
        conversation_data = {
            "user_phone": user_phone,
            "user_message": user_message,
            "bot_response": bot_response,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Saving conversation: {conversation_data}")
        supabase.table("conversations").insert(conversation_data).execute()
        logger.info(f"Conversation saved successfully")
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")

async def get_conversation_history(user_phone):
    """Retrieve recent conversation history."""
    try:
        conversations = supabase.table("conversations").select("*").eq("user_phone", user_phone).order("timestamp", desc=True).limit(5).execute().data
        history = "\n".join([f"User: {c['user_message']}\nBot: {c['bot_response']}" for c in conversations])
        return history or "No recent conversation history."
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return "No recent conversation history."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nickname = random.choice(["Baby","Love"])
    try:
        user_phone = await ensure_user_exists(user.id, user.first_name)
        bot_response = (
            f"Hey {nickname}, my sweetest! I'm Chuty, your loving nurse bot! 🧑‍⚕️💖\n"
            "Tell me about your meds (e.g., 'Fexet night 1'), reminders (e.g., 'drink water at 4:45 PM'), or how you're feeling. 😘\n"
            "Commands:\n"
            "💊 /start - Get cozy with me\n"
            "💡 /help - See examples\n"
            "📋 /status - Check meds and reminders\n"
            "🗑️ /clear - Start fresh\n"
            "😘 /love - A loving note"
        )
        await update.message.reply_text(bot_response)
        await save_conversation(user_phone, "/start", bot_response)
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        bot_response = f"Oh, {nickname}, something went wrong setting you up! 😔 Please try /start again. 💕"
        await update.message.reply_text(bot_response)
        await save_conversation(user_phone, "/start", bot_response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = random.choice(["Baby","Love"])
    user_phone = f"tg_{update.effective_user.id}"
    bot_response = (
        f"Hi {nickname}! I'm Chuty, your nurse bot. 🌸 Here's how to chat:\n"
        "💊 Meds: 'Fexet night 1' → 1 Fexet at night\n"
        "💧 Reminders: 'Drink water at 4:45 PM'\n"
        "💬 Health: 'I have a cold' or 'Going to a party tonight'\n"
        "I'll guide you with love! Use /status, /clear, or /love. 😘"
    )
    await update.message.reply_text(bot_response)
    await save_conversation(user_phone, "/help", bot_response)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    nickname = random.choice(["Baby", "Love"])
    user_phone = f"tg_{user_id}"
    meds = supabase.table("medications").select("*").eq("user_phone", user_phone).execute().data
    reminders = supabase.table("reminders").select("*").eq("user_phone", user_phone).execute().data
    bot_response = f"Your schedule, my dear {nickname}:\n"
    if meds:
        bot_response += "\n💊 Medications:\n"
        for med in meds:
            bot_response += f"  {med['name']} - {med['quantity']} ({med['frequency']}, {med['meal_timing']} meal) at {med['time']}\n"
    if reminders:
        bot_response += "\n💧 Reminders:\n"
        for rem in reminders:
            bot_response += f"  {rem['task']} at {rem['time']}\n"
    if not (meds or reminders):
        bot_response = f"No meds or reminders yet, {nickname}! Tell me what you need, and I’ll care for you. 💕\n"
    bot_response += f"How can I help you feel better today? 🌟"
    await update.message.reply_text(bot_response)
    await save_conversation(user_phone, "/status", bot_response)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    nickname = random.choice(["Baby", "Love"])
    user_phone = f"tg_{user_id}"
    supabase.table("medications").delete().eq("user_phone", user_phone).execute()
    supabase.table("reminders").delete().eq("user_phone", user_phone).execute()
    bot_response = f"All your meds and reminders are cleared, {nickname}. Ready for a fresh start? 😊 How’s your health today? 💖"
    await update.message.reply_text(bot_response)
    await save_conversation(user_phone, "/clear", bot_response)

async def love(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = random.choice(["Baby","Love"])
    user_phone = f"tg_{update.effective_user.id}"
    prompt = f"Generate a short, loving message for {nickname}, using a warm, affectionate tone with emojis (💖, 🌸, 😘). Use only the nickname {nickname}. Keep it sweet and under 50 words."
    try:
        response = gemini_model.generate_content(prompt)
        bot_response = response.text.strip()
    except Exception as e:
        logger.error(f"Error generating love message: {e}")
        bot_response = f"Just a little note, {nickname}, to say I adore you! 😘"
    await update.message.reply_text(bot_response)
    await save_conversation(user_phone, "/love", bot_response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower().strip()
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    nickname = random.choice(["Baby","Love"])
    user_phone = f"tg_{user_id}"

    # Ensure user exists
    try:
        user_phone = await ensure_user_exists(user_id, user_name)
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}")
        bot_response = f"Oh, {nickname}, I had trouble setting you up! 😔 Please try /start again. 💕"
        await update.message.reply_text(bot_response)
        await save_conversation(user_phone, user_message, bot_response)
        return

    # Check if user is confirming a previous medication or reminder
    if context.user_data.get("pending_medications") or context.user_data.get("pending_reminders"):
        pending_meds = context.user_data.get("pending_medications", [])
        pending_reminders = context.user_data.get("pending_reminders", [])
        if user_message.startswith("yes"):
            # Save medications
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
                        bot_response = f"Oh, {nickname}, I couldn’t save {med['name']}! 😔 Please try again. 💕"
                        await update.message.reply_text(bot_response)
                        await save_conversation(user_phone, user_message, bot_response)
                        return
            # Save reminders
            for rem_data in pending_reminders:
                rem = {
                    "user_phone": user_phone,
                    "task": rem_data["task"],
                    "time": rem_data["time"],
                    "sent": False
                }
                logger.info(f"Inserting confirmed reminder into Supabase: {rem}")
                try:
                    supabase.table("reminders").insert(rem).execute()
                except Exception as e:
                    logger.error(f"Error inserting reminder {rem['task']}: {e}")
                    bot_response = f"Oh, {nickname}, I couldn’t save the {rem['task']} reminder! 😔 Please try again. 💕"
                    await update.message.reply_text(bot_response)
                    await save_conversation(user_phone, user_message, bot_response)
                    return
            context.user_data["pending_medications"] = []
            context.user_data["pending_reminders"] = []
            bot_response = f"All set, my dear {nickname}! Your meds and reminders are saved. 💖 How are you feeling today? 😘"
            await update.message.reply_text(bot_response)
            await save_conversation(user_phone, user_message, bot_response)
            return
        elif user_message.startswith("no"):
            new_times = user_message.replace("no", "").strip().split(",")
            if new_times and new_times[0]:
                for med_data in pending_meds:
                    med_data["time"] = ",".join(new_times)
                    med_data["confirmation"] = f"Is {','.join(new_times)} okay for {med_data['name']}, {nickname}?"
                for rem_data in pending_reminders:
                    rem_data["time"] = new_times[0]
                    rem_data["confirmation"] = f"Is {new_times[0]} okay for {rem_data['task']}, {nickname}?"
                context.user_data["pending_medications"] = pending_meds
                context.user_data["pending_reminders"] = pending_reminders
                bot_response = f"Okay, {nickname}, I’ve updated the times to {','.join(new_times)}. Is that right? 😊 Reply ‘yes’ or ‘no, new time (e.g., 18:00)’ to change. 💕"
                await update.message.reply_text(bot_response)
                await save_conversation(user_phone, user_message, bot_response)
                return
            else:
                context.user_data["pending_medications"] = []
                context.user_data["pending_reminders"] = []
                bot_response = f"No worries, {nickname}. Let’s try again. Tell me about your meds, reminders, or health! 🌸"
                await update.message.reply_text(bot_response)
                await save_conversation(user_phone, user_message, bot_response)
                return

    # Fetch conversation history
    conversation_history = await get_conversation_history(user_phone)

    # Use Gemini AI to parse message with retry logic
    prompt = f"""
    You are Chuty, a loving nurse-like bot addressing the user ONLY as 'Baby' or 'Love' (use '{nickname}' for this response). 
    Conversation history:
    {conversation_history}

    Current message: "{user_message}"

    1. If the message contains medication details, extract them into a JSON array of objects, each with:
       - name (e.g., 'Fexet')
       - quantity (integer, default 1)
       - meal_timing ('before' or 'after', default 'before')
       - frequency ('daily' or 'every6hours', default 'daily')
       - time ('HH:MM', map 'morning' to '08:00', 'night' to '20:00', 'every meal' to '08:00,14:00,20:00', default '08:00')
       - confirmation (e.g., 'Is 20:00 okay for Fexet, {nickname}?')
    2. If the message contains a non-medication reminder (e.g., 'drink water at 4:45 PM'), extract into a JSON array of objects, each with:
       - task (e.g., 'drink water')
       - time ('HH:MM', e.g., '16:45')
       - confirmation (e.g., 'Is 16:45 okay for drinking water, {nickname}?')
    3. If no medication or reminder, provide nurse-like health advice based on the message and history (e.g., hydration tips, party advice).
    4. Generate a warm, affectionate response (under 100 words) with emojis (💖, 🌸, 😘). For meds/reminders
    5. Return valid JSON:
    {{
      "medication": [{{"name": "...", "quantity": 1, "meal_timing": "...", "frequency": "...", "time": "...", "confirmation": "..."}}] or [],
      "reminders": [{{"task": "...", "time": "...", "confirmation": "..."}}] or [],
      "response": "..."
    }}
    """
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                response = gemini_model.generate_content(prompt)
                logger.info(f"Gemini raw response: {response.text}")
                response_text = response.text.strip()
                if response_text.startswith("```json") and response_text.endswith("```"):
                    response_text = response_text[7:-3].strip()
                result = json.loads(response_text)
                med_data_list = result.get("medication", [])
                rem_data_list = result.get("reminders", [])
                bot_response = result.get("response", f"Hmm, {nickname}, I didn’t catch that. Tell me about your meds, reminders, or health! 😊")

                # Validate and construct response
                if med_data_list or rem_data_list:
                    expected_response = f"Got it, {nickname}! 💖"
                    if med_data_list:
                        for med_data in med_data_list:
                            time_label = "night" if med_data["time"] == "20:00" else "time"
                            expected_response += f" {med_data['name']} {med_data['quantity']} at {med_data['time']} ({time_label})."
                    if rem_data_list:
                        for rem_data in rem_data_list:
                            expected_response += f" {rem_data['task'].capitalize()} at {rem_data['time']}."
                    expected_response += f" Is this right? 😊 Reply ‘yes’ or ‘no, new time (e.g., 18:00)’ to change. 💕"
                    bot_response = expected_response  # Override with correct format

                context.user_data["pending_medications"] = med_data_list
                context.user_data["pending_reminders"] = rem_data_list
                logger.info(f"Pending medications: {med_data_list}, Pending reminders: {rem_data_list}")
                await update.message.reply_text(bot_response)
                await save_conversation(user_phone, user_message, bot_response)
                return

            except json.JSONDecodeError as je:
                logger.error(f"JSON parse error (attempt {attempt + 1}): {je} - Raw response: {response.text}")
                bot_response = f"Oh, {nickname}, I got a bit confused! Could you tell me about your meds, reminders, or health again? 😊"
                await update.message.reply_text(bot_response)
                await save_conversation(user_phone, user_message, bot_response)
                return
            except Exception as e:
                logger.error(f"Error processing message (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                bot_response = f"Oh, {nickname}, something went wrong: {str(e)}. Tell me about your meds, reminders, or health again? 😘"
                await update.message.reply_text(bot_response)
                await save_conversation(user_phone, user_message, bot_response)
                return

def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("love", love))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"✅ Chuty, your loving nurse bot, is ready to care for {random.choice(['Baby','Love'])}! 🧑‍⚕️💖")
    app.run_polling(poll_interval=1)

if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        print(f"Error starting bot: {e}")