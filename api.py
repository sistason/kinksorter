import requests
import json
import bs4
import re
import logging
import datetime

class KinkAPI():

    def __init__(self):
        self._cache = []
        self._cookies = self.get_kink_cookies()
        self._headers = {'Accept-Language':'en-US,en;q=0.5'}

    def get_kink_cookies(self):
        _ret = requests.get("http://www.kink.com")
        _cookies = _ret.cookies
        _cookies['viewing-preferences']='straight,gay'
        return _cookies


    def update_cache(self):
        try:
            _ret = requests.get("http://www.iafd.com/distrib.rme/distrib=3259/kink%2ecom.htm")
            _bs = bs4.BeautifulSoup(_ret.text, 'html5lib')
            _entries = _bs.find(id="distable").find_all("tr")[1:]
            self._cache = [(i.text, i.a) for i in _entries]
        except requests.HTTPError as e:
            self._cache = []

    def query(self, type_, query):
        ret = None
        if type_ == 'id':
            ret = self.query_for_id(query)
        if type_ == 'name':
            ret = self.query_for_name(query)
        if type_ == 'date':
            ret = self.query_for_date(query)

        # TODO Validation
        return ret

    def query_for_id(self, kink_id):
        return self.get_directly_id(kink_id)

        _kinklist_re = re.compile(r'\D{}\D'.format(kink_id))
        matches = [i for i in self._cache if re.search(_kinklist_re, i[0])]
        print([i[0] for i in matches])
        if not matches:
            return self.get_directly_id(kink_id)

    def query_for_name(self, name):
        ...
        return None

    def query_for_date(self, date):
        ...
        return None

    def get_directly_id(self, kink_id):
        properties = {'title': '', 'performers': [], 'date': datetime.date(1970,1,1), 'site': '', 'id': kink_id}
        ret = requests.get("http://kink.com/shoot/{}".format(kink_id), cookies=self._cookies, headers=self._headers)
        if ret:
            _bs = bs4.BeautifulSoup(ret.text, "html5lib")
            if _bs.title:
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

                info = _bs.body.find('div', attrs={'class':'shoot-info'})
                if info:
                    try:
                        title_ = info.find(attrs={'class', 'shoot-title'})
                        title_ = title_.renderContents().decode().replace('<br/>', ' -')
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
                        date_ = datetime.datetime.strptime(date_, '%B %d, %Y').date()
                        properties['date'] = date_
                    except Exception as e:
                        logging.warning('Could not parse date, exception was: {}'.format(e))
            else:
                logging.error('404! No shoot with id {}'.format(kink_id))
        else:
            logging.error('Could not connect to site')

        return properties

