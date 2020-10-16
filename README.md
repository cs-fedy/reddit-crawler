# reddit crawler:

I'm crawling reddit website, and i want to store them in a database(postgresql maybe). Also in this project i want to use technics related to database(IP Rotation, Real User Agent, Other Request Headers, Random Intervals In Between Requests and a Referrer).

**P.S: [docker](https://www.docker.com/) is required**

## installation:

1. clone the repo `git clone https://github.com/cs-fedy/reddit-crawler`
2. run `docker compose up -d` to start the db.
3. install virtualenv using pip: `sudo pip install virtualenv`
4. create a new virtualenv:  `virtualenv venv`
5. activate the virtualenv: `source venv/bin/activate`
6. install requirements: `pip install requirements.txt`
7. run the script and enjoy: `python scraper.py`

## used tools:

1. [selenium](https://www.selenium.dev/): Primarily it is for automating web applications for testing purposes, but is certainly not limited to just that. Boring web-based administration tasks can (and should) also be automated as well.
2. [BeautifulSoup](https://pypi.org/project/beautifulsoup4/): Beautiful Soup is a library that makes it easy to scrape information from web pages. It sits atop an HTML or XML parser, providing Pythonic idioms for iterating, searching, and modifying the parse tree.
3. [python-dotenv](https://pypi.org/project/python-dotenv/): Add .env support to your django/flask apps in development and deployments.
4. [psycopg2](https://pypi.org/project/psycopg2/): psycopg2 - Python-PostgreSQL Database Adapter.
5. [tabulate](https://pypi.org/project/tabulate/): Pretty-print tabular data.

## Scraping tips:

1. Do not follow the same crawling pattern: Incorporate some random clicks on the page, mouse movements and random actions that will make a spider look like a human.
2. Make requests through Proxies and rotate them as needed: Create a pool of IPs that you can use and use random ones for each request. Along with this, you have to spread a handful of requests across multiple IPs. [How to send requests through a Proxy in Python 3 using Requests](https://www.scrapehero.com/how-to-rotate-proxies-and-ip-addresses-using-python-3/).
3. Rotate User Agents and corresponding HTTP Request Headers between requests. [How to fake and rotate User Agents using Python 3
](https://www.scrapehero.com/how-to-fake-and-rotate-user-agents-using-python-3/).
4. Use a headless browser like Pyppeteer, Selenium or Playwright

## Author:
**created at 🌙 with 💻 and ❤ by f0ody**
* **Fedi abdouli** - **reddit crawler** - [fedi abdouli](https://github.com/cs-fedy)
* my twitter account [FediAbdouli](https://www.twitter.com/FediAbdouli)
* my instagram account [f0odyy](https://www.instagram.com/f0odyy)
