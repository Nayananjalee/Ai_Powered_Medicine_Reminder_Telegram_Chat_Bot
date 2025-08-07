# AI-Powered Medication Reminder Bot

A smart Telegram bot that uses **Gemini AI** to understand natural language and automatically manage medication reminders. No frontend needed - everything happens through conversational AI!

## Features
- 🤖 **AI-Powered**: Uses Google's Gemini AI to understand natural language
- 💬 **Conversational**: Users just chat naturally with the bot
- 📱 **Telegram Integration**: Works entirely through Telegram
- ⏰ **Smart Reminders**: Automatic scheduling and friendly notifications
- 🧠 **Intelligent**: Extracts medication info from natural language
- 🗄️ **Database Storage**: All data stored in Supabase

## How It Works

1. **User starts the bot** with `/start`
2. **User tells the bot** about their medication in natural language
3. **AI extracts information** and saves to database
4. **Bot sends friendly reminders** at scheduled times

## Example Conversations

```
User: "I need to take 2 aspirin tablets daily after breakfast"
Bot: ✅ Medication Added Successfully!
     💊 Aspirin
     📊 Quantity: 2
     ⏰ Time: 08:00 (daily)
     🍽️ Take: after meal

User: "Remind me to take lisinopril 5mg twice a day before meals"
Bot: ✅ Medication Added Successfully!
     💊 Lisinopril
     📊 Quantity: 1
     ⏰ Time: 08:00 (daily)
     🍽️ Take: before meal
```

---

## Setup Instructions

### 1. **Create Telegram Bot**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Save your **Bot Token**

### 2. **Get Gemini API Key**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Save your **Gemini API Key**

### 3. **Set Up Supabase**
1. [Sign up for Supabase](https://supabase.com/)
2. Create a new project
3. Run the SQL in `server/supabase_schema.sql`
4. Get your **Project URL** and **anon key**

### 4. **Configure Environment**
Create `server/.env`:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

### 5. **Install Dependencies**
```bash
cd server
pip install -r requirements.txt
```

### 6. **Run the Bot**
```bash
python telegram_bot.py
```

### 7. **Run the Scheduler** (in another terminal)
```bash
python scheduler.py
```

---

## Bot Commands

- `/start` - Start the bot and register
- `/help` - Show help and examples
- `/status` - Check your current medications
- `/clear` - Clear all your medications

---

## Natural Language Examples

Users can say things like:
- "I take 2 aspirin tablets daily after breakfast"
- "Remind me to take lisinopril 5mg twice a day before meals"
- "I need to take vitamin D 1000 IU once daily"
- "Set reminder for metformin 500mg twice daily with meals"
- "I take blood pressure medicine every morning"

The AI will automatically extract:
- Medication name
- Quantity/dosage
- Frequency (daily, twice daily, etc.)
- Meal timing (before/after)
- Preferred time

---

## Architecture

```
Telegram Bot (telegram_bot.py)
    ↓
Gemini AI (Natural Language Processing)
    ↓
Supabase Database (Store medication data)
    ↓
Scheduler (scheduler.py)
    ↓
Send Reminders via Telegram
```

---

## Benefits

✅ **No Frontend Required** - Everything through Telegram
✅ **Natural Language** - Users speak naturally
✅ **AI-Powered** - Intelligent understanding
✅ **Automatic** - No manual data entry
✅ **User-Friendly** - Familiar chat interface
✅ **Scalable** - Works for any number of users

---

## Deployment

### Local Development
- Run `telegram_bot.py` for the bot
- Run `scheduler.py` for reminders

### Production Deployment
- Deploy both files to a server (Render, Heroku, etc.)
- Set environment variables
- Keep both processes running

---

## Troubleshooting

- **Bot not responding**: Check TELEGRAM_BOT_TOKEN
- **AI not working**: Check GEMINI_API_KEY
- **Database errors**: Check Supabase credentials
- **No reminders**: Ensure scheduler is running

---

## Credits
Built with:
- **Telegram Bot API** - Messaging platform
- **Google Gemini AI** - Natural language processing
- **Supabase** - Database storage
- **Python** - Backend logic 