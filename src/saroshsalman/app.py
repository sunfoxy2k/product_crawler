import scrapydo
from saroshsalman.spiders.products import ProductsSpider
import pandas as pd
import ast
import os
import shutil
import boto3


def lambda_handler(event, context):
    msg = ''
    statusCode = None
    try:
        scrapydo.setup()
        scrapydo.run_spider(ProductsSpider)
        df = pd.read_csv('/tmp/data.csv')
        os.makedirs('/tmp/result/data', exist_ok=True)
        df['image_urls'] = df['image_urls'].apply(lambda x: x.replace(',', '|'))
        df.drop(['image_path_prefix', 'images'], axis=1, inplace=True, errors='ignore')
        for collection in df['collection'].unique():
            coll_df = df[df['collection'] == collection].copy()
            coll_df['options'].apply(ast.literal_eval).explode().apply(pd.Series).to_csv(
                f'/tmp/result/data/{collection}_variants.csv', index=False)
            coll_df.drop(['options', 'collection'], axis=1, inplace=True, errors='ignore')
            coll_df.rename({'image_paths': 'images'}, axis=1).to_csv(
                f'/tmp/result/data/{collection}.csv', index=False)

        os.remove('/tmp/data.csv')
        shutil.make_archive('/tmp/result', 'zip', '/tmp/result')
        s3 = boto3.client('s3')
        with open('/tmp/result.zip', 'rb') as result:
            s3.upload_fileobj(result, Bucket=os.getenv('CSVBucket'), Key='result.zip')
            s3 = boto3.resource('s3')
            object_acl = s3.ObjectAcl(os.getenv('CSVBucket'), 'result.zip')
            object_acl.put(ACL='public-read')
    except Exception as e:
        statusCode = 503
        msg = str(e)
    else:
        statusCode = 200
        msg = 'SUCCESS'
    return {
        "statusCode": statusCode,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,PUT,DELETE,OPTIONS'
        },
        "body": msg,
    }

if __name__ == '__main__':
    print(lambda_handler(None, None))
