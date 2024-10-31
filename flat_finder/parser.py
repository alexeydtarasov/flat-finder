import requests
import os

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import datetime
import pandas as pd
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

import utils

logger = logging.getLogger(__name__)


@dataclass
class Metro:
    name: str
    distance: int
    distance_type: str


@dataclass
class Flat:
    href: str
    cian_id: int
    general_info: str
    metro: str
    address: str
    price: str
    about_money: str
    published_at: str
    parsed_at: Optional[datetime.datetime] = datetime.datetime.now()
    remont: str = None
    saved_images: List[str] = None
    additional_features: str = None
    cian_price: str = None


def general_info(bs: BeautifulSoup) -> Dict[str, str]:
    return {"general_info": bs.text}


def geo(bs: BeautifulSoup) -> Dict[str, str]:
    metro = bs.find("div", {"data-name": "SpecialGeo"})
    if metro is None:
        logger.error(f"Failed to parse metro, bs=\n{bs}")
        return {"metro": None, "address": None}
    metro = metro.find("a").text + ", " + metro.find_all("div")[-1].text
    address = bs.find_all("a", {"data-name": "GeoLabel"})
    address = ", ".join([addr.text for addr in address[4:]])
    return {"metro": metro, "address": address}


def about_money(bs: BeautifulSoup) -> Dict[str, str]:
    about_money = bs.text.replace("\xa0", "")
    price = about_money.split(".")[0]
    about_money = about_money.replace(price, "")[1:]
    return {"price": price, "about_money": about_money}

def publish_date(bs: BeautifulSoup) -> str:
    months_order = [
        'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
        'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь' 
    ]
    months_dict = {k: v for k, v in zip(range(1, 13), months_order)}
    published_at = (
        bs.find("div", {"data-name": "TimeLabel"}).find_all("div")[-1].text
    )
    if "вчера" in published_at:
        date = datetime.datetime.now() - datetime.timedelta(days=1)
        month = months_dict[date.month]
        published_at = published_at.replace("вчера", f"{date.day}, {month}")
    elif "сегодня" in published_at:
        date = datetime.datetime.now()
        month = months_dict[date.month]
        published_at = published_at.replace("сегодня", f"{date.day}, {month}")
    return published_at

def remont(bs: BeautifulSoup) -> str:
    remont_value = (
        bs.find('div', {'data-name': 'OfferSummaryInfoLayout'})
        .find("div", {"data-name": "OfferSummaryInfoGroup"})
        .find_all("div", {"data-name": "OfferSummaryInfoItem"})[-1]
        .find_all("p")[-1]
        .text
    )
    return remont_value

class Cian:
    def __init__(self, url: str, db_path: str):
        logger.info("Initialized Cian parser class")
        self.url = url
        self.db_path = db_path
        self.headers = {'User-Agent': UserAgent().random}
        logger.info(f'Generated user-agent: {self.headers}')

    def _get_query(self, url) -> BeautifulSoup:
        logger.info(f"Loading url: {url[:100]}")
        r = requests.get(url)
        if r is not None and r.status_code == 200:
            return BeautifulSoup(r.content, features="lxml")
        logger.error(f"Failed to load url: {url[:100]}")
        return None
    
    def parse_flat(self, bs: BeautifulSoup) -> Flat:
        result = dict()
        flat = bs.find("div", {"data-name": "LinkArea"})
        href = flat.find("a")["href"]
        result["href"] = href
        cian_id = int(href.split("/")[-2])
        result["cian_id"] = cian_id

        already_parsed = utils.select("select cian_id from flats", self.db_path)[
            "cian_id"
        ].values.tolist()

        if cian_id in already_parsed:
            return cian_id

        attrs = ["general_info", "geo", "about_money"]
        attrs_parsers = [general_info, geo, about_money]
        attrs_data = flat.find_all(
            "div", {"data-name": {"GeneralInfoSectionRowComponent"}}
        )
        if len(attrs_data) > 5:
            attrs_data.pop(1)
        for attr, parser_func, attr_data in zip(attrs, attrs_parsers, attrs_data):
            result.update(parser_func(attr_data))
        result["published_at"] = publish_date(bs)
        return Flat(**result)

    def full_flat_scan(self, flat: Flat, n_photos: int = 7):
        bs = self._get_query(url=flat.href)
        image_sources = list(
            map(
                lambda x: x["src"],
                bs.find("div", {"data-name": "GalleryInnerComponent"}).find_all("img"),
            )
        )
        saved_image_paths = []
        min_start_photo = min(len(image_sources), 4) - 1
        for img_source in image_sources[min_start_photo : min_start_photo + n_photos]:
            img_name = os.path.basename(img_source)
            base_path = '.'
            if os.getenv('PROD'):
                base_path = os.getenv('BASE_PATH')
            saving_path = os.path.join(base_path, f"data/images/{flat.cian_id}/{img_name}")
            utils.download_image(img_source, saving_path)
            saved_image_paths.append(saving_path)
            time.sleep(0.5)
        flat.saved_images = saved_image_paths

        target_features = [
            "Посудомоечная машина",
            "Кондиционер",
            "Ванна",
            "Душевая кабина",
            "Холодильник",
            "Стиральная машина",
            "Интернет",
            "Мебель на кухне",
            "Мебель в комнатах"
        ]
        additional_features = ", ".join(
            filter(
                lambda x: x in target_features,
                map(
                    lambda y: y.text.strip(),
                    bs.find("div", {"data-name": "FeaturesLayout"}).find_all(
                        "div", {"data-name": "FeaturesItem"}
                    ),
                ),
            )
        )
        flat.additional_features = additional_features
        try:
            flat.remont = remont(bs)
        except:
            flat.remont = None
        return flat

    def parse_page(self) -> List[Flat]:
        bs = self._get_query(self.url)
        flats = []
        flats_bs = bs.find("div", {"data-name": "SearchEngineResultsPage"}).find_all(
            "div", {"data-testid": "offer-card"}
        )
        for flat in flats_bs:
            parsed_flat = self.parse_flat(flat)
            if isinstance(parsed_flat, int):
                logger.info(f"Flat: {parsed_flat} was already parsed, skipping..")
            elif isinstance(parsed_flat, Flat):
                flats.append(parsed_flat)

        if len(flats) > 0:
            utils.insert(
                "flats",
                self.db_path,
                pd.DataFrame([asdict(flat) for flat in flats])[
                    ["cian_id", "parsed_at"]
                ],
            )
        else:
            logger.info(f"No flats were parsed in this iteration")
        return flats
