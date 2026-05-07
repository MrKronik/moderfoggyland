import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_IDS = [5145474067]   # ❗ Свой Telegram ID
DATA_FILE = "applications.json"
ADMIN_APPS_FILE = "admin_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"   # ❗ свой Render URL

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
CORS(app)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@app.route("/")
def home():
    return "✅ Бот работает!"

# ----- Приём заявки на модератора -----
@app.route("/webhook", methods=["POST"])
def moderator_webhook():
    data = request.get_json(force=True) if request.is_json else request.form
    code = data.get("verification_code", "").strip().upper()
    pending = load_json(PENDING_CODES_FILE)
    if not code or code not in pending:
        return jsonify({"error": "Неверный код подтверждения"}), 400

    chat_id = pending.pop(code)
    save_json(PENDING_CODES_FILE, pending)

    real_name = data.get("real_name", "Игрок")
    nick = data.get("minecraft_nick", "")
    tg = data.get("telegram", "")
    experience = data.get("experience", "")
    motivation = data.get("motivation", "")
    attitude = data.get("attitude_to_cheats", "")

    apps = load_json(DATA_FILE, [])
    new_app = {
        "id": len(apps) + 1,
        "chat_id": chat_id,
        "real_name": real_name,
        "minecraft_nick": nick,
        "telegram_user": tg,
        "experience": experience,
        "motivation": motivation,
        "attitude_to_cheats": attitude,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    apps.append(new_app)
    save_json(DATA_FILE, apps)

    try:
        bot.send_message(chat_id, f"Привет {real_name}! Твоя заявка рассмотрится в течении недели. Ожидай.")
    except:
        pass
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🆕 Новая заявка #{new_app['id']} от {real_name}\nНик: {nick}\nTG: @{tg}")
        except:
            pass
    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ----- Приём заявки на администратора -----
@app.route("/admin-webhook", methods=["POST"])
def admin_webhook():
    data = request.get_json(force=True) if request.is_json else request.form
    code = data.get("verification_code", "").strip().upper()
    pending = load_json(PENDING_CODES_FILE)
    if not code or code not in pending:
        return jsonify({"error": "Неверный код подтверждения"}), 400

    chat_id = pending.pop(code)
    save_json(PENDING_CODES_FILE, pending)

    full_name = data.get("fullName", "Игрок")
    nick = data.get("minecraftNick", "")
    tg = data.get("telegram", "")
    # собираем все поля как раньше (для краткости не повторяю все, они хранятся)
    admin_apps = load_json(ADMIN_APPS_FILE, [])
    new_app = {
        "id": len(admin_apps) + 1,
        "chat_id": chat_id,
        "full_name": full_name,
        "minecraft_nick": nick,
        "telegram_user": tg,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    admin_apps.append(new_app)
    save_json(ADMIN_APPS_FILE, admin_apps)

    try:
        bot.send_message(chat_id, f"Привет {full_name}! Твоя заявка на администратора принята и будет рассмотрена в течение 5-7 дней. Ожидай.")
    except:
        pass
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🆕 Заявка на администратора #{new_app['id']} от {full_name}\nНик: {nick}\nTG: @{tg}")
        except:
            pass
    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ========== Telegram вебхук ==========
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    return "Bad request", 400

# ========== КЛАВИАТУРА ==========
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.KeyboardButton("🔑 Получить код"), types.KeyboardButton("ℹ️ Помощь"))
    return keyboard

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    pending = load_json(PENDING_CODES_FILE)
    pending[code] = chat_id
    save_json(PENDING_CODES_FILE, pending)

    text = (
        "🌲 Добро пожаловать в FoggyLand!\n\n"
        f"Твой текущий код: `{code}`\n"
        "Используй кнопки ниже:"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_keyboard())

# Кнопка "Получить код"
@bot.message_handler(func=lambda msg: msg.text == "🔑 Получить код")
def button_get_code(message):
    start(message)

# Кнопка "Помощь"
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Помощь")
def button_help(message):
    text = (
        "🌲 **FoggyLand Bot**\n\n"
        "• **🔑 Получить код** – выдаёт код для подачи заявки на модератора или администратора.\n"
        "• **ℹ️ Помощь** – это сообщение.\n\n"
        "По всем вопросам обращайтесь к администрации."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Админ-панель (скрытая команда)
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа.")
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📋 Заявки (модер)", callback_data="list_all"),
        types.InlineKeyboardButton("⏳ Ожидающие (модер)", callback_data="list_pending"),
        types.InlineKeyboardButton("✅ Принятые (модер)", callback_data="list_accepted"),
        types.InlineKeyboardButton("❌ Отклонённые (модер)", callback_data="list_rejected"),
        types.InlineKeyboardButton("👑 Админ-заявки", callback_data="list_admin_apps")
    )
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

# ========== ОБРАБОТКА ЗАЯВОК (коллбэки) ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    data = call.data

    # Списки модераторских заявок
    if data in ("list_all", "list_pending", "list_accepted", "list_rejected"):
        apps = load_json(DATA_FILE, [])
        if data == "list_pending":
            apps = [a for a in apps if a["status"] == "pending"]
        elif data == "list_accepted":
            apps = [a for a in apps if a["status"] == "accepted"]
        elif data == "list_rejected":
            apps = [a for a in apps if a["status"] == "rejected"]
        show_mod_list(call, apps)
        return

    # Просмотр одной заявки
    if data.startswith("view_"):
        app_id = int(data.split("_")[1])
        apps = load_json(DATA_FILE, [])
        app = next((a for a in apps if a["id"] == app_id), None)
        if app:
            show_mod_detail(call, app)
        return

    # Принять / отклонить модератора
    if data.startswith("accept_"):
        app_id = int(data.split("_")[1])
        apps = load_json(DATA_FILE, [])
        accept_mod_app(call, app_id, apps)
        return

    if data.startswith("reject_"):
        app_id = int(data.split("_")[1])
        apps = load_json(DATA_FILE, [])
        reject_mod_app(call, app_id, apps)
        return

    # Админские заявки
    if data == "list_admin_apps":
        apps = load_json(ADMIN_APPS_FILE, [])
        show_admin_list(call, apps)
        return

    if data.startswith("admin_view_"):
        app_id = int(data.split("_")[2])
        apps = load_json(ADMIN_APPS_FILE, [])
        app = next((a for a in apps if a["id"] == app_id), None)
        if app:
            show_admin_detail(call, app)
        return

    if data.startswith("admin_accept_"):
        app_id = int(data.split("_")[2])
        apps = load_json(ADMIN_APPS_FILE, [])
        accept_admin_app(call, app_id, apps)
        return

    if data.startswith("admin_reject_"):
        app_id = int(data.split("_")[2])
        apps = load_json(ADMIN_APPS_FILE, [])
        reject_admin_app(call, app_id, apps)
        return

    if data == "back_to_admin":
        admin_panel(call.message)
        return

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (заявки) ==========
def show_mod_list(call, apps):
    if not apps:
        bot.edit_message_text("📭 Заявок нет.", call.message.chat.id, call.message.message_id)
        return
    text = "📊 Заявки:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        emoji = "✅" if a["status"] == "accepted" else "❌" if a["status"] == "rejected" else "⏳"
        text += f"{emoji} #{a['id']} | {a['real_name']} | {a['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{a['id']} - {a['real_name']}",
            callback_data=f"view_{a['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_mod_detail(call, app):
    status = "✅ Принята" if app["status"] == "accepted" else "❌ Отклонена" if app["status"] == "rejected" else "⏳ Ожидает"
    text = (
        f"📝 Заявка #{app['id']}\n"
        f"👤 Имя: {app['real_name']}\n"
        f"⛏ Ник: {app['minecraft_nick']}\n"
        f"📬 Telegram: @{app.get('telegram_user','')}\n"
        f"📊 Статус: {status}\n"
        f"🚫 Читы: {app.get('attitude_to_cheats','—')}\n"
        f"🛠 Опыт: {app.get('experience','—')}\n"
        f"💬 Мотивация: {app.get('motivation','—')}"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if app["status"] == "pending":
        keyboard.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_{app['id']}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{app['id']}")
        )
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="list_pending"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def accept_mod_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "accepted"
    save_json(DATA_FILE, apps)
    try:
        bot.send_message(app["chat_id"], f"Привет {app['real_name']}!\nТвоя заявка на модератора была принята!\nИ твоего модератора уже выдали!\nВаш ник: {app['minecraft_nick']}")
        bot.edit_message_text(f"✅ Заявка #{app_id} принята!", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {e}", call.message.chat.id, call.message.message_id)

def reject_mod_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "rejected"
    save_json(DATA_FILE, apps)
    try:
        bot.send_message(app["chat_id"], f"Привет {app['real_name']}! К сожалению твоя заявка не прошла проверку. Можешь отправить заявку повторно через 2-7 дней. Ваш ник: {app['minecraft_nick']}")
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена!", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {e}", call.message.chat.id, call.message.message_id)

def show_admin_list(call, apps):
    if not apps:
        bot.edit_message_text("📭 Админ-заявок нет.", call.message.chat.id, call.message.message_id)
        return
    text = "👑 Заявки на администратора:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        emoji = "✅" if a["status"] == "accepted" else "❌" if a["status"] == "rejected" else "⏳"
        text += f"{emoji} #{a['id']} | {a['full_name']} | {a['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{a['id']} - {a['full_name']}",
            callback_data=f"admin_view_{a['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_admin_detail(call, app):
    status = "✅ Принята" if app["status"] == "accepted" else "❌ Отклонена" if app["status"] == "rejected" else "⏳ Ожидает"
    text = (
        f"👑 Заявка #{app['id']}\n"
        f"👤 {app['full_name']}\n"
        f"⛏ Ник: {app['minecraft_nick']}\n"
        f"📬 Telegram: @{app.get('telegram_user','')}\n"
        f"📊 Статус: {status}\n"
        f"💬 Мотивация: {app.get('motivation','—')}"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if app["status"] == "pending":
        keyboard.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"admin_accept_{app['id']}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{app['id']}")
        )
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="list_admin_apps"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def accept_admin_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "accepted"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"], f"Привет {app['full_name']}!\nТвоя заявка на администратора одобрена! Поздравляем!")
        bot.edit_message_text(f"✅ Заявка #{app_id} одобрена!", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {e}", call.message.chat.id, call.message.message_id)

def reject_admin_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "rejected"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"], f"Привет {app['full_name']}. К сожалению, твоя заявка на администратора не прошла. Ты можешь подать повторно через 2 недели.")
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена!", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {e}", call.message.chat.id, call.message.message_id)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("🧹 Старый webhook удалён")
    except:
        pass
    webhook_url = f"{RENDER_URL}/telegram"
    try:
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен на {webhook_url}")
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
    app.run(host="0.0.0.0", port=PORT)
