from bs4 import BeautifulSoup
from selenium import webdriver
import time

# TODO: use IP Rotation
# TODO: Set a Real User Agent
# TODO: Set Other Request Headers
# TODO: Set Random Intervals In Between Requests
# TODO: Set a Referrer
# TODO: save scraped data in a db


def create_headless_browser():
    # options = Options()
    # options.set_headless()
    # assert options.headless  # assert Operating in headless mode
    # return webdriver.Chrome(options=options)
    return webdriver.Chrome()


def load_full_page(browser, page_url):
    browser.get(page_url)
    time.sleep(2)
    print(f'@@@ {page_url} is loaded @@@')
    return browser.page_source


class ScrapeProxies:
    def __init__(self, browser=None):
        self.page_url = 'https://free-proxy-list.net/'
        if not browser:
            self.browser = create_headless_browser()
        else:
            self.browser = browser
        self.__get_data()

    @staticmethod
    def __get_table_proxies(source_code):
        soup = BeautifulSoup(source_code, 'html.parser')
        table_rows = soup.select('#proxylisttable tbody tr')
        proxies = []
        for row in table_rows:
            columns = row.findAll("td")
            if columns[-2].getText() == 'yes':
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

    def __get_data(self):
        self.browser.get(self.page_url)
        time.sleep(1)
        proxies = self.__get_proxies()


class ScrapeCommunitiesURLS:
    def __init__(self, browser=None):
        self.url = 'https://www.reddit.com/subreddits/'
        if not browser:
            self.browser = create_headless_browser()
        else:
            self.browser = browser
        self.proxies = ScrapeProxies(self.browser)

    def __get_category_urls(self, link):
        source_code = load_full_page(self.browser, link)
        soup = BeautifulSoup(source_code, 'html.parser')
        return [link['href'] for link in soup.select('.community-link')]

    def __call__(self):
        communities_urls = []
        for index in range(26):
            communities_category = f'{self.url}{chr(index + 97)}-1'
            communities_urls += self.__get_category_urls(communities_category)
        communities_urls += self.__get_category_urls(f'{self.url}0-1')
        return communities_urls


class ScrapCommunity:
    def __init__(self, communityURL, browser=None):
        self.communityURL = communityURL
        self.scroll_level = 2
        if not browser:
            self.browser = create_headless_browser()
        else:
            self.browser = browser

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

    def __call__(self):
        source_code = load_full_page(self.browser, self.communityURL)
        posts_urls = self.__get_posts_urls()
        

if __name__ == '__main__':
    headless_browser = create_headless_browser()
    url = 'https://www.reddit.com/r/pycharm/'
    sc = ScrapCommunity(url, headless_browser)
    print(sc())
