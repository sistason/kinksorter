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
import tempfile


from apis.base_api import BaseAPI


class KinkAPI(BaseAPI):
    name = 'Kink.com'
    base_url = 'https://www.kink.com'
    api_url = 'https://www.kinkyapi.site/kinkcom'

    def __init__(self, templates=None, use_api=True):
        super().__init__(use_api=use_api)

        self.shootid_templates = []
        for t in templates:
            if t.dtype != np.dtype('uint8'):
                t = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY)
            self.shootid_templates.append(t)

    def set_cookies(self):
        if self._use_api:
            return

        _ret = requests.get(self.base_url)
        _cookies = _ret.cookies
        _cookies['viewing-preferences'] = 'straight,gay'
        self._cookies = _cookies

    def _get_direct_site_responsibilities(self):
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

        return channel_names if channel_names else None

    def _get_api_site_responsibilities(self):
        channel_names = []
        sites_ = self.make_request_get(self.api_url+"/site/.*")
        sites_j = self._to_json(sites_)
        if sites_j.get('errors', False):
            logging.error("Could not get site_responsibilities from API. Error: {}".format(sites_j.get('errors', '<>')))
            return None

        for site in sites_j.get('results', []):
            name = site.get('name', '')
            channel_names.append(name)
            channel_names.append(''.join([n[0] for n in name.split()]))

        return channel_names if channel_names else None

    def _update_cache(self):
        shoots = self.make_request_get(self.api_url + '/dump_shoots')
        if not shoots:
            # Don't continue, as if we get empty here, our thread was interrupted / no internet => no cache available
            return

        performers = self.make_request_get(self.api_url + '/dump_performers')
        if not performers:
            return

        shoots_j = self._to_json(shoots)
        performers_j = self._to_json(performers)

        self._cache = {'shoots': shoots_j.get('results', []), 'performers': performers_j.get('results', [])}
        self._cache_updating = False

    @staticmethod
    def _api_results_to_properties(type_, json_results):
        if type_ == 'shoots':
            return [{'shootid': int(json_result.get('shootid', 0)),
                     'exists': json_result.get('exists', False),
                     'site': json_result.get('site', {}).get('name', None),
                     'title': json_result.get('title', None),
                     'performers': [i.get('name', '') for i in json_result.get('performers', [])],
                     'date': datetime.date.fromtimestamp(int(json_result.get('date', 0)))
                     } for json_result in json_results]
        if type_ == 'performers':
            return json_results
        if type_ == 'sites':
            return json_results

        return []

    def query_cache(self, type_, by_property, value):
        results = []
        if by_property == 'date':
            print(type_, by_property, value)
            print(len(self._cache.get('shoots', [])))
            print(len(self._cache.get(type_, [])))
            print(self._cache.keys())
            print(self._cache.get(type_, [])[1])
            print(self._cache.get(type_, [])[1].get('date', ''))
            print(value)
        for t_ in self._cache.get(type_, []):
            if by_property in ['title', 'name'] and re.search(value, t_.get(by_property, '')) or \
               value == t_.get(by_property, ''):
                results.append(t_)

        return self._api_results_to_properties(type_, results)

    def query_api(self, type_, by_property_, value_):
        results = self.make_request_get(self.api_url + '/{}_{}/{}'.format(type_[:-1], by_property_, value_))
        results_j = self._to_json(results)

        if results_j.get('errors', True):
            return []

        return self._api_results_to_properties(type_, results_j.get('results', []))

    def query_direct_shoot_id(self, kink_id):
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
        """ Works only on Kink.com movies after ~2007 """
        red_frame = self._get_fitting_frame(file_path)
        if red_frame is None:
            return -1

        shootid_crop = None
        for template in self.shootid_templates:
            template_shape, max_loc = self._match_template(red_frame, template)
            if max_loc is not None:
                shootid_crop = red_frame[max_loc[1]:max_loc[1] + template_shape[0], max_loc[0] + template_shape[1]:]

        if shootid_crop is None:
            logging.debug('Templates for shootid did not match file "{}"'.format(file_path))
            return 0

        shootid = self.recognize_shootid(shootid_crop)
        if not shootid:
            logging.debug('Tesseract couldn\'t recognize digits for file "{}"'.format(file_path))
            if logging.getLogger(self.__class__.__name__).level == logging.DEBUG:
                self.debug_frame(shootid_crop)

        return shootid

    def _match_template(self, red_frame, template):
        height, width = red_frame.shape
        # Template is for 720p image, so scale it accordingly
        scale = height / 720.0
        template_scaled = cv2.resize(template.copy(), (0, 0), fx=scale, fy=scale)
        result = cv2.matchTemplate(red_frame, template_scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return template_scaled.shape, max_loc if max_val > 0.6 else None

    def _get_fitting_frame(self, file_path):
        if not self.shootid_templates:
            logging.debug('No template to recognize shootids')
            return None

        capture = cv2.VideoCapture(file_path)
        fps, frame_count = self._prepare_capture(capture)
        if not frame_count:
            logging.debug('No frames to recognize found for file "{}"'.format(file_path))
            return None

        analysis_range = int(frame_count - 3 * fps)
        frame_steps = int(fps / 3)
        next_frame = frame_count - 1
        red_frame = None
        while red_frame is None and next_frame >= analysis_range:
            red_frame = self._get_next_frame(capture, next_frame)
            next_frame -= frame_steps

        capture.release()
        if red_frame is None:
            logging.debug('No suitable frames found in the last seconds of file "{}"'.format(file_path))
        return red_frame

    def _prepare_capture(self, capture):
        # TODO: ignore errors of capture.set of partial files
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = capture.get(cv2.CAP_PROP_FPS)
        # Seek until the end, or adapt the end of the file if not possible
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        frame_count = capture.get(cv2.CAP_PROP_POS_FRAMES)
        return fps, frame_count

    def _get_next_frame(self, capture, next_frame):
        capture.set(cv2.CAP_PROP_POS_FRAMES, next_frame)
        ret, frame_ = capture.read()
        if ret and frame_.any() and (frame_[:, :] > 0).sum() / frame_.size < 0.1:
            red_frame = cv2.inRange(cv2.cvtColor(frame_, cv2.COLOR_BGR2HSV), (0, 50, 50), (30, 255, 255))
            return frame_[:, :, 2]

    @staticmethod
    def recognize_shootid(shootid_img):
        with tempfile.NamedTemporaryFile(suffix='.png') as f_:
            tmp_path = f_.name
        _, t_ = cv2.threshold(shootid_img, 100, 255, cv2.THRESH_BINARY)
        cv2.imwrite(tmp_path, t_)
        out = subprocess.run(['tesseract', tmp_path, 'stdout', 'digits'], stdout=subprocess.PIPE)
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
    settings = Settings({'shootid_template_dir': 'apis/templates/'})
    api_ = settings.apis['Kink.com']
    import sys
    from movie import Movie
    Movie.settings = settings
    path_ = sys.argv[1]
    if os.path.isdir(path_):
        logging.basicConfig(format='%(funcName)s: %(message)s',
                            level=logging.WARNING)
        with open('list.txt', 'w') as f:
            for entry in os.scandir(path_):
                print(entry.name)
                mov = Movie(os.path.join(path_, entry.path), api=api_)
                shootid_cv = api_.get_shootid_through_image_recognition(entry.path)
                if shootid_cv <= 0:
                    shootid_cv = api_.get_shootid_through_metadata(entry.path)
                shootid_nr = mov.get_shootids_from_filename(entry.path)
                if len(shootid_nr) == 1 and shootid_cv == shootid_nr[0] or \
                        not shootid_nr and shootid_cv:
                    continue
                f.write("{} -> {}\n".format(entry.path, shootid_cv))
        sys.exit(0)

    logging.basicConfig(format='%(funcName)s: %(message)s',
                        level=logging.DEBUG)

    print(api_.get_shootid_through_image_recognition(path_))

