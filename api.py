from pymongo import MongoClient
from pymongo.errors import OperationFailure
from scrapy.utils.project import get_project_settings
from flask import Flask, jsonify
import ssl
import logging

app = Flask(__name__)


@app.route('/getnews/<keyword>', methods=['GET'])
def get_news(keyword):
    settings = get_project_settings()
    connection = MongoClient(settings['MONGODB_HOST'],
                             port=settings['MONGODB_PORT'],
                             username=settings['MONGODB_USER'],
                             password=settings['MONGODB_PASS'],
                             ssl=True,
                             ssl_cert_reqs=ssl.CERT_NONE)
    db = connection[settings['MONGODB_DB']]
    collection = db[settings['MONGODB_COLLECTION']]
    collection.create_index([('text', 'text')])
    results = []
    if keyword is not None:
        try:
            for item in collection.find({"$text": {"$search": keyword}}):
                results.append({
                    'url': item['url'],
                    'title': item['title'],
                    'description': item['description'],
                    'section': item['section'],
                    'text': item['text'],
                    'author': item['author'],
                    'keywords': item['keywords']
                })
        except OperationFailure as e:
            logging.log(logging.ERROR, 'Failed read from MongoDB: ' + e.details)
    response = jsonify(results)
    return response


