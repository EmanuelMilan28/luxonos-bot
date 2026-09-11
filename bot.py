"""
Luxonos Community Telegram Bot
--------------------------------
Official community bot for Luxonos (Robinhood Chain).

Features:
  /start      - welcome message
  /price      - live price/volume/market cap via Dexscreener (if indexed)
  /contract   - displays the contract address
  /website    - official website link
  /socials    - social media links
  /help       - lists all commands
  Automatic welcome message for new members
  Basic anti-spam: deletes links posted by brand-new members (first 10 min)

Setup:
  1. pip install -r requirements.txt
  2. Create a `.env` file (see .env.example) with your BotFather token
  3. Run: python bot.py
"""

import logging
import os
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

# Update these once your real accounts exist
TWITTER_URL = "https://x.com/Luxono_"
TELEGRAM_GROUP_URL = "https://t.me/YOUR_GROUP_HANDLE"

# Dexscreener works for most EVM chains once the pair is indexed.
DEXSCREENER_API = f"https://api.dexscreener.com/latest/dex/tokens/{CONTRACT_ADDRESS}"

# How long (minutes) a new member is treated as "new" for anti-spam purposes
NEW_MEMBER_GRACE_MINUTES = 10

# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory store of join times (resets on bot restart)
_join_times: dict[int, datetime] = {}


# ---------------------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"👋 <b>Welcome to {COIN_NAME}!</b>\n\n"
        f"🔗 Chain: {CHAIN_NAME}\n"
        f"📄 Contract: <code>{CONTRACT_ADDRESS}</code>\n\n"
        "<b>Available commands:</b>\n"
        "/price — current price and market stats\n"
        "/contract — official contract address\n"
        "/website — official website\n"
        "/socials — social media links\n"
        "/help — show this menu"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def contract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"📄 <b>{COIN_NAME} Contract Address</b>\n\n"
        f"<code>{CONTRACT_ADDRESS}</code>\n\n"
        f"Chain: {CHAIN_NAME}\n\n"
        "⚠️ Always verify this address yourself before trading — never trust links from unknown users."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def website(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"🌐 Official website:\n{WEBSITE_URL}")


async def socials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📢 <b>Find us here:</b>\n\n"
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
                f"📉 No live price data found yet for {COIN_NAME} on Dexscreener. "
                "This is normal for a very new token or one with limited liquidity."
            )
            return

        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        price_usd = pair.get("priceUsd", "N/A")
        change_24h = pair.get("priceChange", {}).get("h24", "N/A")
        volume_24h = pair.get("volume", {}).get("h24", "N/A")
        liquidity_usd = pair.get("liquidity", {}).get("usd", "N/A")
        market_cap = pair.get("fdv", "N/A")
        pair_url = pair.get("url", WEBSITE_URL)

        text = (
            f"💰 <b>{COIN_NAME} — Live Price</b>\n\n"
            f"Price: ${price_usd}\n"
            f"24h change: {change_24h}%\n"
            f"24h volume: ${volume_24h}\n"
            f"Liquidity: ${liquidity_usd}\n"
            f"Market Cap (FDV): ${market_cap}\n\n"
            f"🔗 <a href='{pair_url}'>View live on Dexscreener</a>"
        )
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Price fetch failed: %s", exc)
        await update.message.reply_text(
            "⚠️ Something went wrong fetching the price. Please try again shortly."
        )


# ---------------------------------------------------------------------------
# WELCOME + BASIC ANTI-SPAM
# ---------------------------------------------------------------------------
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result: ChatMemberUpdated = update.chat_member
    if result.new_chat_member.status != "member":
        return
    if result.old_chat_member.status in ("member", "administrator", "creator"):
        return

    user = result.new_chat_member.user
    _join_times[user.id] = datetime.utcnow()

    text = (
        f"🎉 Welcome to the <b>{COIN_NAME}</b> community, {user.mention_html()}!\n\n"
        "Type /help to see what I can do.\n"
        "⚠️ Beware of DMs from fake 'admins' — no real admin will ever ask for your password or seed phrase."
    )
    try:
        await context.bot.send_message(
            chat_id=result.chat.id, text=text, parse_mode=ParseMode.HTML
        )
    except Exception:
        logger.exception("Could not send welcome message")


async def anti_spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes link-containing messages from very recently joined members."""
    msg = update.message
    if not msg or not msg.from_user:
        return

    user_id = msg.from_user.id
    joined_at = _join_times.get(user_id)
    if not joined_at:
        return  # unknown join time (e.g. bot restarted) — leave it alone

    still_new = datetime.utcnow() - joined_at < timedelta(minutes=NEW_MEMBER_GRACE_MINUTES)
    has_link = bool(msg.entities and any(e.type in ("url", "text_link") for e in msg.entities))

    if still_new and has_link:
        try:
            await msg.delete()
            warning = await context.bot.send_message(
                chat_id=msg.chat_id,
                text=(
                    f"🚫 A message from {msg.from_user.mention_html()} was auto-removed "
                    f"(new members can't post links for {NEW_MEMBER_GRACE_MINUTES} minutes — anti-spam protection)."
                ),
                parse_mode=ParseMode.HTML,
            )
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(msg.chat_id, warning.message_id),
                when=15,
            )
        except Exception:
            logger.exception("Could not delete spam message")


# ---------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOTFATHER_TOKEN_HERE":
        raise SystemExit("❌ Set BOT_TOKEN in your .env file before starting the bot.")

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
