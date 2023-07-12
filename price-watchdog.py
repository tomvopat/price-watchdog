import requests
from bs4 import BeautifulSoup
from tinydb import TinyDB
import logging
import argparse
import time

parser = argparse.ArgumentParser(
        prog='Price Watchdog',
        description='The pricewatch dog checks configured products and sends \
                a notification if the price was updated.')
parser.add_argument('--log-file', help='File to store program logs')
parser.add_argument('--log-level', choices=['DEBUG', 'WARNING', 'ERROR'], default='WARNING', help='Level of logging')
parser.add_argument('--db-file', default='db.json', help='TinyDB database file')
parser.add_argument('--sleep', type=int, default=100, help='Sleep between watchdog fetches. In miliseconds')
args = parser.parse_args()

log_format = '%(asctime)s - %(levelname)s - %(message)s'
request_headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
telegrams_table_name = 'telegrams'
watchdogs_table_name = 'dogs'

def get_log_level(log_level_str):
    if args.log_level == 'DEBUG':
        return logging.DEBUG
    elif args.log_level == 'WARNING':
        return logging.WARNING
    elif args.log_level == 'ERROR':
        return logging.ERROR
    else:
        return None

def notify(telegrams, message):
    logging.debug("notification: {}".format(message))
    for telegram in telegrams:
        url = '{}/bot{}/sendMessage'.format(telegram['api_url'], telegram['token'])
        body = {'chat_id': telegram['chat_id'], 'text': message}
        response = requests.post(url, body)
        if response.status_code != 200:
            logging.error("Failed to send a notification", response)

def parse_price(price_str):
    price_str = price_str.replace(',', '.')
    price_str = price_str.replace('$', '')
    price_str = price_str.replace('€', '')
    price_str = price_str.strip()
    return float(price_str)

log_level = get_log_level(args.log_level)
logging.basicConfig(filename=args.log_file, level=log_level, format=log_format)

db = TinyDB(args.db_file)
table_telegrams = db.table(telegrams_table_name)
telegrams = table_telegrams.all()
table_dogs = db.table(watchdogs_table_name)
dogs = table_dogs.all()

for dog in dogs:
    page = requests.get(dog['url'], headers=request_headers)
    if page.status_code != 200:
        logging.error("failed to scrape: {}".format(page))
        notify(telegrams, "Failed to scrape: {}".format(dog['name']))
        continue

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.select(dog['selector'])

    logging.debug("scrape result: {}".format(results))
    if len(results) == 0:
        logging.warning("no results: {}".format(dog['name']))
        notify(telegrams, "No results: {}".format(dog['name']))
    elif len(results) > 1:
        logging.warning("multiple results for {}: {}".format(dog['name'], results))
        notify(telegrams, "WARNING: multiple results for {}".format(dog['name']))

    for result in results:
        new_price = parse_price(result.text)
        logging.debug("{}: {}".format(dog['name'], dog['price']))

        if(dog['price'] != new_price):
            table_dogs.update({'price': new_price}, doc_ids = [dog.doc_id])
            message = "{}\n\t- old price: {}e\n\t- new price: {}e\n\t{}".format(dog['name'], dog['price'], new_price, dog['url'])
            notify(telegrams, message)

    time.sleep(args.sleep / 1000)
