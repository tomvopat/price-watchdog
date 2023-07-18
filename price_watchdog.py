"""This module scrapes prices from websites and sends notifications with updates"""
import logging
import argparse
import time
from tinydb import TinyDB
from bs4 import BeautifulSoup
import requests

parser = argparse.ArgumentParser(
        prog='Price Watchdog',
        description='The pricewatch dog checks configured products and sends \
                a notification if the price was updated.')
parser.add_argument('--log-file', help='File to store program logs')
parser.add_argument('--log-level', choices=['DEBUG', 'WARNING', 'ERROR'], default='WARNING',
                    help='Level of logging')
parser.add_argument('--db-file', default='db.json', help='TinyDB database file')
parser.add_argument('--sleep', type=int, default=100,
                    help='Sleep between watchdog fetches. In miliseconds')
args = parser.parse_args()

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/114.0.0.0 Safari/537.36'
}
TELEGRAMS_TABLE_NAME = 'telegrams'
WATCHDOGS_TABLE_NAME = 'dogs'

def get_log_level(log_level_str):
    """Function to return corresponding logging value for log-level user input."""
    if log_level_str == 'DEBUG':
        return logging.DEBUG
    if log_level_str == 'WARNING':
        return logging.WARNING
    if log_level_str == 'ERROR':
        return logging.ERROR
    return None

def notify(contacts, content):
    """Send a notification to users via Telegram."""
    logging.debug("notification: %s", content)
    for contact in contacts:
        url = f'{contact["api_url"]}/bot{contact["token"]}/sendMessage'
        body = {'chat_id': contact['chat_id'], 'text': content}
        response = requests.post(url, body)
        if response.status_code != 200:
            logging.error("Failed to send a notification: %s", str(response))

def parse_price(price_str):
    """Parse price as a float from a dirty string containing extra characters
    and whitespaces"""
    price_str = price_str.replace(',', '.')
    price_str = price_str.replace('$', '')
    price_str = price_str.replace('€', '')
    price_str = price_str.strip()
    return float(price_str)

log_level = get_log_level(args.log_level)
logging.basicConfig(filename=args.log_file, level=log_level, format=LOG_FORMAT)

db = TinyDB(args.db_file)
table_telegrams = db.table(TELEGRAMS_TABLE_NAME)
telegrams = table_telegrams.all()
table_dogs = db.table(WATCHDOGS_TABLE_NAME)
dogs = table_dogs.all()

for dog in dogs:
    page = requests.get(dog['url'], headers=REQUEST_HEADERS)
    if page.status_code != 200:
        logging.error("failed to scrape: %s", str(page))
        notify(telegrams, f'Failed to scrape: {dog["name"]}')
        continue

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.select(dog['selector'])

    logging.debug("scrape result: %s", str(results))
    if len(results) == 0:
        logging.warning("no results: %s", dog['name'])
        notify(telegrams, f"No results: {dog['name']}")
    elif len(results) > 1:
        logging.warning("multiple results for %s: %s", dog['name'], str(results))
        notify(telegrams, f"WARNING: multiple results for {dog['name']}")

    for result in results:
        new_price = parse_price(result.text)
        logging.debug("%s: %s", dog['name'], str(dog['price']))

        if dog['price'] != new_price:
            table_dogs.update({'price': new_price}, doc_ids = [dog.doc_id])
            MESSAGE = f"""{dog['name']}
    - old price: {dog['price']}e
    - new price: {new_price}e
    {dog['url']}"""
            notify(telegrams, MESSAGE)

    time.sleep(args.sleep / 1000)
