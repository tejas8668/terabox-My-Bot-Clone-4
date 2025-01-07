import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import urllib.parse
from pymongo import MongoClient
from datetime import datetime, timedelta
import requests


admin_ids = [6025969005, 6018060368]

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI')  # Get MongoDB URI from environment variables
client = MongoClient(MONGO_URI)
db = client['terabox_bot']
users_collection = db['users']

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token and channel ID from environment variables
TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# In-memory storage for user tracking
users = set()

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    user = update.effective_user

    # Check if the start command includes a token (for verification)
    if context.args:
        token = context.args[0]
        user_data = users_collection.find_one({"user_id": user.id, "token": token})

        if user_data:
            # Update the user's verification status
            users_collection.update_one(
                {"user_id": user.id},
                {"$set": {"verified_until": datetime.now() + timedelta(days=1)}},
                upsert=True
            )
            await update.message.reply_text(
                "✅ **Verification Successful!**\n\n"
                "You can now use the bot for the next 24 hours without any ads or restrictions.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Invalid Token!**\n\n"
                "Please try verifying again.",
                parse_mode='Markdown'
            )
        return

    # If no token, send the welcome message
    users.add(user.id)  # Add user to the in-memory set
    message = (
        f"New user started the bot:\n"
        f"Name: {user.full_name}\n"
        f"Username: @{user.username}\n"
        f"User   ID: {user.id}"
    )
    await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
    await update.message.reply_photo(
        photo='https://ik.imagekit.io/dvnhxw9vq/unnamed.png?updatedAt=1735280750258',  # Replace with your image URL
        caption=(
            "👋 **ℍ𝕖𝕝𝕝𝕠 𝔻𝕖𝕒𝕣!**\n\n"
            "SEND ME ANY TERABOX LINK, I WILL SEND YOU DIRECT STREAM LINK WITHOUT TERABOX LOGIN OR ANY ADS​\n\n"
            "**𝐈𝐦𝐩𝐨𝐫𝐭𝐚𝐧𝐭​​**\n\n"
            "𝗨𝘀𝗲 𝗖𝗵𝗿𝗼𝗺𝗲 𝗙𝗼𝗿 𝗔𝗰𝗰𝗲𝘀𝘀 𝗠𝘆 𝗔𝗹𝗹 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀"
        ),
        parse_mode='Markdown'
    )

