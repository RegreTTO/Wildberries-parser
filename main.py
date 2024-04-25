from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import argparse
import time
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
import openpyxl
import string

options = Options()
# options.add_argument("--headless")

SEARCH_URL = "https://www.wildberries.ru/catalog/0/search.aspx?search=%s"

flag_parser = argparse.ArgumentParser("Wildberries parser")
flag_parser.add_argument("product", help="Product name to be parsed")
flag_parser.add_argument("-n", required=True, help="number of pages to parse")


def scroll_until_end(driver: webdriver.Firefox):
    for i in range(20):
        driver.execute_script("window.scrollBy(0, 800);", "")
        time.sleep(0.2)


def get_products_from_page(page: int = 1) -> list[Tag]:
    driver = webdriver.Firefox(options=options)
    driver.implicitly_wait(10)
    driver.get(SEARCH_URL + f"&page={page}")
    time.sleep(2)
    scroll_until_end(driver)
    html = driver.page_source
    soup = bs(html, "html.parser")
    cards = soup.find("div", {"class": "product-card-list"}).find_all(
        "div", {"class": "product-card__wrapper"}
    )
    if len(cards) <= 1:
        return []
    driver.close()
    return cards


def parse(page_count: int = 1):
    products_bs: list[Tag] = []
    with tqdm(total=page_count) as pbar:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(get_products_from_page, i + 1)
                for i in range(0, page_count)
            ]
            for future in as_completed(futures):
                products_bs += future.result()
                pbar.update(1)

    products = [["Название", "Продавец", "Цена со скидкой, руб", "Цена без скидки, руб"]]
    for product in products_bs:
        name = (
            product.find("span", {"class": "product-card__name"})
            .text.replace("/", "")
            .strip()
        )
        price_without_discount = (
            product.find("p", {"class": "product-card__price price"}).find("del").text
        )
        price_with_discount = product.find("ins", {"class" : "price__lower-price wallet-price"}).text
        brand = product.find("span", {"class": "product-card__brand"}).text
        prod = [name, brand, price_with_discount, price_without_discount]
        for i in range(len(prod)):
            prod[i] = prod[i].replace("\xa0", "").replace("₽", "").strip()
        print(prod)
        products.append(prod)
    return products

if __name__ == "__main__":
    args = flag_parser.parse_args()
    SEARCH_URL %= args.product
    data = parse(int(args.n))
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in data:
        ws.append(row)
    wb.save("parsed.xlsx")
