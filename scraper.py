import psycopg2
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from dotenv import load_dotenv
import os
import time

load_dotenv()

# TODO: use IP Rotation
# TODO: Set a Real User Agent
# TODO: Set Other Request Headers
# TODO: Set Random Intervals In Between Requests
# TODO: Set a Referrer
# TODO: save scraped data in a db


def create_headless_browser():
    options = Options()
    options.add_argument('--headless')
    assert options.headless  # assert Operating in headless mode
    return webdriver.Chrome(options=options)


def load_full_page(browser, page_url):
    browser.get(page_url)
    time.sleep(2)
    print(f'@@@ {page_url} is loaded @@@')
    return browser.page_source


class ScrapeProxies:
    def __init__(self, browser):
        self.page_url = 'https://free-proxy-list.net/'
        self.browser = browser

    @staticmethod
    def __get_table_proxies(source_code):
        soup = BeautifulSoup(source_code, 'html.parser')
        table_rows = soup.select('#proxylisttable tbody tr')
        proxies = []
        for row in table_rows:
            columns = row.findAll("td")
            if columns[-2].getText() == 'yes' and columns[-4].getText() == 'elite proxy':
                proxies.append(f'https://{columns[0].getText()}:{columns[1].getText()}')
        return proxies

    def __get_proxies(self):
        next_button = self.browser.find_element(value='proxylisttable_next')
        proxies = []
        while 'disabled' not in next_button.get_attribute('class'):
            source_code = self.browser.page_source
            tables_proxies = self.__get_table_proxies(source_code)
            proxies.extend(tables_proxies)
            next_button.find_element_by_tag_name("a").click()
            next_button = self.browser.find_element(value='proxylisttable_next')
        return proxies

    def get_data(self):
        self.browser.get(self.page_url)
        time.sleep(1)
        return self.__get_proxies()


class DB:
    def __init__(self, data):
        self.data = data
        self.__POSTGRES_DB = os.getenv("POSTGRES_DB")
        self.__POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        self.__POSTGRES_USER = os.getenv("POSTGRES_USER")
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(user=self.__POSTGRES_USER,
                                               password=self.__POSTGRES_PASSWORD,
                                               host="127.0.0.1",
                                               port="5432",
                                               database=self.__POSTGRES_DB)
            self.cursor = self.connection.cursor()
            print("connected to db successfully")
        except (Exception, psycopg2.Error) as error:
            raise Exception(f"failed to connect to db {error}")

    def close_connection(self):
        self.cursor.close()
        self.connection.close()
        print("PostgreSQL connection is closed")

    def drop_tables(self, tables_names):
        for table_name in tables_names:
            drop_table_query = f"DROP TABLE IF EXISTS {table_name} CASCADE"
            self.cursor.execute(drop_table_query)
            self.connection.commit()
            print(f"table {table_name} dropped")


class CrawlReddit:
    def __init__(self):
        self.browser = create_headless_browser()
        self.proxies = ScrapeProxies(self.browser).get_data()

    def __create_headless_browser_proxy(self):
        current_proxy, browser = self.proxies[-1], None
        try:
            print(f'@@@ trying {current_proxy} @@@')
            browser = webdriver.Chrome()
        except:
            print(f'@@@ failed connecting to {current_proxy} @@@')
            self.proxies.pop()
            self.__create_headless_browser_proxy()
        return browser

    def __get_communities_data(self, urls):
        communities_data = []
        for community_url in urls:
            browser = self.__create_headless_browser_proxy()
            communities_data.append(ScrapCommunity(community_url, browser))
        return communities_data

    def __call__(self):
        urls = ScrapeCommunitiesURLS(self.browser)
        communities_data = self.__get_communities_data(urls)
        # * store data in postgresql db:
        DB(communities_data)


class ScrapeCommunitiesURLS:
    def __init__(self, browser):
        self.url = 'https://www.reddit.com/subreddits/'
        self.browser = browser
        self.__get_urls()

    def __get_category_urls(self, link):
        source_code = load_full_page(self.browser, link)
        soup = BeautifulSoup(source_code, 'html.parser')
        return [link['href'] for link in soup.select('.community-link')]

    def __get_urls(self):
        # * Get categories urls:
        urls = [f'{self.url}{chr(index + 97)}-1' for index in range(26)]
        urls.append(f'{self.url}0-1')

        # * Get communities urls:
        communities_urls = []
        for category_url in urls:
            communities_urls += self.__get_category_urls(category_url)
        return communities_urls


class ScrapCommunity:
    def __init__(self, communityURL, browser):
        self.browser = browser
        self.communityURL = communityURL
        self.scroll_level = 2
        self.__get_data()

    def __create_headless_browser(self):
        pass

    def __scroll_page(self):
        scrolling_script = "window.scrollTo(0,document.body.scrollHeight)"
        self.browser.execute_script(scrolling_script)
        time.sleep(1)
        print("@@@ page is fully loaded @@@")

    @staticmethod
    def __get_community_details(source_code):
        soup = BeautifulSoup(source_code, 'html.parser')
        description_element = soup.select_one("div[data-redditstyle=true]")
        details_element = description_element.next_sibling()
        return {
            'description': description_element.getText(),
            'members_count': details_element[0].getText()
        }

    def __get_posts_urls(self):
        for _ in range(self.scroll_level):
            self.__scroll_page()
        soup = BeautifulSoup(self.browser.page_source, 'html.parser')
        return [
            f"https://www.reddit.com{link['href']}"
            for link in soup.select('a[data-click-id=body]')
        ]

    def __scrape_post_details(self, post_url):
        # TODO: for post content check if it contains images, links, lists or texts and parse each of them
        source_code = load_full_page(self.browser, post_url)
        soup = BeautifulSoup(source_code, 'html.parser')
        post_title = soup.select_one('div[data-test-id=post-content] h1').getText()
        content = " ".join(p.getText() for p in soup.select('div[data-test-id=post-content] p'))
        return {
            'title': post_title,
            'content': content.strip()
        }

    def __get_posts_data(self, urls):
        return [self.__scrape_post_details(post_url) for post_url in urls]

    def __get_data(self):
        source_code = load_full_page(self.browser, self.communityURL)
        posts_urls = self.__get_posts_urls()
        return self.__get_posts_data(posts_urls)
        

if __name__ == '__main__':
    cr = CrawlReddit()