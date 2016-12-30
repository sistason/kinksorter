import requests
import bs4
import re
import logging
import datetime

class KinkAPI():
    _cookies = None
    _site_responsibilites = None
    _headers = {}

    def __init__(self):
        logging.getLogger("requests").setLevel(logging.WARNING)
        self.set_kink_headers()

    def set_kink_headers(self):
        # TODO: randomized user-agent?
        self._headers = {'Accept-Language': 'en-US,en;q=0.5'}

    def set_kink_cookies(self):
        _ret = requests.get("http://www.kink.com")
        _cookies = _ret.cookies
        _cookies['viewing-preferences']='straight,gay'
        self._cookies = _cookies

    def make_request_get(self, url, data=None):
        if data is None:
            data = {}
        if not self._cookies:
            self.set_kink_cookies()
        ret = ''
        retries = 3
        while not ret and retries > 0:
            try:
                r_ = requests.get(url, data=data, cookies = self._cookies, headers = self._headers, timeout = 2)
                ret = r_.text
            except requests.Timeout:
                retries -= 1
            except Exception as e:
                logging.debug('Caught Exception "{}" while making a get-request to "{}"'.format(e, url))
                break
        return ret

    def get_site_responsibilities(self):
        if self._site_responsibilites is not None:
            return self._site_responsibilites

        channel_names = []
        content = self.make_request_get("http://kink.com/channels")
        soup = bs4.BeautifulSoup(content, 'html5lib')
        channels = soup.body.find('div', id='footer')
        if channels:
            site_lists = channels.find_all('div', attrs={'class': 'site-list'})
            for site_list_ in site_lists:
                for site_ in site_list_.find_all('a'):
                    if site_.attrs.get('href','').startswith('/channel/'):
                        channel_names.append(site_.text.strip())

            for channel_name in list(channel_names):
                channel_names.append(''.join([c[0] for c in channel_name.split()]))

            self._site_responsibilites = channel_names

        return channel_names

    def query_for_name(self, name):
        # TODO: Not (yet) possible without a cache/list
        properties = {}
        ...
        return properties

    def query_for_date(self, date):
        # TODO: Not (yet) possible without a cache/list
        properties = {}
        ...
        return properties

    def query_for_id(self, kink_id):
        properties = {"id":kink_id}
        content = self.make_request_get("http://kink.com/shoot/{}".format(kink_id))
        if content:
            _bs = bs4.BeautifulSoup(content, "html5lib")
            if _bs.title.text:
                try:
                    # Get link of the site from a.href
                    site_logo_ = _bs.body.find('div', attrs={"class":"column shoot-logo"}) # current-page
                    site_link_ = site_logo_.a.attrs.get('href', '')
                    # Get verbose name from the sitelist
                    site_list_ = _bs.body.find('div', attrs={'class':'site-footer'})
                    site_name_ = site_list_.find('a', href=site_link_).text.strip()
                    properties['site'] = site_name_
                except Exception as e:
                    logging.warning('Could not parse site, exception was: {}'.format(e))
                    logging.warning(_bs.body)

                info = _bs.body.find('div', attrs={'class':'shoot-info'})
                if info:
                    try:
                        title_ = info.find(attrs={'class', 'shoot-title'})
                        title_ = title_.renderContents().decode().replace('<br/>', ' - ').replace('  ',' ')
                        properties['title'] = title_
                    except Exception as e:
                        logging.warning('Could not parse title, exception was: {}'.format(e))

                    try:
                        performers_ = info.find(attrs={'class':'starring'})
                        performers_ = [i.text for i in performers_.find_all('a')]
                        properties['performers'] = performers_
                    except Exception as e:
                        logging.warning('Could not parse performers, exception was: {}'.format(e))

                    try:
                        date_ = info.p
                        date_ = date_.text.split(':')[-1].strip()
                        # TODO: Check if kink.com gives out dates in local locale settings
                        date_ = datetime.datetime.strptime(date_, '%B %d, %Y').date()
                        properties['date'] = date_
                    except Exception as e:
                        logging.warning('Could not parse date, exception was: {}'.format(e))
            else:
                logging.error('404! No shoot with id {}'.format(kink_id))
        else:
            logging.error('Could not connect to site')

        return properties

