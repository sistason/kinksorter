import requests
import bs4
import logging
import datetime
import cv2
import numpy as np
import subprocess
import os
import json


class KinkAPI():
    _cookies = None
    _site_capabilities = None
    _headers = {}
    name = 'Kink.com'

    def __init__(self, template=None):
        logging.getLogger("requests").setLevel(logging.WARNING)

        self._cookies = None
        self.shootid_template = template

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
        if self._site_capabilities is not None:
            return self._site_capabilities

        channel_names = []
        content = self.make_request_get("http://kink.com/channels")
        soup = bs4.BeautifulSoup(content, 'html5lib')
        channels = soup.body.find('div', id='footer')
        if channels:
            site_lists = channels.find_all('div', attrs={'class': 'site-list'})
            for site_list_ in site_lists:
                for site_ in site_list_.find_all('a'):
                    if site_.attrs.get('href','').startswith('/channel/'):
                        channel_ = site_.text.strip()
                        channel_names.append(channel_)
                        channel_names.append(''.join([c[0] for c in channel_.split()]))

            self._site_capabilities = channel_names
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

    def get_shootid_through_metadata(self, file_path):
        """ Works only on Kink.com movies from around 3500-4500 """
        o = subprocess.run(['ffprobe', '-show_format', '-v', 'quiet', '-of', 'json', file_path], stdout=subprocess.PIPE)
        try:
            json_output = json.loads(o.stdout.decode())
            title = json_output.get('format').get('tags').get('title')
            return int(title.split('.')[0].split()[-1])
        except (ValueError, IndexError, AttributeError, json.JSONDecodeError):
            return 0

    def get_shootid_through_image_recognition(self, file_path):
        """ Works only on Kink.com movies after ~ """
        capture = cv2.VideoCapture(file_path)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not frame_count:
            logging.debug('No frames to recognize found for file "{}"'.format(file_path))
            return 0
        template = self.shootid_template
        if template is None:
            logging.debug('No template to recognize shootids')
            return 0
        fps = capture.get(cv2.CAP_PROP_FPS)
        ret = capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count - int(4 * fps))
        frame_list = []
        while ret:
            ret, frame_ = capture.read()
            if ret:
                frame_list.append((frame_.max(), frame_))

        if not frame_list:
            logging.debug('No frames readable in the last seconds of file "{}"'.format(file_path))
            return 0
        frame_list.sort(key=lambda f: f[0])
        best_frame = frame_list[-1][1]

        red_frame = best_frame[:, :, 2]

        if template.dtype != np.dtype('uint8'):
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(red_frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < 0.7:
            logging.debug('Template for shootid doesn\'t match for file "{}"'.format(file_path))
            return 0

        template_height, template_width = template.shape
        shootid_crop = red_frame[max_loc[1]:max_loc[1] + template_height, max_loc[0] + template_width:]

        shootid = self.recognize_shootid(shootid_crop)
        if not shootid:
            logging.debug('Tesseract couldn\'t recognize digits for file "{}"'.format(file_path))
            self.debug_frame(shootid_crop)

        return shootid

    def recognize_shootid(self, shootid_img):
        # FIXME: filepath-independence by piping the image?
        tmp_image = '/tmp/kinksorter_shootid.jpeg'
        cv2.imwrite(tmp_image, shootid_img)
        output = subprocess.run(['tesseract', tmp_image, 'stdout', 'digits'], stdout=subprocess.PIPE)
        if output.stdout is not None and output.stdout.strip().isdigit():
            return int(output.stdout)
        return 0

    def debug_frame(self, frame):
        cv2.imwrite('/tmp/test.jpeg', frame)
        os.system('eog /tmp/test.jpeg 2>/dev/null')
