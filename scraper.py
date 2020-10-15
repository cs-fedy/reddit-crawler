import psycopg2
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from dotenv import load_dotenv
import requests
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
    def __init__(self):
        self.page_url = 'https://free-proxy-list.net/'
        self.browser = self.browser = create_headless_browser()

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
    @staticmethod
    def __get_communities_data(names):
        communities_data = []
        for community_name in names:
            communities_data.append(ScrapCommunity(community_name))
        return communities_data

    def __call__(self):
        names = ScrapeCommunitiesNames().get_names()
        communities_data = self.__get_communities_data(names)
        # * store data in postgresql db:
        DB(communities_data)


class ScrapeCommunitiesNames:
    def __init__(self):
        self.url = 'https://www.reddit.com/subreddits/'

    @staticmethod
    def __get_category_names(link):
        source_code = requests.get(link, timeout=2).content
        soup = BeautifulSoup(source_code, 'html.parser')
        return [link.getText() for link in soup.select('.community-link')]

    def get_names(self):
        # * Get categories urls:
        urls = [f'{self.url}{chr(index + 97)}-1' for index in range(26)]
        urls.append(f'{self.url}0-1')

        # * Get communities Names:
        communities_names = []
        for category_url in urls:
            communities_names += self.__get_category_names(category_url)
        return communities_names


class ScrapCommunity:
    def __init__(self, community_name):
        self.community_name = community_name
        self.scroll_level = 2
        self.__get_data()

    @staticmethod
    def __get_posts_data(content):
        post_ids, posts = content['postIds'], content['posts']
        data = []
        for post_id in post_ids:
            post = posts[post_id]
            data.append({
                'post_title': post['title'],
                'post_link': post['permalink'],
                'post': post['media']['markdownContent']
            })

        return post_ids[-1], data

    @staticmethod
    def __get_community_details(details):
        details_value = details.values()[0]
        return {
            'description': details_value['publicDescription'],
            'members_count': details_value['subscribers']
        }

    def __get_data(self):
        url = f'https://gateway.reddit.com/desktopapi/v1/subreddits/{self.community_name}?sort=hot'
        content = requests.get(url, timeout=2).json()
        community_details = self.__get_community_details(content['subredditAboutInfo'])
        last_id, data = self.__get_posts_data(content)
        for _ in range(self.scroll_level):
            url += f'&after={last_id}'
            content = requests.get(url, timeout=2).json()
            last_id, scroll_data = self.__get_posts_data(content)
            data.extend(scroll_data)
        return {
            'community_name': self.community_name,
            'community_details': community_details,
            'community_data': data
        }


if __name__ == '__main__':
    cr = CrawlReddit()
