from typing import Dict
import yaml
import logging
import sqlite3
import time
from dataclasses import asdict

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import parser
import telegram


def main(config: Dict, secrets: Dict):
    bot = telegram.Bot(token=secrets["tg_bot_token"], chat_ids=secrets["chat_ids"])
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

    scheduler = BlockingScheduler()
    posting_trigger = CronTrigger(
        day_of_week="*", hour="*", minute=f'*/{config["run_every_n_minute"]}'
    )
    main(config, secrets)
    scheduler.add_job(main, posting_trigger, args=(config, secrets), max_instances=1)
    scheduler.start()
