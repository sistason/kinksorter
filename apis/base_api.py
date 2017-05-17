import requests
import logging
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
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                retries -= 1
                time.sleep(1)
            except Exception as e:
                logging.debug('Caught Exception "{}" while making a get-request to "{}"'.format(e.__class__, url))
                break
        return ret

    def get_site_responsibilities(self):
        """ Get responsibilities, e.g. which directory-name (==subsite) this API is capable of """
        if self._site_capabilities is not None:
            return self._site_capabilities

        if self._use_api:
            resps = self._get_api_site_responsibilities()
        else:
            resps = self._get_direct_site_responsibilities()
        self._site_capabilities = resps

        return resps if resps is not None else []

    @NotImplementedError
    def _get_direct_site_responsibilities(self):
        """ Get the site directly from the site """
        return

    @NotImplementedError
    def _get_api_site_responsibilities(self):
        """ Get the site from the API """
        return

    @staticmethod
    def _to_json(result):
        """ Helper to convert a string to JSON """
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {}

    def query(self, type_, by_property_, value_):
        """ Query the API, the cache or the site directly for $type matching $query """
        if not self._use_api:
            if type_ == 'shoots' and by_property_ == 'id':
                return self.query_direct_shoot_id(value_)
            else:
                logging.warning('Not using the API makes it unable to query for {}!'.format(type))
                return []

        if self._cache_updating:
            self._wait_for_cache()

        if self._cache:
            return self.query_cache(type_, by_property_, value_)
        else:
            return self.query_api(type_, by_property_, value_)

    def _wait_for_cache(self):
        i = 0
        while self._cache_updating:
            logging.info('Waiting for API-cache to be downloaded...')
            time.sleep(2)
            if i > 10:
                logging.info('Tired of waiting for API-cache, disabling...')
                self._cache_thread.join(timeout=1)
                self._cache = None
                self._cache_updating = False
            i += 1

    @NotImplementedError
    def query_cache(self, type_, by_property_, value_):
        """ Use the API-cache to get an item of "type" with by_property matching with query"""
        return

    @NotImplementedError
    def query_api(self, type_, by_property_, value_):
        """ Use the API to get an item of "type" with by_property matching with query"""
        return

    def query_direct_shoot_id(self, id_):
        """ Query the site directly for shoots matching that ID """
        return {}
