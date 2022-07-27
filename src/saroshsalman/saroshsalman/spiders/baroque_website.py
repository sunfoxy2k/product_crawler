from scrapy.http import Request
from scrapy import Spider
import hashlib
import re
import math
import requests
import ast

size_chart_dic = {}

urls_text = requests.get('https://baroque.pk/products/embroidered-organza-dupatta-31').text.split(
    '''<script>(function() {
  function asyncLoad() {
    var urls = '''
)[1].split(';')[0]

urls = ast.literal_eval(urls_text)

size_guide_url = [url.replace('\\/', '/') for url in urls if 'size-guides' in url][0]


script = requests.get(
    size_guide_url).text

size_data = ast.literal_eval(
    script.split('window.eastsideco_sizeGuides.cachedCharts=')[1].split(
        ';!function(t)')[0])

for chart in size_data:
    chart['tag'] = chart['tag'].replace(',', '')
    size_chart_dic[chart['tag']] = chart


def chart_table(chart_data):
    table = f'<h2>{chart_data["tag"]}</h2>'
    table += '<table>'
    for row in chart_data['data']:
        table += '<tr>'
        processed_row = [val.replace("\\/", '') for val in row]
        table += ''.join([f'<td>{val}</td>' for val in processed_row])
        table += '</tr>'
    table += '</table>'

    return table



class BaroqueSpider(Spider):
    name = 'baroque_spider'
    allowed_domains = ['baroque.pk']
    start_urls = ['https://baroque.pk/collections/']
    custom_settings = {
        'FEEDS': {
            f'/tmp/data.csv': {
                'format': 'csv',
                'overwrite': True
            }
        }
    }

    def parse(self, response, **kwargs):
        urls = [url for url in response.css('li.collection-list__item > a::attr(href)').getall()
                if 'collections' in url]
        for url in urls:
            if 'https' not in url:
                yield response.follow(url, callback=self.parse_category)
            else:
                yield Request(url, callback=self.parse_category)

    def parse_product(self, response, **kwargs):
        resp = response.json()
        prefix = kwargs['url'].replace('http://baroque.pk/', '')
        diamond = math.ceil(resp['price'] / 100 / 25  * 0.0050)


        if 0 < diamond < 3:
            product_type = "Casual Wear"
        elif diamond < 5:
            product_type = "Party Wear"
        elif diamond < 22:
            product_type = "Formal Wear"
        else:
            product_type = "Bridal Wear"

        USD_price = resp['price'] / 100 * 0.0050


        size_html = '<br/>'.join([chart_table(size_chart_dic[tag]) for tag in resp['tags'] if
                      tag in size_chart_dic])

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
            'post_content': resp['description'].title(),
            'post_excerpt': resp['description'].title(),
            'regular_price': "{:.2f}".format(USD_price),
            'meta:views_woo_price': "{:.2f}".format(USD_price),
            'attribute:Size': '|'.join([item['title'] for item in resp['variants']]),
            'attribute_data:Size': '1|1|1',
            'meta:product_url': response.url[:-3],
            # 'meta:features': '\n'.join(description),
            'meta:name': resp['title'],
            'tax:tags': '|'.join(resp['tags']),
            'meta:price_min': "{:.2f}".format(resp["price_min"] / 100 * 0.0050),
            'meta:price_max': "{:.2f}".format(resp["price_max"] / 100 * 0.0050),
            'collection': kwargs['url'].split('/collections/')[-1].split('/')[0],
            'image_paths': '|'.join([
                f'https://foreverdulhan.com/wp-content/uploads/product_images/{prefix}/{re.match(r".+((png)|(jpg))", img["src"].split("/")[-1], re.IGNORECASE).group()}'
                for img in resp['media']]),
            'image_urls': [img['src'] for img in resp['media']],
            'image_path_prefix': prefix,
            'meta:wpcf-sizing-gu' : size_html,
            'sku': f'BRQ-{ "{:.2f}".format(USD_price)}-{resp["title"].split()[-1]}'.replace('.', ''),
        }

        options = []
        for i, variant in enumerate(resp['variants']):
            option = {
                'post_title': f'{item["post_title"]}-{variant["title"]}',
                'parent_sku': item['sku'],
                'sku': hashlib.md5(variant['name'].encode()).hexdigest(),
                'regular_price': "{:.2f}".format(variant['price'] / 100 * 0.0050),
                'meta:attribute_Size': variant['title'],
                'tax:product_type': 'variation',
                'tax_class': 'parent',
                'visibility': 'visible',
                'post_status': 'publish',
                'tax_status': 'taxable',
                'stock_status': 'instock',
                'instock': 1,
                'sold_individually': 0,
                'meta:_credits_amount':  math.ceil(variant['price'] / 100 * 0.0050 / 25)
            }
            options.append(option)

        item['options'] = options

        return item

    def parse_category(self, response):
        api_urls = [[f'http://baroque.pk/products/{url.split("/")[-1]}.js', response.url] for
                    url in
                    response.css('h3.card-information__text a.full-unstyled-link::attr(href)').getall()]

        for api_url, url in api_urls:
            yield Request(api_url, callback=self.parse_product,
                          cb_kwargs={'url': url})