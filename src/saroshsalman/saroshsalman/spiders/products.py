from scrapy.http import Request
from scrapy import Spider
import html
from scrapy.selector import Selector
import hashlib
import re
import math

class ProductsSpider(Spider):
    name = 'products'
    allowed_domains = ['saroshsalman.com']
    start_urls = ['http://saroshsalman.com/']
    custom_settings = {
        'FEEDS': {
            f'/tmp/data.csv': {
                'format': 'csv',
                'overwrite': True
            }
        }
    }

    def parse(self, response, **kwargs):
        urls = [url for url in response.css('a.action-bar__link::attr(href)').getall() if
                'collections' in url]
        for url in urls:
            yield response.follow(url, callback=self.parse_category)

    def parse_product(self, response, **kwargs):
        resp = response.json()

        description = html.unescape(resp['description']).replace('\xa0', '')
        selector = Selector(text=description)

        description = [feature.strip() for feature in selector.css('p::text').getall()]
        description = [feature for feature in description if feature != '']
        prefix = kwargs['url'].replace('http://saroshsalman.com/', '')
        item = {
            'tax:product_type': 'variable',
            'visibility': 'visible',
            'post_status': 'publish',
            'tax_status': 'taxable',
            'stock_status': 'instock',
            'backorders_allowed': 0,
            'attribute_default:Size': resp['variants'][0]['title'],
            'tax:product_cat': f"Formal Wear > {resp['type']}",
            'post_title': resp['title'],
            'post_date': resp['published_at'],
            'post_content': '\n'.join(description),
            'post_excerpt': description[0],
            'sku': hashlib.md5(resp['title'].encode()).hexdigest(),
            'regular_price': resp['price'] / 100,
            'meta:views_woo_price': resp['price'] / 100,
            'attribute:Size': '|'.join([item['title'] for item in resp['variants']]),
            'attribute_data:Size': '1|1|1',
            'meta:product_url': kwargs['url'],
            'meta:features': '\n'.join(description[1:-1]),
            'meta:model_note': description[-1],
            'meta:name': resp['title'],
            'tax:tags': '|'.join(resp['tags']),
            'meta:price_min': f'${resp["price_min"] / 100}',
            'meta:price_max': f'${resp["price_max"] / 100}',
            'collection': kwargs['url'].split('/collections/')[-1].split('/')[0],
            'image_paths': '|'.join([
                f'https://foreverdulhan.com/wp-content/uploads/product_images/{prefix}/{re.match(r".+jpg", img["src"].split("/")[-1], re.IGNORECASE).group()}'
                for img in resp['media']]),
            'image_urls': [img['src'] for img in resp['media']],
            'image_path_prefix': prefix,
            'meta:wpcf-sizing-gu' : '<img src="https://foreverdulhan.com/wp-content/uploads/product_images/size/Size_Chart.jpg"/>'
        }

        options = []
        for i, variant in enumerate(resp['variants']):
            option = {
                'post_title' : f'{item["post_title"]}-{variant["title"]}',
                'parent_sku': item['sku'],
                'sku': hashlib.md5(variant['name'].encode()).hexdigest(),
                'regular_price': variant['price'] / 100,
                'meta:attribute_Size': variant['title'],
                'tax:product_type' : 'variation',
                'tax_class': 'parent',
                'visibility': 'visible',
                'post_status': 'publish',
                'tax_status': 'taxable',
                'stock_status': 'instock',
                'instock' : 1,
                'sold_individually': 0,
                'meta:_credits_amount': math.ceil(variant['price'] / 100 / 25)
            }
            options.append(option)

        item['options'] = options

        return item

    def parse_category(self, response):
        api_urls = [[f'http://saroshsalman.com/products/{url.split("/")[-1]}.js', url] for
                    url in
                    response.css('a.product-item__link::attr(href)').getall()]

        for api_url, url in api_urls:
            yield Request(api_url, callback=self.parse_product,
                          cb_kwargs={'url': f'http://saroshsalman.com{url}'})
