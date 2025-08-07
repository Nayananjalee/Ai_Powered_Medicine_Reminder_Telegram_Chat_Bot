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

async def send_telegram_reminder(user_name, user_telegram_id, med_name, quantity, meal_timing):
    if not bot:
        print("ERROR: Bot not initialized - check TELEGRAM_BOT_TOKEN")
        return False
    
    nickname = random.choice(["Bole"])
    prompt = f"""
    Generate a short, loving medication reminder for {nickname} (real name: {user_name}) to take {quantity} {med_name} {meal_timing} their meal.
    Use a warm, affectionate tone with emojis (💖, 🌸, 😘).
    Include a caring follow-up question (e.g., 'Feeling okay today?').
    Keep it under 50 words.
    """
    try:
        response = gemini_model.generate_content(prompt)
        message = response.text.strip()
        await bot.send_message(chat_id=user_telegram_id, text=message, parse_mode='Markdown')
        print(f"✅ Telegram message sent to {user_telegram_id}: {med_name}")
        return True
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")
        return False

def check_and_send_reminders():
    try:
        now = datetime.now().strftime("%H:%M")
        print(f"🔍 Checking reminders at {now}")
        
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
                            user_data["name"], 
                            telegram_id, 
                            m["name"], 
                            m["quantity"], 
                            m["meal_timing"]
                        ))
                        
                        if success:
                            supabase.table("medications").update({"sent": True}).eq("id", m["id"]).execute()
                            print(f"✅ Marked medication {m['id']} as sent")
                        else:
                            print(f"❌ Failed to send Telegram reminder")
                    else:
                        print(f"❌ Telegram ID not found for user: {user_data['name']}")
                else:
                    print(f"❌ User not found for phone: {m['user_phone']}")
            else:
                print(f"⏳ Not time yet for {m['name']} (scheduled: {m['time']}, current: {now})")
                
    except Exception as e:
        print(f"❌ Error in check_and_send_reminders: {e}")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1)
    scheduler.start()
    print(f"🚀 Your loving scheduler is ready to care for {random.choice(['Bole'])}! 💕")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("🛑 Scheduler stopped.")