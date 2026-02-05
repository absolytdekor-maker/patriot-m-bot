import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)
from database import (
    инициализировать_базу, добавить_пользователя, проверить_доступ,
    проверить_админа, установить_расценку, получить_расценку,
    получить_все_расценки, добавить_работу, получить_работы_до_сегодня,
    экспорт_в_csv
)
from config import ТОКЕН_БОТА, ВЛАДЕЛЕЦ_ID, ПОЛУЧАТЕЛЬ_ОТЧЁТОВ_ID
from scheduler import запустить_планировщик
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ВЫБОР_ОПЕРАЦИИ, ВВОД_КОЛИЧЕСТВА = range(2)

НАЗВАНИЯ_ОПЕРАЦИЙ = {
    "sw_rama_8": "1) Сварка рамы 8 отв.",
    "sw_kal_qr": "2) Сварка + калибр + QR",
    "paj_reg_kond_sil": "3) Пайка регулятора (конд+сил)",
    "paj_reg_kond_sil_mot": "4) Пайка регулятора (+моторы)",
    "paj_polt_kript_tep_kam_vtx": "5) Пайка полетника (камера на конн.)",
    "paj_polt_kript_tep_kam_rasp_vtx": "6) Пайка полетника (камера под расп.)",
    "sb_dron": "7) Сборка дрона",
    "obletka": "8) Облетка"
}

