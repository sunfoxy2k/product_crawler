from scrapy.http import Request
from scrapy import Spider
import html
from scrapy.selector import Selector
import hashlib
import re
import math
import requests

def render_html(table):
  tmp = '<table><tbody>'
  for idx, row in enumerate(table['data']):
    tmp += '<tr>'
    tmp +=''.join( [f'<td>{val["value"]}</td>' for val in row])
    tmp += '</tr>'
  tmp += '</tbody></table>'
  return tmp

class SUFFSpider(Spider):
    name = 'suffuse_spider'
    allowed_domains = ['suffuse.pk']
    start_urls = ['http://suffuse.pk']
    custom_settings = {
        'FEEDS': {
            f'/tmp/data.csv': {
                'format': 'csv',
                'overwrite': True
            }
        }
    }

    def parse(self, response, **kwargs):
        urls = [url for url in response.css('nav.Header__MainNav a::attr(href)').getall()
                if 'collections' in url]
        for url in urls:
            if 'https' not in url:
                yield response.follow(url, callback=self.parse_category)
            else:
                yield Request(url, callback=self.parse_category)

    def parse_product(self, response, **kwargs):
        resp = response.json()

        description = html.unescape(resp['description']).replace('\xa0', '')
        selector = Selector(text=description)

        description = [feature.strip() for feature in selector.css('li *::text').getall()]
        if len(description) == 0:
            description = [feature.strip() for feature in
                           selector.css('p::text').getall()]
        description = [feature for feature in description if feature != '']
        prefix = kwargs['url'].replace('http://suffuse.pk/', '')
        diamond = math.ceil(resp['price'] / 100 / 25)

        if 0 < diamond < 4:
            product_type = "Casual Wear"
        elif diamond < 8:
            product_type = "Party Wear"
        elif diamond < 22:
            product_type = "Formal Wear"
        else:
            product_type = "Bridal Wear"

        size_html = ''



        for img in resp['media']:
            if resp['title'].replace(' ', '_') in img['src']:
                size_img = f'https://foreverdulhan.com/wp-content/uploads/product_images/{prefix}/{re.match(r".+((png)|(jpg))", img["src"].split("/")[-1], re.IGNORECASE).group()}'

        size_data = requests.get(f'https://app.kiwisizing.com/api/getSizingChart?shop=suffuse.myshopify.com&product={resp["id"]}').json()

        if size_data['sizings'] :
            title_table = [val['value'] for val in size_data['sizings'][0]['layout']['data'] if val['type'] == 0]
            tables = [render_html(table) for table in size_data['sizings'][0]['tables'].values()]
            if len(tables) == 2 and len(title_table) == 1:
                size_html += tables[0]
                size_html += title_table[0]
                size_html += tables[1]
            elif len(tables) == 1 and len(title_table) == 0:
                size_html += tables[0]
            else:
                for idx, table in enumerate(tables):
                  size_html += title_table[idx]
                  size_html += table

        item = {
            'tax:product_type': 'variable',
            'visibility': 'visible',
            'post_status': 'publish',
            'tax_status': 'taxable',
            'stock_status': 'instock',
            'backorders_allowed': 0,
            'attribute_default:Size': resp['variants'][0]['title'],
            'tax:product_cat': f"{product_type} > {resp['type']}",
            'post_title': resp['title'],
            'post_date': resp['published_at'],
            'post_content': '\n'.join(description).title(),
            'post_excerpt': description[0].title(),
            'regular_price': resp['price'] / 100,
            'meta:views_woo_price': resp['price'] / 100,
            'attribute:Size': '|'.join([item['title'] for item in resp['variants']]),
            'attribute_data:Size': '1|1|1',
            'meta:product_url': kwargs['url'],
            'meta:features': '\n'.join(description),
            'meta:name': resp['title'],
            'tax:tags': '|'.join(resp['tags']),
            'meta:price_min': f'${resp["price_min"] / 100}',
            'meta:price_max': f'${resp["price_max"] / 100}',
            'collection': kwargs['url'].split('/collections/')[-1].split('/')[0],
            'image_paths': '|'.join([
                f'https://foreverdulhan.com/wp-content/uploads/product_images/{prefix}/{re.match(r".+((png)|(jpg))", img["src"].split("/")[-1], re.IGNORECASE).group()}'
                for img in resp['media']]),
            'image_urls': [img['src'] for img in resp['media']],
            'image_path_prefix': prefix,
            'meta:wpcf-sizing-gu' : size_html,
            'sku': f'SUFF{str(resp["price"] // 100)}{resp["title"]}',
        }

        options = []
        for i, variant in enumerate(resp['variants']):
            option = {
                'post_title': f'{item["post_title"]}-{variant["title"]}',
                'parent_sku': item['sku'],
                'sku': hashlib.md5(variant['name'].encode()).hexdigest(),
                'regular_price': variant['price'] / 100,
                'meta:attribute_Size': variant['title'],
                'tax:product_type': 'variation',
                'tax_class': 'parent',
                'visibility': 'visible',
                'post_status': 'publish',
                'tax_status': 'taxable',
                'stock_status': 'instock',
                'instock': 1,
                'sold_individually': 0,
                'meta:_credits_amount': math.ceil(variant['price'] / 100 / 25)
            }
            options.append(option)

        item['options'] = options

        return item

    def parse_category(self, response):
        api_urls = [[f'http://suffuse.pk/products/{url.split("/")[-1]}.js', url] for
                    url in
                    response.css('a.ProductItem__ImageWrapper::attr(href)').getall()]

        for api_url, url in api_urls:
            yield Request(api_url, callback=self.parse_product,
                          cb_kwargs={'url': f'http://suffuse.pk{url}'})