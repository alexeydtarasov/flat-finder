from typing import Dict
import yaml
import logging
import time
import sqlite3
import time
from dataclasses import asdict
from telebot import TeleBot

import parser
import telegram


def main(config: Dict, bot: TeleBot, secrets: Dict):
    bot = telegram.Bot(bot, chat_ids=secrets["chat_ids"])
    text_template = open("data/message_template.html").read().strip()
    cian = parser.Cian(url=config["url"], db_path=config["db_path"])
    flats = cian.parse_page()
    for flat in flats:
        flat = cian.full_flat_scan(flat)
        text = text_template.format(**asdict(flat))
        bot.send_photos(flat.saved_images)
        bot.send_message(text=text)
        time.sleep(10)
    time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s|%(levelname)s|%(message)s", level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info("Staring application")

    config = yaml.safe_load(open("config.yaml"))
    secrets = yaml.safe_load(open(".secrets.yaml"))

    create_tables_query = open("data/create_tables.sql").read()
    with sqlite3.connect("data/db.sqlite3") as conn:
        cursor = conn.cursor()
        cursor.executescript(create_tables_query)

    bot = TeleBot(secrets['tg_bot_token'])
    
    while True:
        main(config, bot, secrets)
        time.sleep(60)
