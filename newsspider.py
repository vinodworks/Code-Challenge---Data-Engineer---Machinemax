from urllib.parse import urlparse
from newspy.items import ArticleItem
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import newsspider


class bbcSpider(CrawlSpider):
    name = 'bbc'
    rules = (
        Rule(
            LinkExtractor(allow=(), unique=True),
            callback='parse_item',
            follow=True
        ),
    )
    start_urls = []
    allowed_domains = []

    def __init__(self, filename=None, url=None):
        super(bbcSpider, self).__init__()

        # Either URL or a file with URLs has to be provided
        if filename:
            with open(filename, 'r') as f:
                self.start_urls = [url.strip() for url in f.readlines()]
            self.allowed_domains = [urlparse(url).hostname.lstrip('www.bbc.com') for url in self.start_urls]
        elif url:
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://{}/'.format(url)
            self.start_urls = [url]
            self.allowed_domains = [urlparse(url).hostname.lstrip('www.')]

    def parse_item(self, response):
        # to tell article pages from digests/ads/videos
        page_type = response.xpath("//meta[@property='og:type']/@content").extract_first()

        if page_type == 'article':
            item = ArticleItem()
            item['url'] = response.url
            item['title'] = response.xpath("//meta[@property='og:title']/@content").extract_first() or \
                            response.xpath("//h1[@itemprop='headline']/text()").extract_first()
            item['description'] = response.xpath("//meta[@property='og:description']/@content").extract_first()
            item['author'] = response.xpath("//meta[@property='article:author']/@content").extract_first()
            item['section'] = response.xpath("//meta[@property='article:section']/@content").extract_first()
            item['keywords'] = response.xpath("//meta[@name='keywords']/@content").extract_first()

            text_contents = response.xpath("//div[@itemprop='articleBody' or @property='articleBody']/p").extract()
            item['text'] = re.sub(r'<.*?>', '', ' '.join(text_contents)).strip() if text_contents else None

            return item