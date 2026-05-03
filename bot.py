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
DATA_FILE = "applications.json"           # заявки на модератора
ADMIN_APPS_FILE = "admin_applications.json"  # заявки на администратора
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))
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
CORS(app)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@app.route("/")
def home():
    return "✅ Бот работает!"

# ----- Приём заявки на модератора -----
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
    motivation = data.get("motivation", "")
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
        "attitude_to_cheats": attitude,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    applications.append(new_app)
    save_json(DATA_FILE, applications)

    # Уведомления
    try:
        bot.send_message(chat_id,
                         f"Привет {real_name}! Твоя заявка рассмотрится в течении недели. Ожидай.")
    except Exception as e:
        print(f"Ошибка отправки заявителю: {e}")

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id,
                             f"🆕 Новая заявка #{new_app['id']} от {real_name}\n"
                             f"Ник: {minecraft_nick}\nTG: @{telegram_user}")
        except:
            pass

    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ----- Приём заявки на администратора -----
@app.route("/admin-webhook", methods=["POST"])
def admin_application_webhook():
    data = request.get_json(force=True) if request.is_json else request.form
    code = data.get("verification_code", "").strip().upper()
    pending_codes = load_json(PENDING_CODES_FILE)
    if not code or code not in pending_codes:
        return jsonify({"error": "Неверный код подтверждения"}), 400

    chat_id = pending_codes.pop(code)
    save_json(PENDING_CODES_FILE, pending_codes)

    full_name = data.get("fullName", "Игрок")
    nick = data.get("minecraftNick", "")
    telegram_user = data.get("telegram", "")
    # Сохраняем все поля (можно выборочно, но пусть будут все)
    admin_apps = load_json(ADMIN_APPS_FILE, [])
    new_app = {
        "id": len(admin_apps) + 1,
        "chat_id": chat_id,
        "full_name": full_name,
        "minecraft_nick": nick,
        "telegram_user": telegram_user,
        "age": data.get("age", ""),
        "timezone": data.get("timezone", ""),
        "modDuration": data.get("modDuration", ""),
        "modTasks": data.get("modTasks", ""),
        "activityHours": data.get("activityHours", ""),
        "rule_q1": data.get("rule_q1", ""),
        "rule_q2": data.get("rule_q2", ""),
        "rule_q3": data.get("rule_q3", ""),
        "rule_q4": data.get("rule_q4", ""),
        "rule_q5": data.get("rule_q5", ""),
        "rule_q6": data.get("rule_q6", ""),
        "rule_q7": data.get("rule_q7", ""),
        "rule_q8": data.get("rule_q8", ""),
        "rule_q9": data.get("rule_q9", ""),
        "rule_q10": data.get("rule_q10", ""),
        "rule_q11": data.get("rule_q11", ""),
        "rule_q12": data.get("rule_q12", ""),
        "techSkills": data.get("techSkills", ""),
        "logAnalysis": data.get("logAnalysis", ""),
        "teamManagement": data.get("teamManagement", ""),
        "situation1": data.get("situation1", ""),
        "situation2": data.get("situation2", ""),
        "situation3": data.get("situation3", ""),
        "situation4": data.get("situation4", ""),
        "punishmentStyle": data.get("punishmentStyle", ""),
        "motivation": data.get("motivation", ""),
        "suggestions": data.get("suggestions", ""),
        "commitment": data.get("commitment", ""),
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    admin_apps.append(new_app)
    save_json(ADMIN_APPS_FILE, admin_apps)

    try:
        bot.send_message(chat_id,
                         f"Привет {full_name}! Твоя заявка на администратора принята и будет рассмотрена в течение 5-7 дней. Ожидай.")
    except Exception as e:
        print(f"Ошибка отправки заявителю: {e}")

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id,
                             f"🆕 Заявка на администратора #{new_app['id']} от {full_name}\n"
                             f"Ник: {nick}\nTG: @{telegram_user}")
        except:
            pass

    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ----- Telegram вебхук (приём команд) -----
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
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
        types.InlineKeyboardButton("📋 Все заявки (модер)", callback_data="list_all"),
        types.InlineKeyboardButton("⏳ Ожидающие (модер)", callback_data="list_pending"),
        types.InlineKeyboardButton("✅ Принятые (модер)", callback_data="list_accepted"),
        types.InlineKeyboardButton("❌ Отклонённые (модер)", callback_data="list_rejected"),
        types.InlineKeyboardButton("👑 Админ-заявки", callback_data="list_admin_apps")
    )
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    # Модераторские заявки
    if call.data in ("list_all", "list_pending", "list_accepted", "list_rejected"):
        applications = load_json(DATA_FILE, [])
        if call.data == "list_all":
            show_list(call, applications, "mod")
        elif call.data == "list_pending":
            show_list(call, [a for a in applications if a["status"] == "pending"], "mod")
        elif call.data == "list_accepted":
            show_list(call, [a for a in applications if a["status"] == "accepted"], "mod")
        elif call.data == "list_rejected":
            show_list(call, [a for a in applications if a["status"] == "rejected"], "mod")
        return

    if call.data.startswith("view_"):
        app_id = int(call.data.split("_")[1])
        applications = load_json(DATA_FILE, [])
        app_data = next((a for a in applications if a["id"] == app_id), None)
        if app_data:
            show_detail(call, app_data)
        return

    if call.data.startswith("accept_"):
        app_id = int(call.data.split("_")[1])
        applications = load_json(DATA_FILE, [])
        accept_app(call, app_id, applications)
        return

    if call.data.startswith("reject_"):
        app_id = int(call.data.split("_")[1])
        applications = load_json(DATA_FILE, [])
        reject_app(call, app_id, applications)
        return

    # Админские заявки
    if call.data == "list_admin_apps":
        admin_apps = load_json(ADMIN_APPS_FILE, [])
        show_admin_list(call, admin_apps)
        return

    if call.data.startswith("admin_view_"):
        app_id = int(call.data.split("_")[2])
        admin_apps = load_json(ADMIN_APPS_FILE, [])
        app_data = next((a for a in admin_apps if a["id"] == app_id), None)
        if app_data:
            show_admin_detail(call, app_data)
        return

    if call.data.startswith("admin_accept_"):
        app_id = int(call.data.split("_")[2])
        admin_apps = load_json(ADMIN_APPS_FILE, [])
        accept_admin_app(call, app_id, admin_apps)
        return

    if call.data.startswith("admin_reject_"):
        app_id = int(call.data.split("_")[2])
        admin_apps = load_json(ADMIN_APPS_FILE, [])
        reject_admin_app(call, app_id, admin_apps)
        return

    if call.data == "back_to_admin":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("📋 Все заявки (модер)", callback_data="list_all"),
            types.InlineKeyboardButton("⏳ Ожидающие (модер)", callback_data="list_pending"),
            types.InlineKeyboardButton("✅ Принятые (модер)", callback_data="list_accepted"),
            types.InlineKeyboardButton("❌ Отклонённые (модер)", callback_data="list_rejected"),
            types.InlineKeyboardButton("👑 Админ-заявки", callback_data="list_admin_apps")
        )
        bot.edit_message_text("🎛 Админ-панель", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# ----- Общие функции отображения для модераторских заявок -----
def show_list(call, apps, app_type="mod"):
    if not apps:
        bot.edit_message_text("📭 Заявок нет.", call.message.chat.id, call.message.message_id)
        return
    text = "📊 Заявки:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        if a["status"] == "accepted":
            emoji = "✅"
        elif a["status"] == "rejected":
            emoji = "❌"
        else:
            emoji = "⏳"
        name = a.get("real_name", a.get("full_name", "—"))
        nick = a.get("minecraft_nick", "")
        text += f"{emoji} #{a['id']} | {name} | {nick}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{a['id']} - {name}",
            callback_data=f"view_{a['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_detail(call, app):
    status_text = "⏳ Ожидает"
    if app["status"] == "accepted":
        status_text = "✅ Принята"
    elif app["status"] == "rejected":
        status_text = "❌ Отклонена"

    text = (
        f"📝 Заявка #{app['id']}\n\n"
        f"👤 Имя: {app.get('real_name', '—')}\n"
        f"⛏ Ник: {app.get('minecraft_nick', '—')}\n"
        f"📬 Telegram: {app.get('telegram_user', '—')}\n"
        f"📅 Дата: {app.get('submitted_at', '—')[:10]}\n"
        f"📊 Статус: {status_text}\n"
        f"🚫 Отношение к читу: {app.get('attitude_to_cheats', '—')}\n"
        f"🛡 Опыт: {app.get('experience', '—')}\n"
        f"💬 Мотивация: {app.get('motivation', '—')}"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if app["status"] == "pending":
        keyboard.add(
            types.InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"accept_{app['id']}"),
            types.InlineKeyboardButton("❌ ОТКАЗАТЬ", callback_data=f"reject_{app['id']}")
        )
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="list_pending"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def accept_app(call, app_id, applications):
    app = next((a for a in applications if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "accepted"
    save_json(DATA_FILE, applications)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['real_name']}!\nТвоя заявка на модератора была принята!\nИ твоего модератора уже выдали!\nВаш ник: {app['minecraft_nick']}")
        bot.edit_message_text(f"✅ Заявка #{app_id} принята! Уведомление отправлено.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"✅ Заявка #{app_id} принята!\n⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)

def reject_app(call, app_id, applications):
    app = next((a for a in applications if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "rejected"
    save_json(DATA_FILE, applications)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['real_name']}! К сожалению твоя заявка не прошла проверку. Можешь отправить заявку повторно через 2-7 дней. Ваш ник: {app['minecraft_nick']}")
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена! Уведомление отправлено.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена!\n⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)

# ----- Функции для админских заявок -----
def show_admin_list(call, apps):
    if not apps:
        bot.edit_message_text("📭 Админ-заявок нет.", call.message.chat.id, call.message.message_id)
        return
    text = "👑 Заявки на администратора:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        if a["status"] == "accepted":
            emoji = "✅"
        elif a["status"] == "rejected":
            emoji = "❌"
        else:
            emoji = "⏳"
        text += f"{emoji} #{a['id']} | {a['full_name']} | {a['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{a['id']} - {a['full_name']}",
            callback_data=f"admin_view_{a['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_admin_detail(call, app):
    status_text = "⏳ Ожидает"
    if app["status"] == "accepted":
        status_text = "✅ Принята"
    elif app["status"] == "rejected":
        status_text = "❌ Отклонена"
    text = (
        f"👑 Заявка на админа #{app['id']}\n"
        f"👤 {app['full_name']}\n"
        f"⛏ Ник: {app['minecraft_nick']}\n"
        f"📬 Telegram: @{app.get('telegram_user', '')}\n"
        f"📊 Статус: {status_text}\n"
        f"💬 Мотивация: {app.get('motivation', '—')}"
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
        bot.edit_message_text("❌ Заявка не найдена.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "accepted"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['full_name']}!\nТвоя заявка на администратора одобрена! Поздравляем!")
        bot.edit_message_text(f"✅ Заявка #{app_id} одобрена.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)

def reject_admin_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "rejected"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['full_name']}. К сожалению, твоя заявка на администратора не прошла. Ты можешь подать повторно через 2 недели.")
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("🧹 Старый webhook удалён")
    except Exception as e:
        print(f"⚠️ Ошибка при удалении webhook: {e}")

    webhook_url = f"{RENDER_URL}/telegram"
    try:
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен на {webhook_url}")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

    app.run(host="0.0.0.0", port=PORT)