# Define the /users command handler
async def users_count(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id in admin_ids:
        user_count = len(users)
        await update.message.reply_text(f"Total users who have interacted with the bot: {user_count}")
    else:
        await update.message.reply_text("You Have No Rights To Use My Commands")

async def handle_link(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    # Check if user is admin
    if user.id in admin_ids:
        # Admin ko verify karne ki zaroorat na ho
        pass
    else:
        # User ko verify karne ki zaroorat hai
        if not await check_verification(user.id):
            # User ko verify karne ki zaroorat hai
            btn = [
                [InlineKeyboardButton("Verify", url=await get_token(user.id, context.bot.username))],
                [InlineKeyboardButton("How To Open Link & Verify", url="https://t.me/how_to_download_0011")]
            ]
            await update.message.reply_text(
                text="🚨 <b>Token Expired!</b>\n\n"
                     "<b>Timeout: 24 hours</b>\n\n"
                     "Your access token has expired. Verify it to continue using the bot!\n\n"
                     "<b>🔑 Why Tokens?</b>\n\n"
                     "Tokens unlock premium features with a quick ad process. Enjoy 24 hours of uninterrupted access! 🌟\n\n"
                     "<b>👉 Tap below to verify your token.</b>\n\n"
                     "Thank you for your support! ❤️",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return

    # Check if user sent a link
    if update.message.text.startswith('http://') or update.message.text.startswith('https://'):
        # User sent a link
        original_link = update.message.text
        parsed_link = urllib.parse.quote(original_link, safe='')
        modified_link = f"https://streamterabox.blogspot.com/?q={parsed_link}&m=0"
        modified_url = f"https://streamterabox.blogspot.com/2024/12/terabox-player.html?q={parsed_link}"

        # Create a button with the modified link
        button = [
            [InlineKeyboardButton("Stream Server 1", url=modified_link)],
            [InlineKeyboardButton("Stream Server 2", url=modified_url)]
        ]
        reply_markup = InlineKeyboardMarkup(button)

        # Send the user's details and message to the channel
        user_message = (
            f"User   message:\n"
            f"Name: {update.effective_user.full_name}\n"
            f"Username: @{update.effective_user.username}\n"
            f"User   ID: {update.effective_user.id}\n"
            f"Message: {original_link}"
        )
        await context.bot.send_message(chat_id=os.getenv('CHANNEL_ID'), text=user_message)

        # Send the message with the link, copyable link, and button
        await update.message.reply_text(
            f"👇👇 YOUR VIDEO LINK IS READY, USE THESE SERVERS 👇👇\n\n♥ 👇Your Stream Link👇 ♥\n",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Please send Me Only TeraBox Link.")

# Define the /broadcast command handler
async def broadcast(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id in admin_ids:
        message = update.message.reply_to_message
        if message:
            total_users = len(users)
            sent_count = 0
            block_count = 0
            fail_count = 0

            for user_id in users:
                try:
                    if message.photo:
                        await context.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id, caption=message.caption)
                    elif message.video:
                        await context.bot.send_video(chat_id=user_id, video=message.video.file_id, caption=message.caption)
                    else:
                        await context.bot.send_message(chat_id=user_id, text=message.text)
                    sent_count += 1
                except Exception as e:
                    if 'blocked' in str(e):
                        block_count += 1
                    else:
                        fail_count += 1

            await update.message.reply_text(
                f"Broadcast completed!\n\n"
                f"Total users: {total_users}\n"
                f"Messages sent: {sent_count}\n"
                f"Users blocked the bot: {block_count}\n"
                f"Failed to send messages: {fail_count}"
            )
        else:
            await update.message.reply_text("Please reply to a message with /broadcast to send it to all users.")
    else:
        await update.message.reply_text("You Have No Rights To Use My Commands")


async def check_verification(user_id: int) -> bool:
    user = users_collection.find_one({"user_id": user_id})
    if user and user.get("verified_until", datetime.min) > datetime.now():
        return True
    return False

async def get_token(user_id: int, bot_username: str) -> str:
    # Generate a random token
    token = os.urandom(16).hex()
    # Update user's verification status in database
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"token": token, "verified_until": datetime.min}},  # Reset verified_until to min
        upsert=True
    )
    # Create verification link
    verification_link = f"https://telegram.me/{bot_username}?start={token}"
    # Shorten verification link using shorten_url_link function
    shortened_link = shorten_url_link(verification_link)
    return shortened_link

def shorten_url_link(url):
    api_url = 'https://clickspay.in/api'
    api_key = '2be0849743f9dae76487a66551105da32b68165f'
    params = {
        'api': api_key,
        'url': url
    }
    # Yahan pe custom certificate bundle ka path specify karo
    response = requests.get(api_url, params=params, verify=False)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success':
            logger.info(f"Adrinolinks shortened URL: {data['shortenedUrl']}")
            return data['shortenedUrl']
    logger.error(f"Failed to shorten URL with Adrinolinks: {url}")
    return url

def main() -> None:
    # Get the port from the environment variable or use default
    port = int(os.environ.get('PORT', 8080))  # Default to port 8080
    webhook_url = f"https://total-jessalyn-toxiccdeveloperr-36046375.koyeb.app/{TOKEN}"  # Replace with your server URL

    # Create the Application and pass it your bot's token
    app = ApplicationBuilder().token(TOKEN).build()

    # Register the /start command handler
    app.add_handler(CommandHandler("start", start))

    # Register the /users command handler
    app.add_handler(CommandHandler("users", users_count))

    # Register the link handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    # Register the /broadcast command handler
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Run the bot using a webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
