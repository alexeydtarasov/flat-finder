from typing import List

import telebot

import os
import logging

logger = logging.getLogger(__name__)


class Bot:
    def __init__(self, bot: telebot.TeleBot, chat_ids: List[int]):
        logger.info("Initialized telegram-bot")
        self.bot = bot
        self.chat_ids = chat_ids

    def send_message(self, text: str, parse_mode="html"):
        for chat_id in self.chat_ids:
            logger.info(f"Sending message:\n{text}")
            self.bot.send_message(
                chat_id, text=text, parse_mode=parse_mode, disable_web_page_preview=True
            )

    def send_photos(self, saved_paths: List[str]):
        medias = []
        for photo_path in saved_paths:
            logger.info(f"Sending images: {saved_paths}")
            medias.append(
                telebot.types.InputMediaPhoto(media=open(photo_path, "rb").read())
            )
        for chat_id in self.chat_ids:
            self.bot.send_media_group(chat_id=chat_id, media=medias)
        
        os.system(f'rm -rf {os.path.dirname(saved_paths[0])}')
