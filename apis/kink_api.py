import requests
import bs4
import logging
import datetime
import cv2
import numpy as np
import subprocess
import os
import json
import re


from apis.base_api import BaseAPI


class KinkAPI(BaseAPI):
    name = 'Kink.com'
    base_url = 'https://www.kink.com'
    api_url = 'https://www.kinkyapi.site/kinkcom'

    def __init__(self, templates=None):
        super().__init__()

        self.shootid_templates = templates

    def set_cookies(self):
        if self._use_api:
            return

        _ret = requests.get(self.base_url)
        _cookies = _ret.cookies
        _cookies['viewing-preferences'] = 'straight,gay'
        self._cookies = _cookies

    def get_site_responsibilities(self):
        if self._site_capabilities is not None:
            return self._site_capabilities

        channel_names = []
        content = self.make_request_get(self.base_url+"/channels")
        soup = bs4.BeautifulSoup(content, 'html5lib')
        channels = soup.body.find('div', id='footer')
        if channels:
            site_lists = channels.find_all('div', attrs={'class': 'site-list'})
            for site_list_ in site_lists:
                for site_ in site_list_.find_all('a'):
                    if site_.attrs.get('href', '').startswith('/channel/'):
                        channel_ = site_.text.strip()
                        channel_names.append(channel_)
                        channel_names.append(''.join([c[0] for c in channel_.split()]))

            self._site_capabilities = channel_names
        return channel_names

    def _update_cache(self):
        shoots = self.make_request_get(self.api_url + '/dump_shoots')
        models = self.make_request_get(self.api_url + '/dump_models')

        shoots_j = self._to_json(shoots)
        models_j = self._to_json(models)

        self._cache = {'shoots': shoots_j.get('results', []), 'models': models_j.get('results', [])}
        self._cache_updating = False

    def cached_query_for_id(self, kink_id):
        shoots = self._cache.get('shoots', [])
        for s in shoots:
            if s.get('shootid', 0) == kink_id:
                shoot = s
                break
        else:
            return []

        return [self._api_result_to_properties(shoot)]

    def api_query_for_id(self, kink_id):
        shoots = self.make_request_get(self.api_url + '/shoot/{}'.format(kink_id))
        shoots_j = self._to_json(shoots)

        return self._api_to_properties(shoots_j)

    def _api_to_properties(self, json_response):
        if json_response.get('errors', True):
            return []

        return [self._api_result_to_properties(r) for r in json_response.get('results', [])]

    @staticmethod
    def _api_result_to_properties(json_result):
        return {'shootid': int(json_result.get('shootid', 0)),
                'exists': json_result.get('exists', False),
                'site': json_result.get('site', {}).get('name', None),
                'title': json_result.get('title', None),
                'performers': [i.get('name', '') for i in json_result.get('performers', [])],
                'date': datetime.date.fromtimestamp(int(json_result.get('date', 0)))
                 }

    def direct_query_for_id(self, kink_id):
        properties = {"shootid": kink_id}
        if not kink_id:
            return [properties]

        content = self.make_request_get(self.base_url+"/shoot/{}".format(kink_id))
        if content:
            _bs = bs4.BeautifulSoup(content, "html5lib")
            if _bs.title.text:
                properties['exists'] = True
                try:
                    # Get link of the site from a.href
                    site_logo_ = _bs.body.find('div', attrs={"class": "column shoot-logo"})
                    site_link_ = site_logo_.a.attrs.get('href', '')
                    # Get verbose name from the sitelist
                    site_list_ = _bs.body.find('div', attrs={'class': 'site-footer'})
                    site_name_ = site_list_.find('a', href=site_link_).text.strip()
                    properties['site'] = site_name_
                except Exception as e:
                    logging.warning('Could not parse site, exception was: {}'.format(e))
                    logging.warning(_bs.body)

                info = _bs.body.find('div', attrs={'class': 'shoot-info'})
                if info:
                    try:
                        title_ = info.find(attrs={'class', 'shoot-title'})
                        title_ = title_.renderContents().decode().replace('<br/>', ' - ').replace('  ', ' ')
                        properties['title'] = title_
                    except Exception as e:
                        logging.warning('Could not parse title, exception was: {}'.format(e))

                    try:
                        performers_ = info.find(attrs={'class': 'starring'})
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
                properties['exists'] = False
        else:
            logging.error('Could not connect to site')

        return [properties]

    def api_query_for_date(self, date_):
        shoot = self.make_request_get(self.api_url + '/shoot_date/{}'.format(date_))
        shoot_j = self._to_json(shoot)

        return self._api_to_properties(shoot_j)

    def cached_query_for_date(self, date_):
        shoots_ = self._cache.get('shoots', [])
        shoots = [s for s in shoots_ if s.get('date', -1) == date_]

        return [self._api_result_to_properties(s) for s in shoots]

    def api_query_for_title(self, title):
        shoots = self.make_request_get(self.api_url + '/shoot_title/{}'.format(title))
        shoots_j = self._to_json(shoots)

        return self._api_to_properties(shoots_j)

    def cached_query_for_title(self, title):
        shoots_ = self._cache.get('shoots', [])
        shoots = [s for s in shoots_ if re.search(title, s.get('title', ''))]

        return [self._api_result_to_properties(s) for s in shoots]

    @staticmethod
    def get_shootid_through_metadata(file_path):
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
            return -1
        template = self.shootid_templates[0] if self.shootid_templates else None
        if template is None:
            logging.debug('No template to recognize shootids')
            return -1
        fps = capture.get(cv2.CAP_PROP_FPS)
        ret = capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count - int(4 * fps))
        frame_list = []

        # capture is sometimes not able to read at the end, so read the last possible frame
        current_frame = capture.get(cv2.CAP_PROP_POS_FRAMES)
        if current_frame != frame_count:
            ret = capture.set(cv2.CAP_PROP_POS_FRAMES, current_frame-1)

        while ret:
            ret, frame_ = capture.read()
            if ret:
                frame_list.append((frame_.max(), frame_))

        if not frame_list:
            logging.debug('No frames readable in the last seconds of file "{}"'.format(file_path))
            return -1
        frame_list.sort(key=lambda f: f[0])
        best_frame = frame_list[-1][1]

        red_frame = best_frame[:, :, 2]

        if template.dtype != np.dtype('uint8'):
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        height, width = red_frame.shape
        # Template is for 720p image, so scale it accordingly
        scale = height/720.0
        template_scaled = cv2.resize(template.copy(), (0,0), fx=scale, fy=scale)

        result = cv2.matchTemplate(red_frame, template_scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < 0.6:
            # Try other templates, which were used before 2009
            templates_older = self.shootid_templates[1:] if len(self.shootid_templates) > 1 else []
            for template_older in templates_older:
                template_scaled = cv2.resize(template_older.copy(), (0, 0), fx=scale, fy=scale)
                result = cv2.matchTemplate(red_frame, template_scaled, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val >= 0.6:
                    break
            else:
                r_ = result.copy()
                cv2.normalize(result, r_, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
                r_ = cv2.cvtColor(r_, cv2.COLOR_GRAY2BGR)
                cv2.circle(r_, max_loc, 5, (0, 0, 255))
                logging.debug('Template for shootid doesn\'t match ({:.2}<0.7) for file "{}"'.format(max_val, file_path))
                return 0

        template_height, template_width = template_scaled.shape
        shootid_crop = red_frame[max_loc[1]:max_loc[1] + template_height, max_loc[0] + template_width:]

        shootid = self.recognize_shootid(shootid_crop)
        if not shootid:
            logging.debug('Tesseract couldn\'t recognize digits for file "{}"'.format(file_path))
            self.debug_frame(shootid_crop)

        return shootid

    @staticmethod
    def recognize_shootid(shootid_img):
        # FIXME: filepath-independence by piping the image?
        tmp_image = '/tmp/kinksorter_shootid.jpeg'
        cv2.imwrite(tmp_image, shootid_img)
        out = subprocess.run(['tesseract', tmp_image, 'stdout', 'digits'], stdout=subprocess.PIPE)
        output = out.stdout.decode()
        if ' ' in output:
            output = output.replace(' ', '')
        if output is not None and output.strip().isdigit():
            return int(output)
        return 0

    @staticmethod
    def debug_frame(frame):
        cv2.imwrite('/tmp/test.jpeg', frame)
        os.system('eog /tmp/test.jpeg 2>/dev/null')

if __name__ == '__main__':
    from utils import Settings
    settings = Settings({'shootid_template_dir':'templates/'})
    api_ = settings.apis['Kink.com']
    import sys
    from movie import Movie
    Movie.settings = settings
    if len(sys.argv) == 1:
        with open('list.txt', 'w') as f:
            for entry in os.scandir('/media/data/foo/BDSM/Electrosluts'):
                print(entry.name)
                mov = Movie(os.path.join('/media/data/foo/BDSM/Electrosluts', entry.path), api=api_)
                shootid_cv = api_.get_shootid_through_image_recognition(entry.path)
                shootid_nr = mov.get_shootids(entry.path)
                if len(shootid_nr) == 1 and shootid_cv == shootid_nr[0] or \
                        not shootid_nr and shootid_cv:
                    continue
                f.write("{} -> {}\n".format(entry.path, shootid_cv))
        sys.exit(0)

    movie = sys.argv[1]

    logging.basicConfig(format='%(funcName)s: %(message)s',
                        level=logging.DEBUG)
    print(api_.get_shootid_through_image_recognition(movie))