async def старт(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not проверить_доступ(user_id):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    клавиатура = [["/add", "/me"], ["/rates"]]
    reply_markup = ReplyKeyboardMarkup(клавиатура, resize_keyboard=True)
    await update.message.reply_text(
        "✅ Добро пожаловать в систему учёта «Патриот-М»!\n\n"
        "Вы работаете по сдельной оплате.\n"
        "Нажмите /add → выберите операцию → введите количество.\n\n"
        "Доступные команды:\n"
        "/me — ваша зарплата с начала месяца\n"
        "/add — добавить выполненную операцию\n"
        "/rates — список расценок",
        reply_markup=reply_markup
    )

async def выдать_доступ(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ВЛАДЕЛЕЦ_ID:
        await update.message.reply_text("🚫 Только владелец может выдавать доступ.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /grant <ID_пользователя> [имя]")
        return
    try:
        целевой_id = int(context.args[0])
        имя = context.args[1] if len(context.args) > 1 else f"пользователь_{целевой_id}"
        добавить_пользователя(целевой_id, имя)
        await update.message.reply_text(f"✅ Доступ выдан: {имя} ({целевой_id})")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID.")

async def установить_расценку_команда(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not проверить_админа(user_id):
        await update.message.reply_text("🚫 Только админ может устанавливать расценки.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /rate <код> <ставка>")
        return
    код = context.args[0]
    try:
        ставка = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ставка должна быть числом.")
        return
    установить_расценку(код, ставка, "шт")
    название = НАЗВАНИЯ_ОПЕРАЦИЙ.get(код, код)
    await update.message.reply_text(f"✅ Расценка: {название} = {ставка} руб/шт")

async def моя_зп_сегодня(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not проверить_доступ(user_id):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    работы = получить_работы_до_сегодня(user_id)
    if not работы:
        await update.message.reply_text("📭 Нет работ с начала месяца.")
        return
    итого = 0.0
    детали = []
    for тип_операции, колво, дата in работы:
        расценка = получить_расценку(тип_операции)
        if расценка:
            ставка, единица = расценка
            сумма = колво * ставка
            итого += сумма
            дата_стр = дата[:10]
            название = НАЗВАНИЯ_ОПЕРАЦИЙ.get(тип_операции, тип_операции)
            детали.append(f"• {дата_стр} | {название}: {колво} {единица} × {ставка} = {сумма:.2f} руб")
        else:
            детали.append(f"• {тип_операции}: {колво} — ❌ без расценки")
    сейчас = datetime.now()
    период = f"с 01.{сейчас.month:02d}.{сейчас.year} по {сейчас.day:02d}.{сейчас.month:02d}.{сейчас.year}"
    текст = f"💰 Ваша зарплата {период}:\n\n" + "\n".join(детали) + f"\n\nИТОГО: {итого:.2f} руб"
    await update.message.reply_text(текст)

async def список_расценок(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not проверить_доступ(user_id):
        return
    расценки = получить_все_расценки()
    if not расценки:
        await update.message.reply_text("📭 Нет расценок.")
        return
    текст = "📋 Доступные операции:\n\n"
    for код, ставка, _ in расценки:
        название = НАЗВАНИЯ_ОПЕРАЦИЙ.get(код, код)
        текст += f"• {название}: {ставка} руб/шт\n"
    await update.message.reply_text(текст)

async def экспорт_команда(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not проверить_админа(user_id):
        await update.message.reply_text("🚫 Только админ может экспортировать.")
        return
    try:
        путь = экспорт_в_csv()
        with open(путь, "rb") as f:
            await update.message.reply_document(document=f, caption="📄 Экспорт за текущий месяц")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def начать_добавление(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not проверить_доступ(user_id):
        await update.message.reply_text("❌ Доступ запрещён.")
        return ВЫБОР_ОПЕРАЦИИ

    расценки = получить_все_расценки()
    if not расценки:
        await update.message.reply_text("📭 Нет доступных операций.")
        return ВЫБОР_ОПЕРАЦИИ

    кнопки = []
    ряд = []
    for код, _, _ in расценки:
        человекочитаемое = НАЗВАНИЯ_ОПЕРАЦИЙ.get(код, код)
        ряд.append(InlineKeyboardButton(человекочитаемое, callback_data=f"op_{код}"))
        if len(ряд) == 2:
            кнопки.append(ряд)
            ряд = []
    if ряд:
        кнопки.append(ряд)

    клавиатура = InlineKeyboardMarkup(кнопки)
    await update.message.reply_text("Выберите операцию:", reply_markup=клавиатура)
    return ВЫБОР_ОПЕРАЦИИ

async def выбрать_операцию(update: Update, context: ContextTypes.DEFAULT_TYPE):
    запрос = update.callback_query
    await запрос.answer()
    код = запрос.data.replace("op_", "")
    context.user_data["выбранная_операция"] = код
    название = НАЗВАНИЯ_ОПЕРАЦИЙ.get(код, код)
    await запрос.edit_message_text(f"Вы выбрали: {название}\n\n✏️ Введите количество (только число):")
    return ВВОД_КОЛИЧЕСТВА

async def ввести_количество(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    имя = update.effective_user.username or f"пользователь_{user_id}"
    код = context.user_data.get("выбранная_операция")

    if not код:
        await update.message.reply_text("❌ Ошибка: операция не выбрана.")
        return ВВОД_КОЛИЧЕСТВА

    try:
        количество = float(update.message.text.replace(",", "."))
        if количество <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите положительное число (например: 1, 2.5)")
        return ВВОД_КОЛИЧЕСТВА

    расценка = получить_расценку(код)
    if not расценка:
        await update.message.reply_text("❌ Ошибка: расценка не найдена.")
        return ВВОД_КОЛИЧЕСТВА

    ставка, единица = расценка
    сумма = количество * ставка
    добавить_работу(user_id, имя, код, количество)

    from sheets import добавить_в_google
    добавить_в_google(имя, код, количество, ставка, сумма, user_id)

    бот = context.bot
    try:
        await бот.send_message(
            chat_id=ВЛАДЕЛЕЦ_ID,
            text=f"🔔 Новая работа!\n\n👤 @{имя} ({user_id})\n📄 {НАЗВАНИЯ_ОПЕРАЦИЙ.get(код, код)}: {количество} {единица}\n💰 {сумма:.2f} руб"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление: {e}")

    await update.message.reply_text(
        f"✅ Готово!\n{НАЗВАНИЯ_ОПЕРАЦИЙ.get(код, код)}: {количество} {единица}\n💰 Заработано: {сумма:.2f} руб"
    )
    return ВВОД_КОЛИЧЕСТВА

def основная():
    инициализировать_базу()
    добавить_пользователя(ВЛАДЕЛЕЦ_ID, "владелец", админ=True)

    приложение = Application.builder().token(ТОКЕН_БОТА).build()

    приложение.add_handler(CommandHandler("start", старт))
    приложение.add_handler(CommandHandler("grant", выдать_доступ))
    приложение.add_handler(CommandHandler("rate", установить_расценку_команда))
    приложение.add_handler(CommandHandler("me", моя_зп_сегодня))
    приложение.add_handler(CommandHandler("rates", список_расценок))
    приложение.add_handler(CommandHandler("export", экспорт_команда))

    диалог_добавления = ConversationHandler(
        entry_points=[CommandHandler("add", начать_добавление)],
        states={
            ВЫБОР_ОПЕРАЦИИ: [CallbackQueryHandler(выбрать_операцию)],
            ВВОД_КОЛИЧЕСТВА: [MessageHandler(filters.TEXT & ~filters.COMMAND, ввести_количество)],
        },
        fallbacks=[]
    )
    приложение.add_handler(диалог_добавления)

    цикл = asyncio.get_event_loop()
    цикл.create_task(запустить_планировщик())
    приложение.run_polling()

if __name__ == "__main__":
    основная()