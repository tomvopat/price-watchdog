# Price Watchdog

Watchdog fetches prices of products configured in the database and sends a Telegram notification
when the price changes.

Configuration is stored in the TinyDB database which can be configured independently through the
command line.

Populate the database with following structures in tables 'dogs' and 'telegrams':

## Database Documents

Populate TinyDB with following structures in order to run the watchdog.

```python
from tinydb import TinyDB

db = TinyDB('db.json')

telegrams = db.table('telegrams')
telegrams.insert({ ... })

dogs = db.table('dogs')
dogs.insert({ ... })
```

Selector column is CSS selector. See [BeatifulSoup documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property)

### Dogs table document

```json
dogs = [
    {
        'name': '',
        'url': '',
        'selector': '',
        'price': 0
    }
]
```

### Telegrams table document

```json
telegrams = [
    {
        'api_url': '',
        'bot_url': '',
        'token': '',
        'chat_id': 0
    }
]
```
