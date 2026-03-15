from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from config import BOT_TOKEN
from database import *
from scheduler import scheduler


logging.basicConfig(level=logging.INFO)

SELECT_OP, SELECT_QTY, ENTER_QTY = range(3)

OPS = {
    "sw_rama_8": "Сварка рамы",
    "sw_kal_qr": "Сварка + QR",
    "sb_dron": "Сборка дрона",
    "obletka": "Облетка"
}


# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if not has_access(uid):
        await update.message.reply_text("❌ Нет доступа")
        return

    await update.message.reply_text(
        "✅ Добро пожаловать в систему Патриот-М\n\n"
        "Добавление операции:\n"
        "/add\n\n"
        "Команды:\n"
        "/today — операции за сегодня\n"
        "/last — удалить последнюю"
    )


# ==============================
# ADD OPERATION
# ==============================

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    buttons = [
        [InlineKeyboardButton(name, callback_data=code)]
        for code, name in OPS.items()
    ]

    await update.message.reply_text(
        "Выберите операцию:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    return SELECT_OP


async def choose_op(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["op"] = query.data

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("0.5", callback_data="0.5"),
            InlineKeyboardButton("1", callback_data="1"),
            InlineKeyboardButton("2", callback_data="2")
        ],
        [
            InlineKeyboardButton("5", callback_data="5"),
            InlineKeyboardButton("10", callback_data="10")
        ],
        [
            InlineKeyboardButton("✏️ Другое", callback_data="custom")
        ]
    ])

    await query.edit_message_text(
        "Выберите количество:",
        reply_markup=keyboard
    )

    return SELECT_QTY


async def choose_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "custom":
        await query.edit_message_text("Введите количество:")
        return ENTER_QTY

    qty = float(query.data)

    return await save_work(update, context, qty)


async def enter_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        qty = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return ENTER_QTY

    return await save_work(update, context, qty)


# ==============================
# SAVE WORK
# ==============================

async def save_work(update, context, qty):

    user = update.effective_user
    op = context.user_data.get("op")

    if not op:
        await update.effective_chat.send_message("Ошибка: операция не выбрана")
        return ConversationHandler.END

    add_work(user.id, user.username or str(user.id), op, qty)

    await update.effective_chat.send_message(
        f"✅ Добавлено\n"
        f"{OPS.get(op)} — {qty}"
    )

    return ConversationHandler.END


# ==============================
# TODAY
# ==============================

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📅 Функция today будет показывать операции за сегодня"
    )


# ==============================
# DELETE LAST
# ==============================

async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):

    delete_last(update.effective_user.id)

    await update.message.reply_text(
        "🗑 Последняя операция удалена"
    )


# ==============================
# MAIN
# ==============================

def main():

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден")
        return

    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("add", add)],
        states={
            SELECT_OP: [CallbackQueryHandler(choose_op)],
            SELECT_QTY: [CallbackQueryHandler(choose_qty)],
            ENTER_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_qty)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("last", last))
    app.add_handler(conv)

    # запуск планировщика
    asyncio.get_event_loop().create_task(scheduler())

    print("🚀 Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()