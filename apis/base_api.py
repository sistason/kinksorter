import requests
import bs4
import logging
import datetime
import cv2
import numpy as np
import subprocess
import os
import json
import threading
import time


class BaseAPI:
    name = 'BaseAPI'
    base_url = ''

    def __init__(self, use_api=True):
        logging.getLogger("requests").setLevel(logging.WARNING)
        self._site_capabilities = None
        self._cookies = None
        self._headers = {}
        self._use_api = use_api

        self._cache_updating = False
        self._cache_thread = None
        self._cache = {}

        self.set_headers()

    def set_headers(self):
        """ Set any HTTP-headers required """
        # TODO: randomized user-agent?
        self._headers = {'Accept-Language': 'en-US,en;q=0.5'}

    def set_cookies(self):
        """ Set any HTTP-cookies required """
        self._cookies = None

    def use_cache(self):
        """ Enable the usage and the creation of the API-cache """
        if not self._use_api or self._cache or self._cache_updating:
            return

        self._cache_updating = True
        self._cache_thread = threading.Thread(target=self._update_cache)
        self._cache_thread.start()

    def _update_cache(self):
        """ Get a dump of the API to use as a cache """
        self._cache_updating = False
        return NotImplementedError

    def make_request_get(self, url, data=None):
        """ Do a GET request, take care of the cookies, timeouts and exceptions """
        if data is None:
            data = {}
        if not self._cookies:
            self.set_cookies()
        ret = ''
        retries = 3
        while not ret and retries > 0:
            try:
                r_ = requests.get(url, data=data, cookies=self._cookies, headers=self._headers, timeout=2)
                ret = r_.text
            except requests.Timeout:
                retries -= 1
                time.sleep(1)
            except Exception as e:
                logging.debug('Caught Exception "{}" while making a get-request to "{}"'.format(e, url))
                break
        return ret

    def query_for_name(self, name):
        """ Query the API or the cache for shoots matching that name """
        if not self._use_api:
            logging.warning('Not using the API makes it unable to query for name!')
            return {}

        if self._cache or self._cache_updating:
            while self._cache_updating:
                time.sleep(1)

            return self.cached_query_for_title(name)

        return self.api_query_for_title(name)

    @NotImplementedError
    def cached_query_for_title(self, name):
        """ Use the API-cache to look shoots matching that name """
        return

    @NotImplementedError
    def api_query_for_title(self, name):
        """ Query the API for shoots matching that name """
        return

    def query_for_date(self, date_):
        """ Query the API or the cache for shoots matching that date """
        if not self._use_api:
            logging.warning('Not using the API makes it unable to query for date!')
            return {}

        if self._cache or self._cache_updating:
            while self._cache_updating:
                time.sleep(1)

            return self.cached_query_for_date(date_)

        return self.api_query_for_date(date_)

    @NotImplementedError
    def cached_query_for_date(self, date_):
        """ Use the API-cache to look shoots matching that date """
        return

    @NotImplementedError
    def api_query_for_date(self, date_):
        """ Query the API for shoots matching that date """
        return

    def query_for_id(self, id_):
        """ Query the API, the cache or the site directly for shoots matching that ID """
        if not self._use_api:
            return self.direct_query_for_id(id_)

        if self._cache or self._cache_updating:
            while self._cache_updating:
                time.sleep(1)
                print('waiting...')

            return self.cached_query_for_id(id_)

        return self.api_query_for_id(id_)

    @NotImplementedError
    def cached_query_for_id(self, id_):
        """ Use the API-cache to look shoots matching that ID """
        return

    @NotImplementedError
    def api_query_for_id(self, id_):
        """ Query the API for shoots matching that ID """
        return

    @NotImplementedError
    def direct_query_for_id(self, id_):
        """ Query the site directly for shoots matching that ID """
        return

    @staticmethod
    def _to_json(result):
        """ Helper to convert a string to JSON """
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {}
