from typing import Dict
import yaml
import logging
import time
import sqlite3
import time
from dataclasses import asdict
import os
from telebot import TeleBot

import parser
import telegram


def main(config: Dict, bot: TeleBot, secrets: Dict):
    bot = telegram.Bot(bot, chat_ids=secrets["chat_ids"])
    text_template = open(os.path.join(config['base_path'], "data/message_template.html")).read().strip()
    cian = parser.Cian(url=config["url"], db_path=os.path.join(config['base_path'], config["db_path"]))
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

    if os.getenv('PROD'):
        base_path = os.getenv('BASE_PATH')
        
    else:
        base_path = '.'

    logger.info(f'{base_path=}')
    logger.info(f'{os.listdir(base_path)}')
    config_path = os.path.join(base_path, "config.yaml")
    secrets_path = os.path.join(base_path, ".secrets.yaml")
    logger.info(f'{config_path=}, {secrets_path=}')
    config = yaml.safe_load(open(config_path))
    secrets = yaml.safe_load(open(secrets_path))

    create_tables_query = open(os.path.join(base_path, "data/create_tables.sql")).read()
    with sqlite3.connect(os.path.join(base_path, config['db_path'])) as conn:
        cursor = conn.cursor()
        cursor.executescript(create_tables_query)

    bot = TeleBot(secrets['tg_bot_token'])
    config['base_path'] = base_path
    while True:
        main(config, bot, secrets)
        time.sleep(60)
