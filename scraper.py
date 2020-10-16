import psycopg2
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from dotenv import load_dotenv
from random import randint
import tabulate
import requests
import os
import time

load_dotenv()


# TODO: Set a Real User Agent
# TODO: Set Other Request Headers
# TODO: Set a Referrer


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
                proxies.append({
                    'requests_count': 0,
                    'start_time': None,
                    'proxy': f'https://{columns[0].getText()}:{columns[1].getText()}'
                })
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
        self.__connect()
        self.__drop_tables(['post', 'subreddit'])
        self.__create_tables()
        self.__seed_db()
        self.__close_connection()

    def __connect(self):
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

    def __close_connection(self):
        self.cursor.close()
        self.connection.close()
        print("PostgreSQL connection is closed")

    def __drop_tables(self, tables_names):
        for table_name in tables_names:
            drop_table_query = f"DROP TABLE IF EXISTS {table_name} CASCADE"
            self.cursor.execute(drop_table_query)
            self.connection.commit()
            print(f"table {table_name} dropped")

    def __create_tables(self):
        queries = []
        # subreddit(subreddit_name_, subreddit_description, members_count)
        subreddit_table_query = """
            CREATE TABLE subreddit(
                subreddit_name TEXT PRIMARY KEY,
                subreddit_description TEXT,
                members_count NUMBER); 
        """
        queries.append((subreddit_table_query, "subreddit"))

        # post(post_id_, sub_reddit_name#, post_title, post_url, post_content)
        post_table_query = """
            CREATE TABLE post(
                post_id TEXT PRIMARY KEY,
                sub_reddit_name TEXT NOT NULL,
                post_url TEXT,
                post_title TEXT,
                post_content TEXT,
                FOREIGN KEY sub_reddit_name REFERENCES subreddit(subreddit_name)); 
        """
        queries.append((post_table_query, "post"))

        # * tables creation
        for query in queries:
            query_text, table_name = query
            self.cursor.execute(query_text)
            self.connection.commit()
            print(f"Table {table_name} created successfully in PostgreSQL ")

    def __get_rows(self, table_name):
        row_select_query = f"SELECT * FROM {table_name}"
        self.cursor.execute(row_select_query)
        return [row for row in self.cursor.fetchall()]

    def __get_columns(self, table_name):
        columns_select_query = f"SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}';"
        self.cursor.execute(columns_select_query)
        return [col[0] for col in self.cursor.fetchall()]

    def __show_data(self, table_name):
        rows = self.__get_rows(table_name)
        columns = self.__get_columns(table_name)
        print("=" * 28, f"@ rows in {table_name} table @", "=" * 28)
        print(tabulate.tabulate(rows, headers=columns, tablefmt="psql"))
        print("\n")

    def __seed_subreddit_table(self, data):
        community_name, description, members_count = data.items()
        seeding_subreddit_query = """ 
                INSERT INTO subreddit (subreddit_name, subreddit_description, members_count)  
                VALUES (%s, %s, %s)
        """
        self.cursor.execute(seeding_subreddit_query, (community_name, description, members_count))
        self.connection.commit()
        print(f"seeding subreddit table with {community_name} details")

    def __seed_post_table(self, data, subreddit_name):
        post_id, post_title, post_link, post = data.items()
        # post(post_id_, sub_reddit_name#, post_title, post_url, post_content)
        seeding_post_query = """ 
                INSERT INTO subreddit (post_id, sub_reddit_name, post_title, post_url, post_content)  
                VALUES (%s, %s, %s, %s, %s)
        """
        self.cursor.execute(seeding_post_query, (post_id, subreddit_name, post_link, post))
        self.connection.commit()
        print(f"seeding post table with {post_id} details")

    def __seed_db(self):
        for subreddit in self.data:
            self.__seed_subreddit_table(subreddit['community_details'])
            self.__seed_post_table(subreddit['community_data'],
                                   subreddit['community_details']['community_name'])


class CrawlReddit:
    def __init__(self):
        self.proxies = ScrapeProxies().get_data()

    def __get_communities_data(self, names):
        communities_data = []
        for community_name in names:
            community_data = ScrapCommunity(community_name, self.proxies).get_data()
            communities_data.append(community_data)
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
    def __init__(self, community_name, proxies):
        self.community_name = community_name
        self.proxies = proxies
        self.scroll_level = 2

    @staticmethod
    def __get_posts_data(content):
        post_ids, posts = content['postIds'], content['posts']
        data = []
        for post_id in post_ids:
            post = posts[post_id]
            data.append({
                'post_id': post_id,
                'post_title': post['title'],
                'post_link': post['permalink'],
                'post': post['media']['markdownContent']
            })

        return post_ids[-1], data

    def __get_community_details(self, details):
        details_value = details.values()[0]
        return {
            'community_name': self.community_name,
            'description': details_value['publicDescription'],
            'members_count': details_value['subscribers']
        }

    def __set_proxy(self, url):
        current_proxy, request = self.proxies[-1], None
        try:
            print(f'@@@ trying {current_proxy.proxy} @@@')
            # * If current max request number is reached use another proxy:
            if current_proxy['requests_count'] > 450 or \
                    time.time() - current_proxy['start_time'] > 3600:
                print(f'@@@ proxy {current_proxy.proxy} failed @@@')
                self.proxies.pop()
                self.__set_proxy(url)
            proxies = {
                'http': current_proxy['proxy'],
                'https': current_proxy['proxy'],
            }
            request = requests.get(url, timeout=5, proxies=proxies)
            if self.proxies[-1]['requests_count'] == 0:
                self.proxies[-1]['start_time'] = time.time()
            self.proxies[-1]['requests_count'] += 1
            random_delay = randint(0, 10)
            time.sleep(random_delay)
        except:
            print(f'@@@ proxy {current_proxy.proxy} failed @@@')
            self.proxies.pop()
            self.__set_proxy(url)
        return request.json()

    def get_data(self):
        url = f'https://gateway.reddit.com/desktopapi/v1/subreddits/{self.community_name}?sort=hot'
        content = content = self.__set_proxy(url)
        community_details = self.__get_community_details(content['subredditAboutInfo'])
        last_id, data = self.__get_posts_data(content)
        for _ in range(self.scroll_level):
            url += f'&after={last_id}'
            content = self.__set_proxy(url)
            last_id, scroll_data = self.__get_posts_data(content)
            data.extend(scroll_data)
        return {
            'community_details': community_details,
            'community_data': data
        }


if __name__ == '__main__':
    cr = CrawlReddit()
