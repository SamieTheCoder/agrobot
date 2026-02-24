import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, filters, ContextTypes
)
from automation import validate_excel, process_file, REQUIRED_COLUMNS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# How often to send a live progress ping (every N rows)
PROGRESS_PING_EVERY = 20


# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cols = "\n".join(f"  • {c}" for c in REQUIRED_COLUMNS)
    await update.message.reply_text(
        f"👋 *Form Filler Bot*\n\n"
        f"Send me an Excel (.xlsx) file with these columns:\n{cols}\n\n"
        f"I'll validate the file, fill the form row by row, "
        f"and send you a full report when done.",
        parse_mode="Markdown"
    )


# ── Document handler ──────────────────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc  = update.message.document
    chat = update.message.chat_id

    # ── 1. File type check ────────────────────────────────────────────────────
    if not doc.file_name.endswith('.xlsx'):
        await update.message.reply_text(
            "❌ Only *.xlsx* files are accepted. Please re-export your file as Excel.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("📥 File received — validating...")

    # ── 2. Download ───────────────────────────────────────────────────────────
    tg_file   = await context.bot.get_file(doc.file_id)
    file_path = f"/tmp/{doc.file_id}.xlsx"
    await tg_file.download_to_drive(file_path)

    # ── 3. Validate ───────────────────────────────────────────────────────────
    df, reg_no, password, val_error = validate_excel(file_path)

    if val_error:
        await context.bot.send_message(
            chat,
            f"❌ *Validation Failed*\n\n{val_error}",
            parse_mode="Markdown"
        )
        return

    total = len(df)
    await context.bot.send_message(
        chat,
        f"✅ *File Valid*\n"
        f"📊 Rows to process: *{total}*\n"
        f"👤 Account: `{reg_no}`\n\n"
        f"⏳ Automation started — I'll update you every {PROGRESS_PING_EVERY} rows.",
        parse_mode="Markdown"
    )

    # ── 4. Run automation in thread (don't block event loop) ──────────────────
    loop = asyncio.get_event_loop()

    # Collect progress ticks from the sync thread
    progress_ticks: list[str] = []

    def progress_callback(current: int, total_rows: int, product_name: str):
        pct = int((current / total_rows) * 100)
        tick = f"`[{pct:3d}%]` {current}/{total_rows} — {product_name[:45]}"
        progress_ticks.append(tick)

        # Every N rows, schedule a Telegram message from the main loop
        if current % PROGRESS_PING_EVERY == 0 or current == total_rows:
            batch = "\n".join(progress_ticks[-PROGRESS_PING_EVERY:])
            asyncio.run_coroutine_threadsafe(
                context.bot.send_message(chat, f"📈 *Progress*\n{batch}", parse_mode="Markdown"),
                loop
            )

    try:
        success_count, error_list = await loop.run_in_executor(
            None,
            lambda: process_file(file_path, progress_callback)
        )

        # ── 5. Final report ───────────────────────────────────────────────────
        report = f"🏁 *Automation Complete*\n\n"
        report += f"✔️ Successful rows: *{success_count} / {total}*\n"

        if not error_list:
            report += "🎉 All rows submitted without errors!"
        else:
            report += f"❌ Failed rows: *{len(error_list)}*\n\n"
            report += "*Error Details:*\n"
            # Show first 15 errors max to stay under Telegram's 4096 char limit
            shown = error_list[:15]
            report += "\n".join(f"• {e}" for e in shown)
            if len(error_list) > 15:
                report += f"\n_...and {len(error_list) - 15} more (check server logs)_"

        await context.bot.send_message(chat, report, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Automation crashed")
        await context.bot.send_message(
            chat,
            f"💥 *Automation Failed*\n\n`{str(e)}`\n\n"
            f"Fix the issue and resend the file.",
            parse_mode="Markdown"
        )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    logger.info("Bot is polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
