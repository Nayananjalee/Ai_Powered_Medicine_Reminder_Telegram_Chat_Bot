import os
import time
import asyncio
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot
from database import supabase
from dotenv import load_dotenv
from google.generativeai import GenerativeModel, configure
import aiohttp

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = GenerativeModel("gemini-1.5-flash")

# Initialize Telegram bot
if TELEGRAM_BOT_TOKEN:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    print(f"Telegram bot initialized with token: {TELEGRAM_BOT_TOKEN[:10]}...")
else:
    bot = None
    print("WARNING: TELEGRAM_BOT_TOKEN not found")

async def get_conversation_history(user_phone):
    """Retrieve recent conversation history."""
    try:
        conversations = supabase.table("conversations").select("*").eq("user_phone", user_phone).order("timestamp", desc=True).limit(5).execute().data
        history = "\n".join([f"User: {c['user_message']}\nBot: {c['bot_response']}" for c in conversations])
        return history or "No recent conversation history."
    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return "No recent conversation history."

async def send_telegram_reminder(user_name, user_telegram_id, med_name=None, quantity=None, meal_timing=None, task=None, user_phone=None):
    if not bot:
        print("ERROR: Bot not initialized - check TELEGRAM_BOT_TOKEN")
        return False
    
    nickname = random.choice(["Baby","Love"])
    conversation_history = await get_conversation_history(user_phone)
    if med_name:
        prompt = f"""
        Generate a loving medication reminder for {nickname} (real name: {user_name}) to take {quantity} {med_name} {meal_timing} their meal.
        Use a warm, nurse-like tone with emojis (💖, 🌸, 😘).
        Include dietary restrictions and healing advice based on the medication and conversation history:
        {conversation_history}
        For example:
        - Fexet: Avoid alcohol, rest well.
        - Moxikind: Stay hydrated, avoid dairy.
        - Predni: Low-sodium diet, monitor blood sugar.
        Keep it under 60 words, including a caring follow-up question.
        """
    else:
        prompt = f"""
        Generate a loving reminder for {nickname} (real name: {user_name}) to {task}.
        Use a warm, nurse-like tone with emojis (💖, 🌸, 😘).
        Include health advice based on the task and conversation history:
        {conversation_history}
        For example, for 'drink water', suggest hydration tips.
        Keep it under 60 words, including a caring follow-up question.
        """
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                response = gemini_model.generate_content(prompt)
                message = response.text.strip()
                await bot.send_message(chat_id=user_telegram_id, text=message, parse_mode='Markdown')
                print(f"✅ Telegram message sent to {user_telegram_id}: {med_name or task}")
                return True
            except Exception as e:
                print(f"❌ Error sending Telegram message (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return False

def check_and_send_reminders():
    try:
        now = datetime.now().strftime("%H:%M")
        print(f"🔍 Checking reminders at {now}")
        
        # Check medications
        meds = supabase.table("medications").select("*").eq("sent", False).execute().data
        print(f"📋 Found {len(meds)} unsent medications")
        for m in meds:
            print(f"⏰ Medication {m['name']} scheduled for {m['time']}, current time: {now}")
            if m["time"] == now:
                print(f"🎯 Time match! Processing medication: {m['name']}")
                user = supabase.table("users").select("*").eq("phone", m["user_phone"]).execute().data
                if user:
                    user_data = user[0]
                    telegram_id = user_data.get("telegram_id")
                    if telegram_id:
                        print(f"👤 Telegram user found: {user_data['name']} (ID: {telegram_id})")
                        success = asyncio.run(send_telegram_reminder(
                            user_data["name"], telegram_id, m["name"], m["quantity"], m["meal_timing"], None, m["user_phone"]
                        ))
                        if success:
                            supabase.table("medications").update({"sent": True}).eq("id", m["id"]).execute()
                            print(f"✅ Marked medication {m['id']} as sent")
                        else:
                            print(f"❌ Failed to send Telegram medication reminder")
                    else:
                        print(f"❌ Telegram ID not found for user: {user_data['name']}")
                else:
                    print(f"❌ User not found for phone: {m['user_phone']}")
            else:
                print(f"⏳ Not time yet for {m['name']} (scheduled: {m['time']}, current: {now})")
        
        # Check reminders
        reminders = supabase.table("reminders").select("*").eq("sent", False).execute().data
        print(f"📋 Found {len(reminders)} unsent reminders")
        for r in reminders:
            print(f"⏰ Reminder {r['task']} scheduled for {r['time']}, current time: {now}")
            if r["time"] == now:
                print(f"🎯 Time match! Processing reminder: {r['task']}")
                user = supabase.table("users").select("*").eq("phone", r["user_phone"]).execute().data
                if user:
                    user_data = user[0]
                    telegram_id = user_data.get("telegram_id")
                    if telegram_id:
                        print(f"👤 Telegram user found: {user_data['name']} (ID: {telegram_id})")
                        success = asyncio.run(send_telegram_reminder(
                            user_data["name"], telegram_id, None, None, None, r["task"], r["user_phone"]
                        ))
                        if success:
                            supabase.table("reminders").update({"sent": True}).eq("id", r["id"]).execute()
                            print(f"✅ Marked reminder {r['id']} as sent")
                        else:
                            print(f"❌ Failed to send Telegram reminder")
                    else:
                        print(f"❌ Telegram ID not found for user: {user_data['name']}")
                else:
                    print(f"❌ User not found for phone: {r['user_phone']}")
            else:
                print(f"⏳ Not time yet for {r['task']} (scheduled: {r['time']}, current: {now})")
                
    except Exception as e:
        print(f"❌ Error in check_and_send_reminders: {e}")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1)
    scheduler.start()
    print(f"🚀 Chuty, your loving nurse bot, is ready to care for {random.choice(['Baby','Love'])}! 🧑‍⚕️💕")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("🛑 Scheduler stopped.")