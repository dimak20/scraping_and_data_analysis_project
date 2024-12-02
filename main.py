import logging
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

driver = webdriver.Chrome()
driver.get("https://jobs.dou.ua/vacancies/?category=Python")
more_button = driver.find_element(
    By.CLASS_NAME,
    "more-btn"
)
while more_button:
    try:
        WebDriverWait(
            driver,
            1
        ).until(
            ec.element_to_be_clickable(
                (
                    By.CLASS_NAME,
                    "more-btn"
                )
            )
        )
        link = more_button.find_element(By.TAG_NAME, "a")

        link.click()
        time.sleep(1)
    except Exception as e:
        logging.info(f"An error occurred during touch scraping {e}")
        break
