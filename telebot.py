import logging
import sqlite3
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, InlineQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import uuid

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize SQLite database connection
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create table for storing messages if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT UNIQUE COLLATE NOCASE, message TEXT)''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        'Welcome to the bot! You can save a message under a title, retrieve it, or delete it later. '
        'Use /help to see available commands.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    await update.message.reply_text(
        'Available commands:\n'
        '/start - Start the bot and see the welcome message\n'
        '/help - Get the list of available commands\n'
        '/get <Title> - Retrieve a saved message by its title\n'
        '/delete <Title> - Delete a saved message by its title\n\n'
        'To save a message, type a title followed by your message (e.g., "Title: Your message").'
    )

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save a message under a given title."""
    text = update.message.text
    if ':' in text:
        title, message = text.split(':', 1)
        title = title.strip()
        message = message.strip()
        try:
            cursor.execute("INSERT INTO messages (title, message) VALUES (?, ?)", (title, message))
            conn.commit()
            await update.message.reply_text(f'Message saved under title "{title}".')
        except sqlite3.IntegrityError:
            await update.message.reply_text(f'A message with the title "{title}" already exists. Please choose a different title.')
    else:
        await update.message.reply_text(
            'Please provide a title and a message separated by a colon (e.g., "Title: Your message").'
        )

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve a message by its title (case insensitive)."""
    if len(context.args) > 0:
        title = ' '.join(context.args).strip()
        cursor.execute("SELECT message FROM messages WHERE title = ?", (title,))
        result = cursor.fetchone()
        if result:
            await update.message.reply_text(f'Message under title "{title}": {result[0]}')
        else:
            await update.message.reply_text(f'No message found under title "{title}".')
    else:
        await update.message.reply_text('Please provide a title to retrieve the message (e.g., "/get Title").')

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a message by its title (case insensitive)."""
    if len(context.args) > 0:
        title = ' '.join(context.args).strip()
        cursor.execute("DELETE FROM messages WHERE title = ?", (title,))
        conn.commit()
        if cursor.rowcount > 0:
            await update.message.reply_text(f'Message under title "{title}" has been deleted.')
        else:
            await update.message.reply_text(f'No message found under title "{title}".')
    else:
        await update.message.reply_text('Please provide a title to delete the message (e.g., "/delete Title").')

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline query to search for messages by title."""
    query = update.inline_query.query.strip()
    results = []

    if query:
        cursor.execute("SELECT title, message FROM messages WHERE title LIKE ?", ('%' + query + '%',))
        rows = cursor.fetchall()
        for row in rows:
            title, message = row
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=title,
                    input_message_content=InputTextMessageContent(f'Message under title "{title}": {message}')
                )
            )
    
    await update.inline_query.answer(results)

def main() -> None:
    """Start the bot."""
    # Get the bot token from environment variables
    token = os.getenv('TOKEN')

    # Create the ApplicationBuilder and pass the bot token
    application = ApplicationBuilder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get", get_message))
    application.add_handler(CommandHandler("delete", delete_message))

    # Add message handler to save messages under titles
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))

    # Add inline query handler
    application.add_handler(InlineQueryHandler(inline_query))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
