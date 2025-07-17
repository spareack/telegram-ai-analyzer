# Telegram Chat Analyzer Bot

A Telegram bot that answers questions about group chat history using OpenAI Assistants API.

---

## 🤖 Creating and setting up your bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token — you’ll need it for deployment
4. Send `/setprivacy` to BotFather and **disable privacy** for the bot  
   (this allows it to see messages in groups)
5. Add your bot to the desired **Telegram group**
6. Grant the bot the **“Read all messages”** permission

---

## 💬 Exporting Telegram Chat(s)

> 🟡 Telegram bots cannot read **messages sent before they were added** to a group.  
> So the first time, you must export the history manually.

1. Open **Telegram Desktop**
2. Go to a group → ⋮ → **Export chat history**
3. Choose:
   - ✅ Text only
   - ✅ Entire history
   - ✅ Export as **JSON**
4. Put one or multiple `result.json` files into the `raw_chats/` folder

---

## 🔄 Importing exported chats

At container startup, all JSON files in `raw_chats/` will be:
- Automatically converted to `chat_<id>.txt` in `converted_chats/`
- Deleted after successful import

You can place many files at once.

---

## 🚀 Running the bot with Docker

```bash
docker compose up --build -d
```

---

## 🧠 How to use the bot

In your Telegram group:

- Mention the bot in a message:  
  `@YourBotName Describe each person in chat`
- Or use the same as `/ask` command:  
  `/ask Who suggested to play Minecraft?`

---

## 📌 About the assistant's knowledge

The bot uses a **cached uploaded version** of the chat history.  
New messages sent after that will be **saved automatically**,  
but will not be included in the assistant's answers **until you run:**

```
/refresh
```

This will re-upload the updated chat history and replace the cached version.
