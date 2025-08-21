import logging
import asyncio
import os
import threading
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from config import TOKEN, WEBAPP_URL, LOG_LEVEL

# 🔧 Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# HTTP health server (для Render/UptimeRobot)
PORT = int(os.getenv('PORT', '10000'))
_health_app = Flask(__name__)

@_health_app.get('/')
def _health_root():
    return 'OK', 200

@_health_app.get('/health')
def _health_check():
    return 'healthy', 200


def _run_health_server() -> None:
    # В отдельном потоке, чтобы не блокировать Telegram polling
    _logger = logging.getLogger('health')
    _logger.info(f'Health server listening on 0.0.0.0:{PORT}')
    _health_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# 🌍 Тексты на разных языках
LANGUAGES = {
    "ru": {
        "start": "🎉 Добро пожаловать в Actogram Bot!\n\n"
                "🚀 Я помогу вам быстро получить доступ к вашему мессенджеру и другим функциям.\n\n"
                "Выберите действие:",
        "menu": "📋 Главное меню",
        "site": "💬 Открыть Actogram",
        "help": "❓ Помощь",
        "choose_lang": "🌍 Выберите язык:",
        "lang_changed": "✅ Язык изменён!",
        "help_text": "🤖 **Actogram Bot - Ваш помощник**\n\n"
                    "📱 **Основные команды:**\n"
                    "• /start - Главное меню\n"
                    "• /help - Помощь\n"
                    "• /menu - Показать меню\n"
                    "• /lang - Изменить язык\n\n"
                    "💬 **Мессенджер Actogram:**\n"
                    "Быстрый доступ к вашему персональному мессенджеру\n\n"
                    "🌐 **Веб-приложение:**\n"
                    "Полнофункциональная версия на сайте",
        "about": "ℹ️ **О боте:**\n\n"
                "Actogram Bot - это умный помощник для быстрого доступа к вашему мессенджеру.\n\n"
                "✨ **Возможности:**\n"
                "• Быстрый доступ к мессенджеру\n"
                "• Многоязычная поддержка\n"
                "• Удобный интерфейс\n"
                "• Интеграция с веб-приложением",
        "back_to_menu": "🔙 Вернуться в меню",
        "messenger_title": "💬 **Actogram Messenger**\n\nОткройте ваш персональный мессенджер:",
        "web_app_title": "🌐 **Веб-приложение Actogram**\n\nПолная версия с дополнительными функциями:"
    },
    "uz": {
        "start": "🎉 Actogram Bot-ga xush kelibsiz!\n\n"
                "🚀 Men sizga messenjeringiz va boshqa funksiyalarga tez kirishda yordam beraman.\n\n"
                "Harakatni tanlang:",
        "menu": "📋 Asosiy menyu",
        "site": "💬 Actogram-ni ochish",
        "help": "❓ Yordam",
        "choose_lang": "🌍 Tilni tanlang:",
        "lang_changed": "✅ Til o'zgartirildi!",
        "help_text": "🤖 **Actogram Bot - Sizning yordamchingiz**\n\n"
                    "📱 **Asosiy buyruqlar:**\n"
                    "• /start - Asosiy menyu\n"
                    "• /help - Yordam\n"
                    "• /menu - Menyuni ko'rsatish\n"
                    "• /lang - Tilni o'zgartirish\n\n"
                    "💬 **Actogram Messenjeri:**\n"
                    "Shaxsiy messenjeringizga tez kirish\n\n"
                    "🌐 **Veb-ilova:**\n"
                    "To'liq funksiyali versiya saytda",
        "about": "ℹ️ **Bot haqida:**\n\n"
                "Actogram Bot - bu messenjeringizga tez kirish uchun aqlli yordamchi.\n\n"
                "✨ **Imkoniyatlar:**\n"
                "• Messenjerga tez kirish\n"
                "• Ko'p tilli qo'llab-quvvatlash\n"
                "• Qulay interfeys\n"
                "• Veb-ilova bilan integratsiya",
        "back_to_menu": "🔙 Menyuga qaytish",
        "messenger_title": "💬 **Actogram Messenjeri**\n\nShaxsiy messenjeringizni oching:",
        "web_app_title": "🌐 **Actogram Veb-ilovasi**\n\nQo'shimcha funksiyalar bilan to'liq versiya:"
    }
}

