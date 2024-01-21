import logging
import requests
import os
import sqlite3
import pandas as pd


logger = logging.getLogger(__name__)


def select(query: str, db_path: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(query, conn)


def insert(table_name: str, db_path: str, table: pd.DataFrame):
    with sqlite3.connect(db_path) as conn:
        return table.to_sql(table_name, conn, if_exists="append", index=False)


def download_image(url: str, saving_path: str):
    logger.info(f"Downloading image, url = {url}")
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        os.makedirs(os.path.dirname(saving_path), exist_ok=True)
        with open(saving_path, "wb") as fout:
            for chunk in r:
                fout.write(chunk)
