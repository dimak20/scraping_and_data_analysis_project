import json
import logging
import re
import time
from typing import Iterable

import scrapy
from scrapy import Request
from scrapy.http import Response, TextResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

chrome_options = Options()
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/85.0.4183.121 Safari/537.36"
)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_argument("--incognito")

VACANCY_CSS = "li.l-vacancy"
VACANCY_URL = "a.vt::attr(href)"
VACANCY_TITLE = "h1.g-h2::text"
VACANCY_LOCATION = "span.place.bi::text"
VACANCY_COMPANY = "div.l-n a::text"
VACANCY_SALARY = "span.salary::text"
VACANCY_DESCRIPTION = "div.b-typo.vacancy-section"


class JobVacancyItem(scrapy.Item):
    title = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    salary = scrapy.Field()
    description = scrapy.Field()
    technologies = scrapy.Field()
    experience = scrapy.Field()


class DouSpider(scrapy.Spider):
    name = "dou_spider"
    allowed_domains = ["jobs.dou.ua"]
    start_urls = ["https://jobs.dou.ua/vacancies/?category=Python"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.technologies = self.load_technologies("technologies.json")
        self.exp = ["1-3", "3-5", "5plus"]
        self.driver = webdriver.Chrome(options=chrome_options)

    def load_technologies(self, file_path: str) -> list[str]:
        with open(file_path, "r") as file:
            return json.load(file)

    def start_requests(self) -> Iterable[Request]:
        for level in self.exp:
            url = f"{self.start_urls[0]}&exp={level}"
            self.driver.get(url)
            while True:
                try:
                    more_button = WebDriverWait(self.driver, 10).until(
                        ec.element_to_be_clickable((By.CLASS_NAME, "more-btn"))
                    )
                    link = more_button.find_element(By.TAG_NAME, "a")
                    link.click()
                    time.sleep(1)
                except Exception as e:
                    logging.info(f"An error occurred {e}")

            html = self.driver.page_source
            response = TextResponse(url=url, body=html, encoding="utf-8")
            yield from self.parse(response, level)

    def close(self, reason: str):
        self.driver.quit()

    def parse(self, response: Response, level: str, **kwargs) -> Response:
        for vacancy in response.css(VACANCY_CSS):
            url = vacancy.css(VACANCY_URL).get()
            if url:
                yield response.follow(
                    url, callback=self.parse_vacancy, meta={"experience": level}
                )

    def parse_vacancy(self, response: Response) -> JobVacancyItem:
        item = JobVacancyItem()

        item["title"] = response.css(VACANCY_TITLE).get()

        location_string = response.css(VACANCY_LOCATION).get()
        if location_string:
            item["location"] = [city.strip() for city in location_string.split(",")]

        item["company"] = response.css(VACANCY_COMPANY).get()

        salary = response.css(VACANCY_SALARY).get()
        if salary:
            salary = re.sub(r"\$", "", salary)

        item["salary"] = salary

        description = response.css(VACANCY_DESCRIPTION).getall()
        item["description"] = description

        cleaned_description = [text.strip() for text in description if text.strip()]
        string_description = "".join(cleaned_description).replace("\xa0", " ")

        found_technologies = [
            tech
            for tech in self.technologies
            if tech.lower() in string_description.lower()
        ]
        item["technologies"] = found_technologies

        item["experience"] = response.meta.get("experience")

        yield item
