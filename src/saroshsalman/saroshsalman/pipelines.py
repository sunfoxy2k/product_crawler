from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline
import re

class CustomImagePipeline(ImagesPipeline):

    def open_spider(self, spider):
        self.spiderinfo = self.SpiderInfo(spider)
        self.spider_name = spider.name

    def file_path(self, request, response=None, info=None, **kwargs):
        prefix = request.meta['image_path_prefix']
        image_name = re.match(r".+((jpg)|(png))", request.url.split("/")[-1]).group()

        return f'{prefix}/{image_name}'

    def get_media_requests(self, item, info):
        if self.spider_name == 'saroshalman_spider':
            yield Request('https://cdn.shopify.com/s/files/1/1919/6837/files/Size_Chart.jpg', meta={'image_path_prefix' : 'size'})

        for image in item['image_urls']:
            yield Request(image, meta={'image_path_prefix': item['image_path_prefix']})