import os
import json
import uuid
import asyncio
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_IDS = [5145474067]  # ❗СВОЙ ID
DATA_FILE = "applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"  # ❗СВОЙ URL

# ========== ХРАНИЛИЩЕ ==========
def load_json(filename, default=None):
    if default is None:
        default = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== FLASK ==========
app = Flask(__name__)
telegram_app = None

@app.route("/")
def home():
    return "✅ Бот работает! Webhook активен."

@app.route("/telegram", methods=["POST"])
async def telegram_webhook():
    global telegram_app
    if telegram_app:
        data = request.get_json(force=True)
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    return "ok"

@app.route("/webhook", methods=["POST"])
def formspree_webhook():
    global telegram_app
    data = request.get_json(force=True) if request.is_json else request.form
    
    code = data.get("verification_code", "").strip().upper()
    pending_codes = load_json(PENDING_CODES_FILE)
    
    if not code or code not in pending_codes:
        return jsonify({"error": "Неверный код подтверждения"}), 400
    
    chat_id = pending_codes.pop(code)
    save_json(PENDING_CODES_FILE, pending_codes)
    
    real_name = data.get("real_name", "Игрок")
    minecraft_nick = data.get("minecraft_nick", "")
    telegram_user = data.get("telegram", "")
    experience = data.get("experience", "")
    motivation = data.get("motivation", "")
    
    applications = load_json(DATA_FILE, [])
    
    new_app = {
        "id": len(applications) + 1,
        "chat_id": chat_id,
        "real_name": real_name,
        "minecraft_nick": minecraft_nick,
        "telegram_user": telegram_user,
        "experience": experience,
        "motivation": motivation,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    
    applications.append(new_app)
    save_json(DATA_FILE, applications)
    
    if telegram_app and telegram_app.bot:
        try:
            asyncio.new_event_loop().run_until_complete(
                telegram_app.bot.send_message(
                    chat_id=chat_id,
                    text=f"Привет {real_name}! Твоя заявка рассмотрится в течении недели. Ожидай."
                )
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
        
        for admin_id in ADMIN_IDS:
            try:
                asyncio.new_event_loop().run_until_complete(
                    telegram_app.bot.send_message(
                        chat_id=admin_id,
                        text=f"🆕 Новая заявка #{new_app['id']} от {real_name}\nНик: {minecraft_nick}\nTG: @{telegram_user}"
                    )
                )
            except:
                pass
    
    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ========== TELEGRAM BOT ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    
    pending_codes = load_json(PENDING_CODES_FILE)
    pending_codes[code] = chat_id
    save_json(PENDING_CODES_FILE, pending_codes)
    
    await update.message.reply_text(
        f"🌲 Привет! Добро пожаловать в FoggyLand!\n\n"
        f"Твой код подтверждения: `{code}`\n\n"
        f"Скопируй его и вставь в форму заявки.",
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Все заявки", callback_data="list_all")],
        [InlineKeyboardButton("⏳ Ожидающие", callback_data="list_pending")],
        [InlineKeyboardButton("✅ Принятые", callback_data="list_accepted")]
    ]
    
    await update.message.reply_text(
        "🎛 Админ-панель FoggyLand",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Нет доступа.")
        return
    
    applications = load_json(DATA_FILE, [])
    
    if query.data == "list_all":
        await show_list(query, applications)
    elif query.data == "list_pending":
        await show_list(query, [a for a in applications if a["status"] == "pending"])
    elif query.data == "list_accepted":
        await show_list(query, [a for a in applications if a["status"] == "accepted"])
    elif query.data.startswith("view_"):
        app_id = int(query.data.split("_")[1])
        app_data = next((a for a in applications if a["id"] == app_id), None)
        if app_data:
            await show_detail(query, app_data)
    elif query.data.startswith("accept_"):
        app_id = int(query.data.split("_")[1])
        await accept_app(query, app_id, applications)
    elif query.data == "back_to_admin":
        keyboard = [
            [InlineKeyboardButton("📋 Все заявки", callback_data="list_all")],
            [InlineKeyboardButton("⏳ Ожидающие", callback_data="list_pending")],
            [InlineKeyboardButton("✅ Принятые", callback_data="list_accepted")]
        ]
        await query.edit_message_text("🎛 Админ-панель", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_list(query, apps):
    if not apps:
        await query.edit_message_text("📭 Заявок нет.")
        return
    
    text = "📊 Заявки:\n\n"
    keyboard = []
    
    for app_data in apps[:10]:
        emoji = "✅" if app_data["status"] == "accepted" else "⏳"
        text += f"{emoji} #{app_data['id']} | {app_data['real_name']} | {app_data['minecraft_nick']}\n"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} #{app_data['id']} - {app_data['real_name']}",
            callback_data=f"view_{app_data['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_detail(query, app_data):
    text = (
        f"📝 Заявка #{app_data['id']}\n\n"
        f"👤 Имя: {app_data['real_name']}\n"
        f"⛏ Ник: {app_data['minecraft_nick']}\n"
        f"📬 Telegram: {app_data.get('telegram_user', '-')}\n"
        f"📊 Статус: {'✅ Принята' if app_data['status'] == 'accepted' else '⏳ Ожидает'}"
    )
    
    keyboard = []
    if app_data["status"] == "pending":
        keyboard.append([InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_{app_data['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="list_pending")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def accept_app(query, app_id, applications):
    app_data = next((a for a in applications if a["id"] == app_id), None)
    if not app_data or app_data["status"] != "pending":
        await query.edit_message_text("❌ Не найдена.")
        return
    
    app_data["status"] = "accepted"
    save_json(DATA_FILE, applications)
    
    try:
        await query.bot.send_message(
            chat_id=app_data["chat_id"],
            text=f"Привет {app_data['real_name']}!\nТвоя заявка на модератора была принята!\nИ твоего модератора уже выдали!\nВаш ник: {app_data['minecraft_nick']}"
        )
        await query.edit_message_text(f"✅ Заявка #{app_id} принята!")
    except Exception as e:
        await query.edit_message_text(f"⚠️ Ошибка: {e}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Устанавливаем webhook через urllib (встроенная библиотека)
    import urllib.request
    webhook_url = f"{RENDER_URL}/telegram"
    set_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}"
    
    try:
        with urllib.request.urlopen(set_url) as response:
            print(f"🔗 Webhook установлен: {response.read().decode()}")
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")

    # Создаём приложение Telegram
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("admin", admin_panel))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    
    loop.run_until_complete(telegram_app.initialize())
    
    print("✅ Бот готов к работе!")
    
    # Запускаем Flask
    app.run(host="0.0.0.0", port=PORT)
