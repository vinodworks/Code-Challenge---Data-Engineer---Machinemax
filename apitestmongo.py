import random
import ssl
import string
import unittest

from pymongo import MongoClient
from scrapy.utils.project import get_project_settings


class TestApi(unittest.TestCase):

    def setUp(self):
        self.base_url = 'http://www.bbc.com/news/'
        settings = get_project_settings()
        connection = MongoClient(settings['MONGODB_HOST'],
                                 port=settings['MONGODB_PORT'],
                                 username=settings['MONGODB_USER'],
                                 password=settings['MONGODB_PASS'],
                                 ssl=True,
                                 ssl_cert_reqs=ssl.CERT_NONE)
        db = connection[settings['MONGODB_DB']]
        self.collection = db[settings['MONGODB_COLLECTION']]

        self.item = {
            'url': 'http://www.bbc.com/',
            'title': 'Unittest Test Article',
            'description': None,
            'section': None,
            'text': None,
            'author': None,
            'keywords': None
        }

    def test_one_record_inserted(self):
        self.item['url'] += str(random.random())
        self.item['text'] = ''.join(random.choices(string.ascii_letters + ' ', k=250))
        inserted_id = self.collection.insert_one(self.item).inserted_id
        result = self.collection.find_one({'_id': inserted_id})
        self.assertNotEqual(result, [])

    def test_one_record_data_matches(self):
        self.item['url'] += str(random.random())
        self.item['text'] = ''.join(random.choices(string.ascii_letters + ' ', k=250))
        inserted_id = self.collection.insert_one(self.item).inserted_id
        result = self.collection.find_one({'_id': inserted_id})
        self.assertEqual(result['text'], self.item['text'])

    def test_one_record_updated(self):
        self.item['url'] += str(random.random())
        self.item['text'] = ''.join(random.choices(string.ascii_letters + ' ', k=250))
        inserted_id = self.collection.insert_one(self.item).inserted_id
        new_text = ''.join(random.choices(string.ascii_letters, k=1))
        self.collection.update_one({'_id': inserted_id}, {'$set': {'text': new_text}})
        result = self.collection.find_one({'_id': inserted_id})
        self.assertEqual(result['text'], new_text)
