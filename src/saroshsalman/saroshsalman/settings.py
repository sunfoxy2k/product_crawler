
BOT_NAME = 'saroshsalman'

SPIDER_MODULES = ['saroshsalman.spiders']
NEWSPIDER_MODULE = 'saroshsalman.spiders'

ROBOTSTXT_OBEY = False

IMAGES_STORE = '/tmp/result/images'  # folder name or path where to save images
IMAGES_EXPIRES = 2
ITEM_PIPELINES = {'saroshsalman.pipelines.CustomImagePipeline':400 }
