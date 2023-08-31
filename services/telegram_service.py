import time

import telegram
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from telegram.constants import ParseMode

logger = setup_logging(__name__)

TELEGRAM_TOKEN, CHAT_ID = get_secrets(["telegram/token", "telegram/chat_id"])
MAX_LENGTH_PER_MESSAGE = 4096 - 50


async def send_to_telegram(message):
    if len(message) < MAX_LENGTH_PER_MESSAGE:
        await telegram.Bot(TELEGRAM_TOKEN).send_message(
            chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML
        )
    else:
        messages_needed = len(message) // MAX_LENGTH_PER_MESSAGE + 1
        for i in range(messages_needed):
            temp = message[i * MAX_LENGTH_PER_MESSAGE: (i + 1) * MAX_LENGTH_PER_MESSAGE]
            await telegram.Bot(TELEGRAM_TOKEN).send_message(
                chat_id=CHAT_ID, text=temp, parse_mode=ParseMode.HTML
            )
            time.sleep(5)
