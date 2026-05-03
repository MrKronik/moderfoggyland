import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_IDS = [5145474067]  # ❗ ЗАМЕНИ НА СВОЙ ID
DATA_FILE = "applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))
# URL твоего сервера на Render (подставь свой, если отличается)
RENDER_URL = "https://moderfoggyland.onrender.com"

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
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@app.route("/")
def home():
    return "✅ Бот работает! Вебхуки активны."

# Маршрут для Formspree (приём заявок)
@app.route("/webhook", methods=["POST"])
def formspree_webhook():
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
    attitude = data.get("attitude_to_cheats", "")

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
        "attitude_to_cheats": attitude,
    }

    applications.append(new_app)
    save_json(DATA_FILE, applications)

    # Сообщение заявителю
    try:
        bot.send_message(chat_id,
                         f"Привет {real_name}! Твоя заявка рассмотрится в течении недели. Ожидай.")
    except Exception as e:
        print(f"Ошибка отправки заявителю: {e}")

    # Сообщение админам
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id,
                             f"🆕 Новая заявка #{new_app['id']} от {real_name}\n"
                             f"Ник: {minecraft_nick}\nTG: @{telegram_user}")
        except:
            pass

    return jsonify({"status": "ok", "app_id": new_app["id"]})

# Маршрут для Telegram (приём команд)
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    else:
        return "Bad request", 400

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    pending_codes = load_json(PENDING_CODES_FILE)
    pending_codes[code] = chat_id
    save_json(PENDING_CODES_FILE, pending_codes)

    bot.reply_to(message,
                 f"🌲 Привет! Добро пожаловать в FoggyLand!\n\n"
                 f"Твой код подтверждения: `{code}`\n\n"
                 f"Скопируй его и вставь в форму заявки.",
                 parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа.")
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📋 Все заявки", callback_data="list_all"),
        types.InlineKeyboardButton("⏳ Ожидающие", callback_data="list_pending"),
        types.InlineKeyboardButton("✅ Принятые", callback_data="list_accepted")
    )
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    applications = load_json(DATA_FILE, [])

    if call.data == "list_all":
        show_list(call, applications)
    elif call.data == "list_pending":
        show_list(call, [a for a in applications if a["status"] == "pending"])
    elif call.data == "list_accepted":
        show_list(call, [a for a in applications if a["status"] == "accepted"])
    elif call.data.startswith("view_"):
        app_id = int(call.data.split("_")[1])
        app_data = next((a for a in applications if a["id"] == app_id), None)
        if app_data:
            show_detail(call, app_data)
    elif call.data.startswith("accept_"):
        app_id = int(call.data.split("_")[1])
        accept_app(call, app_id, applications)
    elif call.data == "back_to_admin":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("📋 Все заявки", callback_data="list_all"),
            types.InlineKeyboardButton("⏳ Ожидающие", callback_data="list_pending"),
            types.InlineKeyboardButton("✅ Принятые", callback_data="list_accepted")
        )
        bot.edit_message_text("🎛 Админ-панель", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_list(call, apps):
    if not apps:
        bot.edit_message_text("📭 Заявок нет.", call.message.chat.id, call.message.message_id)
        return

    text = "📊 Заявки:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for app_data in apps[:10]:
        emoji = "✅" if app_data["status"] == "accepted" else "⏳"
        text += f"{emoji} #{app_data['id']} | {app_data['real_name']} | {app_data['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{app_data['id']} - {app_data['real_name']}",
            callback_data=f"view_{app_data['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_detail(call, app_data):
    text = (
        f"📝 Заявка #{app_data['id']}\n\n"
        f"👤 Имя: {app_data['real_name']}\n"
        f"⛏ Ник: {app_data['minecraft_nick']}\n"
        f"📬 Telegram: {app_data.get('telegram_user', '-')}\n"
        f"📅 Дата: {app_data.get('submitted_at', '-')[:10]}\n"
        f"📊 Статус: {'✅ Принята' if app_data['status'] == 'accepted' else '⏳ Ожидает'}\n\n"
        f"🛡 Опыт: {app_data.get('experience', '-')}\n"
        f"💬 Мотивация: {app_data.get('motivation', '-')}"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    if app_data["status"] == "pending":
        keyboard.add(types.InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_{app_data['id']}"))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="list_pending"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def accept_app(call, app_id, applications):
    app_data = next((a for a in applications if a["id"] == app_id), None)
    if not app_data or app_data["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return

    app_data["status"] = "accepted"
    save_json(DATA_FILE, applications)

    try:
        bot.send_message(app_data["chat_id"],
                         f"Привет {app_data['real_name']}!\n"
                         f"Твоя заявка на модератора была принята!\n"
                         f"И твоего модератора уже выдали!\n"
                         f"Ваш ник: {app_data['minecraft_nick']}")
        bot.edit_message_text(f"✅ Заявка #{app_id} принята! Уведомление отправлено.",
                              call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"✅ Заявка #{app_id} принята!\n⚠️ Ошибка отправки: {e}",
                              call.message.chat.id, call.message.message_id)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # 1. Удаляем все прошлые вебхуки
    try:
        bot.remove_webhook()
        print("🧹 Старый webhook удалён")
    except Exception as e:
        print(f"⚠️ Не удалось удалить webhook: {e}")

    # 2. Ставим новый вебхук на /telegram
    webhook_url = f"{RENDER_URL}/telegram"
    try:
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен на {webhook_url}")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

    # 3. Запуск Flask (без polling!)
    app.run(host="0.0.0.0", port=PORT)
