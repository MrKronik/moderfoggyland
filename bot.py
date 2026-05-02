import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8694410683:AAHDkj6SfiZF1PY5dr3Ahc97jNxEnIkWZkY")
ADMIN_IDS = [5145474067]  # ❗Замени на свой Telegram ID (узнать в @userinfobot)
DATA_FILE = "applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))

# ========== ХРАНИЛИЩЕ ==========
def load_json(filename, default={}):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== FLASK ДЛЯ ВЕБХУКОВ ==========
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "FoggyLand Bot is running!"

@app.route("/webhook", methods=["POST"])
def formspree_webhook():
    """Принимает заявки от Formspree"""
    data = request.get_json(force=True) if request.is_json else request.form
    
    # Проверяем код подтверждения
    code = data.get("verification_code", "").strip().upper()
    pending_codes = load_json(PENDING_CODES_FILE)
    
    if not code or code not in pending_codes:
        return jsonify({"error": "Неверный код подтверждения"}), 400
    
    chat_id = pending_codes.pop(code)
    save_json(PENDING_CODES_FILE, pending_codes)
    
    # Собираем заявку
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
    
    # Отправляем подтверждение заявителю
    try:
        application.bot.send_message(
            chat_id=chat_id,
            text=f"Привет {real_name}! Твоя заявка рассмотрится в течении недели. Ожидай."
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")
    
    # Уведомляем всех админов
    for admin_id in ADMIN_IDS:
        try:
            keyboard = [[InlineKeyboardButton("📋 Просмотреть заявки", callback_data="list_apps")]]
            application.bot.send_message(
                chat_id=admin_id,
                text=f"🆕 Новая заявка #{new_app['id']} от {real_name} (@{telegram_user})\n"
                     f"Ник: {minecraft_nick}\n"
                     f"Опыт: {experience[:100]}...",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass
    
    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ========== TELEGRAM БОТ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдача кода подтверждения"""
    chat_id = update.effective_chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    
    pending_codes = load_json(PENDING_CODES_FILE)
    pending_codes[code] = chat_id
    save_json(PENDING_CODES_FILE, pending_codes)
    
    await update.message.reply_text(
        f"🌲 Привет! Добро пожаловать в FoggyLand!\n\n"
        f"Твой код подтверждения: `{code}`\n\n"
        f"Скопируй его и вставь в форму заявки на сайте: https://твой-никнейм.github.io/foggymod/\n\n"
        f"После отправки заявки ты получишь уведомление здесь.",
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель (только для админов)"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к админ-панели.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Все заявки", callback_data="list_apps")],
        [InlineKeyboardButton("⏳ Ожидающие", callback_data="list_pending")],
        [InlineKeyboardButton("✅ Принятые", callback_data="list_accepted")]
    ]
    
    await update.message.reply_text(
        "🎛 Админ-панель FoggyLand\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Нет доступа.")
        return
    
    applications = load_json(DATA_FILE, [])
    
    if query.data == "list_apps":
        await show_applications(query, applications, "all")
    
    elif query.data == "list_pending":
        pending = [a for a in applications if a["status"] == "pending"]
        await show_applications(query, pending, "pending")
    
    elif query.data == "list_accepted":
        accepted = [a for a in applications if a["status"] == "accepted"]
        await show_applications(query, accepted, "accepted")
    
    elif query.data.startswith("view_"):
        app_id = int(query.data.split("_")[1])
        app = next((a for a in applications if a["id"] == app_id), None)
        if app:
            await show_application_detail(query, app)
    
    elif query.data.startswith("accept_"):
        app_id = int(query.data.split("_")[1])
        await accept_application(query, app_id, applications)

async def show_applications(query, apps, filter_type):
    """Показывает список заявок"""
    if not apps:
        await query.edit_message_text("📭 Заявок нет.", reply_markup=back_button())
        return
    
    text = f"📊 Заявки ({filter_type}):\n\n"
    keyboard = []
    
    for app in apps[:10]:  # Показываем первые 10
        status_emoji = "✅" if app["status"] == "accepted" else "⏳"
        text += f"{status_emoji} #{app['id']} | {app['real_name']} | {app['minecraft_nick']}\n"
        keyboard.append([InlineKeyboardButton(
            f"{status_emoji} #{app['id']} - {app['real_name']}",
            callback_data=f"view_{app['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")])
    
    await query.edit_message_text(
        text if text else "Нет заявок.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_application_detail(query, app):
    """Детальный просмотр заявки"""
    text = (
        f"📝 Заявка #{app['id']}\n\n"
        f"👤 Имя: {app['real_name']}\n"
        f"⛏ Ник: {app['minecraft_nick']}\n"
        f"📬 Telegram: {app.get('telegram_user', 'Не указан')}\n"
        f"📅 Дата: {app.get('submitted_at', '—')[:10]}\n"
        f"📊 Статус: {'✅ Принята' if app['status'] == 'accepted' else '⏳ Ожидает'}\n\n"
        f"🛡 Опыт: {app.get('experience', 'Не указан')}\n\n"
        f"💬 Мотивация: {app.get('motivation', 'Не указана')}"
    )
    
    keyboard = []
    if app["status"] == "pending":
        keyboard.append([InlineKeyboardButton(
            "✅ ПРИНЯТЬ ЗАЯВКУ",
            callback_data=f"accept_{app['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 К списку", callback_data="list_pending")])
    keyboard.append([InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def accept_application(query, app_id, applications):
    """Принимает заявку"""
    app = next((a for a in applications if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        await query.edit_message_text("❌ Заявка не найдена или уже обработана.")
        return
    
    # Меняем статус
    app["status"] = "accepted"
    save_json(DATA_FILE, applications)
    
    # Отправляем сообщение принятому
    try:
        await query.bot.send_message(
            chat_id=app["chat_id"],
            text=(
                f"Привет {app['real_name']}!\n"
                f"Твоя заявка на модератора была принята!\n"
                f"И твоего модератора уже выдали!\n"
                f"Ваш ник: {app['minecraft_nick']}"
            )
        )
        send_status = "✅ Уведомление отправлено!"
    except Exception as e:
        send_status = f"⚠️ Не удалось отправить: {e}"
    
    await query.edit_message_text(
        f"✅ Заявка #{app_id} от {app['real_name']} принята!\n\n{send_status}",
        reply_markup=back_button()
    )

def back_button():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")
    ]])

# ========== ЗАПУСК ==========
def main():
    # Создаём приложение Telegram
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("admin", admin_panel))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота в фоновом потоке
    import threading
    threading.Thread(target=telegram_app.run_polling, daemon=True).start()
    
    # Запускаем Flask для вебхуков
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
