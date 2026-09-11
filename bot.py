"""
Luxonos Community Telegram Bot
--------------------------------
A community bot for the Luxonos memecoin (Robinhood Chain).

Features:
  /start      - welcome message
  /price      - fetches live price/volume/market cap from Dexscreener (if the pair is indexed there)
  /contract   - shows the contract address
  /website    - shows the official website
  /socials    - shows social links
  /help       - lists all commands
  Welcome message for new members joining the group
  Basic anti-spam: deletes messages containing links/forwarded ads from brand-new members (first 10 min)

Setup:
  1. pip install -r requirements.txt
  2. Create a file named `.env` (see .env.example) and put your BotFather token in it
  3. Run: python bot.py
"""

import logging
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from telegram import Update, ChatMemberUpdated
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

# ---------------------------------------------------------------------------
# CONFIG — edit these or set them in your .env file
# ---------------------------------------------------------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOTFATHER_TOKEN_HERE")

COIN_NAME = "Luxonos"
CONTRACT_ADDRESS = "0x8240aa31d53f34bb53a9031d3efbfb50f5ce5fa1"
CHAIN_NAME = "Robinhood Chain"
WEBSITE_URL = "https://luxono.netlify.app/"

# Add your real social links here once you have them
TWITTER_URL = "https://x.com/Luxono_"
TELEGRAM_GROUP_URL = "https://t.me/YOUR_GROUP_HANDLE"  # update once your group exists

# Dexscreener works for most EVM chains once the pair is indexed.
# If Luxonos isn't listed yet, /price will say so instead of crashing.
DEXSCREENER_API = f"https://api.dexscreener.com/latest/dex/tokens/{CONTRACT_ADDRESS}"

# How long (in minutes) a new member is considered "new" for anti-spam purposes
NEW_MEMBER_GRACE_MINUTES = 10

# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory store of when each user joined (resets if the bot restarts)
_join_times: dict[int, datetime] = {}


# ---------------------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"👋 <b>Mirë se erdhe te {COIN_NAME}!</b>\n\n"
        f"🔗 Chain: {CHAIN_NAME}\n"
        f"📄 Kontrata: <code>{CONTRACT_ADDRESS}</code>\n\n"
        "Komandat e disponueshme:\n"
        "/price — çmimi dhe statistikat aktuale\n"
        "/contract — adresa e kontratës\n"
        "/website — website-i zyrtar\n"
        "/socials — rrjetet sociale\n"
        "/help — kjo listë"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def contract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"📄 <b>Kontrata e {COIN_NAME}</b>\n\n"
        f"<code>{CONTRACT_ADDRESS}</code>\n\n"
        f"Chain: {CHAIN_NAME}\n\n"
        "⚠️ Gjithmonë verifiko adresën vetë përpara se të blesh — mos u beso linkeve nga persona të panjohur."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def website(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"🌐 Website zyrtar:\n{WEBSITE_URL}")


async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📢 <b>Na gjej këtu:</b>\n\n"
        f"🌐 Website: {WEBSITE_URL}\n"
        f"🐦 X (Twitter): {TWITTER_URL}\n"
        f"💬 Telegram: {TELEGRAM_GROUP_URL}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")
    try:
        resp = requests.get(DEXSCREENER_API, timeout=10)
        data = resp.json()
        pairs = data.get("pairs") or []
        if not pairs:
            await update.message.reply_text(
                "📉 Nuk gjeta ende të dhëna çmimi për "
                f"{COIN_NAME} te Dexscreener. Kjo është normale nëse coin-i "
                "është shumë i ri ose ende s'ka likuiditet të mjaftueshëm."
            )
            return

        # Use the pair with the highest liquidity
        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        price_usd = pair.get("priceUsd", "N/A")
        change_24h = pair.get("priceChange", {}).get("h24", "N/A")
        volume_24h = pair.get("volume", {}).get("h24", "N/A")
        liquidity_usd = pair.get("liquidity", {}).get("usd", "N/A")
        market_cap = pair.get("fdv", "N/A")
        pair_url = pair.get("url", WEBSITE_URL)

        text = (
            f"💰 <b>{COIN_NAME} — Çmimi aktual</b>\n\n"
            f"Çmimi: ${price_usd}\n"
            f"Ndryshimi 24h: {change_24h}%\n"
            f"Volumi 24h: ${volume_24h}\n"
            f"Likuiditeti: ${liquidity_usd}\n"
            f"Market Cap (FDV): ${market_cap}\n\n"
            f"🔗 <a href='{pair_url}'>Shiko live te Dexscreener</a>"
        )
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Price fetch failed: %s", exc)
        await update.message.reply_text(
            "⚠️ Pati një problem duke marrë çmimin. Provo përsëri pak më vonë."
        )


# ---------------------------------------------------------------------------
# WELCOME + BASIC ANTI-SPAM
# ---------------------------------------------------------------------------
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result: ChatMemberUpdated = update.chat_member
    if result.new_chat_member.status != "member":
        return
    # Ignore if this isn't actually a fresh join
    if result.old_chat_member.status in ("member", "administrator", "creator"):
        return

    user = result.new_chat_member.user
    _join_times[user.id] = datetime.utcnow()

    text = (
        f"🎉 Mirë se erdhe në komunitetin e <b>{COIN_NAME}</b>, "
        f"{user.mention_html()}!\n\n"
        "Shkruaj /help për të parë komandat e disponueshme.\n"
        "⚠️ Ruhu nga mesazhet private nga 'admins' të rremë — asnjë admin i vërtetë s'të kërkon fjalëkalime apo seed phrase."
    )
    try:
        await context.bot.send_message(
            chat_id=result.chat.id, text=text, parse_mode=ParseMode.HTML
        )
    except Exception:
        logger.exception("Could not send welcome message")


async def anti_spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes link-containing messages from users who joined very recently."""
    msg = update.message
    if not msg or not msg.from_user:
        return

    user_id = msg.from_user.id
    joined_at = _join_times.get(user_id)
    if not joined_at:
        return  # unknown join time (e.g. bot restarted) — don't touch it

    still_new = datetime.utcnow() - joined_at < timedelta(minutes=NEW_MEMBER_GRACE_MINUTES)
    has_link = bool(msg.entities and any(e.type in ("url", "text_link") for e in msg.entities))

    if still_new and has_link:
        try:
            await msg.delete()
            warning = await context.bot.send_message(
                chat_id=msg.chat_id,
                text=(
                    f"🚫 Mesazhi i {msg.from_user.mention_html()} u fshi automatikisht "
                    "(anëtarë të rinj s'mund të postojnë linke për "
                    f"{NEW_MEMBER_GRACE_MINUTES} minuta, si masë anti-spam)."
                ),
                parse_mode=ParseMode.HTML,
            )
            # auto-delete the warning after 15s so the chat stays clean
            time.sleep(0)  # placeholder, real delay handled via job_queue below
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(msg.chat_id, warning.message_id),
                when=15,
            )
        except Exception:
            logger.exception("Could not delete spam message")


# ---------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOTFATHER_TOKEN_HERE":
        raise SystemExit(
            "❌ Vendos BOT_TOKEN te skedari .env përpara se ta nisësh botin."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("contract", contract))
    app.add_handler(CommandHandler("website", website))
    app.add_handler(CommandHandler("socials", socials))

    app.add_handler(ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam_filter))

    logger.info("Luxonos bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