# 🗂 Память пользователей (в реальности лучше БД)
user_lang = {}

# 📌 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")

    keyboard = [
        [InlineKeyboardButton("💬 " + LANGUAGES[lang]["site"], web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("🌐 Веб-приложение", url=WEBAPP_URL)],
        [InlineKeyboardButton("❓ " + LANGUAGES[lang]["help"], callback_data="help")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton("🌍 Language / Til", callback_data="lang")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(LANGUAGES[lang]["start"], reply_markup=reply_markup, parse_mode='Markdown')

# 📌 /menu command
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")

    keyboard = [
        [InlineKeyboardButton("💬 " + LANGUAGES[lang]["site"], web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("🌐 Веб-приложение", url=WEBAPP_URL)],
        [InlineKeyboardButton("❓ " + LANGUAGES[lang]["help"], callback_data="help")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton("🌍 Language / Til", callback_data="lang")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📋 **Главное меню**" if lang == "ru" else "📋 **Asosiy menyu**", 
                                   reply_markup=reply_markup, parse_mode='Markdown')

# 📌 /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")
    
    keyboard = [[InlineKeyboardButton(LANGUAGES[lang]["back_to_menu"], callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(LANGUAGES[lang]["help_text"], reply_markup=reply_markup, parse_mode='Markdown')

# 📌 Обработка нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    lang = user_lang.get(chat_id, "ru")

    await query.answer()

    if query.data == "lang":
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_ru")],
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="set_uz")],
            [InlineKeyboardButton(LANGUAGES[lang]["back_to_menu"], callback_data="menu")]
        ]
        await query.edit_message_text(
            text=LANGUAGES[lang]["choose_lang"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif query.data == "help":
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]["back_to_menu"], callback_data="menu")]]
        await query.edit_message_text(
            LANGUAGES[lang]["help_text"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif query.data == "about":
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]["back_to_menu"], callback_data="menu")]]
        await query.edit_message_text(
            LANGUAGES[lang]["about"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif query.data == "menu":
        keyboard = [
            [InlineKeyboardButton("💬 " + LANGUAGES[lang]["site"], web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton("🌐 Веб-приложение", url=WEBAPP_URL)],
            [InlineKeyboardButton("❓ " + LANGUAGES[lang]["help"], callback_data="help")],
            [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
            [InlineKeyboardButton("🌍 Language / Til", callback_data="lang")]
        ]
        await query.edit_message_text(
            "📋 **Главное меню**" if lang == "ru" else "📋 **Asosiy menyu**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif query.data.startswith("set_"):
        new_lang = query.data.split("_")[1]
        user_lang[chat_id] = new_lang
        keyboard = [[InlineKeyboardButton(LANGUAGES[new_lang]["back_to_menu"], callback_data="menu")]]
        await query.edit_message_text(
            LANGUAGES[new_lang]["lang_changed"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# 📌 Обработка текстов
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")
    
    # Красивое меню при любом тексте
    keyboard = [
        [InlineKeyboardButton("💬 " + LANGUAGES[lang]["site"], web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("🌐 Веб-приложение", url=WEBAPP_URL)],
        [InlineKeyboardButton("❓ " + LANGUAGES[lang]["help"], callback_data="help")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton("🌍 Language / Til", callback_data="lang")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 **Главное меню**" if lang == "ru" else "📋 **Asosiy menyu**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# 🚀 Запуск
def main():
    # Поднимаем HTTP health-сервер для Render/UptimeRobot
    threading.Thread(target=_run_health_server, daemon=True).start()

    # Создаем приложение Telegram
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
    
    app.add_error_handler(error_handler)

    # Запускаем бота (polling)
    try:
        logger.info("🚀 Starting Actogram Bot...")
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
