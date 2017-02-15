import logging
import os
import re
import tqdm
from cv2 import imread
from ftplib import FTP
import datetime

from apis.kink_api import KinkAPI
from fuzzywuzzy import fuzz
#from kinksorter import KinkSorter


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super(self.__class__, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class Settings:
    RECURSION_DEPTH = 10
    interactive = False
    simulation = True
    apis = {'Default': None}

    def __init__(self, args):
        self.interactive = args.get('interactive', False)
        self.simulation = not args.get('tested', False)
        use_api = not args.get('use_direct', False)

        kink_templates_sorted = []
        template_dir = args.get('shootid_template_dir', None)
        if template_dir and os.path.exists(template_dir):
            kink_templates_ = []
            for template_ in os.scandir(template_dir):
                if template_.name.endswith('.jpeg'):
                    kink_templates_.append(template_.path)

            for template_ in sorted(kink_templates_):
                kink_templates_sorted.append(imread(template_, 0))

        self.apis[KinkAPI.name] = KinkAPI(kink_templates_sorted, use_api=use_api)
        if self.interactive:
            # Default to most probable API only if interactive, so the results are validated by user
            self.apis['Default'] = self.apis[KinkAPI.name]

    def apis_use_cache(self):
        for api in self.apis.values():
            if api is not None:
                api.use_cache()


class FileProperties:
    file_path = None
    base_name = None
    extension = None
    relative_path = None
    subdirectory_path = None
    storage_root_path = None

    def __init__(self, file_path, storage_root_path='/', **kwargs):
        if file_path.startswith(storage_root_path):
            self.relative_path = file_path[len(storage_root_path):]
        else:
            self.relative_path = file_path

#        if KinkSorter.UNSORTED_DIRECTORY_NAME in self.relative_path:
#            pos = self.relative_path.find(KinkSorter.UNSORTED_DIRECTORY_NAME)
#            self.relative_path = self.relative_path[pos+len(KinkSorter.UNSORTED_DIRECTORY_NAME)+1:]

        if self.relative_path.startswith('/'):
            self.relative_path = self.relative_path[1:]

        self.file_path = file_path
        self.storage_root_path = storage_root_path
        t_, self.extension = os.path.splitext(self.relative_path)
        self.subdirectory_path, self.base_name = os.path.split(t_)

        if not self.base_name:
            print('no base name', file_path, storage_root_path)

    def serialize(self):
        return {'file_path': self.file_path, 'storage_root_path': self.storage_root_path}

    def print_base_name(self):
        return self.base_name[:50]


class SceneProperties:
    """ The properties of a scene. Takes care that there is always a non-true default value."""
    title = None
    performers = None
    site = None
    date = None
    shootid = None

    def __init__(self, title=None, performers=None, site=None, date=None, shootid=None, **kwargs):
        self.set_title(title)
        self.set_performers(performers)
        self.set_site(site)
        self.set_date(date)
        self.set_shootid(shootid)

    def set_title(self, title):
        if title is not None and type(title) is str:
            self.title = title
        else:
            self.title = ''
            
    def set_site(self, site):
        if site is not None and type(site) is str:
            self.site = site
        else:
            self.site = ''
            
    def set_shootid(self, shootid):
        if shootid is not None and type(shootid) is int:
            self.shootid = shootid
        else:
            self.shootid = 0
            
    def set_performers(self, performers):
        if performers is not None and type(performers) is list:
            self.performers = performers
        else:
            self.performers = []

    def set_date(self, date):
        try:
            if type(date) is datetime.date:
                self.date = date
            elif type(date) is int or (type(date) is str and date.isdigit()):
                self.date = datetime.date.fromtimestamp(int(date))
            elif type(date) is str:
                self.date = datetime.datetime.strptime('%Y-%m-%d', date).date()
            else:
                self.date = datetime.date.fromtimestamp(0)
        except (ValueError, TypeError):
            self.date = datetime.date.fromtimestamp(0)

    def serialize(self):
        return {'title': self.title, 'site': self.site, 'shootid': self.shootid,
                'performers': self.performers, 'date': int(self.date.strftime('%s'))}

    def is_filled(self):
        return bool(self.title
                    and self.performers
                    and self.site
                    and int(self.date.strftime("%s")) > 0
                    and self.shootid > 0)

    def is_empty(self):
        return bool(self.title is ''
                    and self.performers == []
                    and self.site is ''
                    and int(self.date.strftime('%s')) <= 0
                    and self.shootid is 0)

    def __bool__(self):
        return not self.is_empty()

    def __str__(self):
        if not bool(self):
            return ''
        return '{site} - {date} - {title} [{perfs}] ({shootid})'.format(
            site=self.site.replace(' ', '') if self.site else None,
            date=self.date if int(self.date.strftime('%s')) > 0 else None,
            title=self.title if self.title else None,
            perfs=', '.join((str(i) for i in self.performers)) if self.performers else None,
            shootid=self.shootid if self.shootid > 0 else None)

    def __eq__(self, other):
        return (type(other) is SceneProperties
                and self.title == other.title
                and self.performers == other.performers
                and self.date == other.date
                and self.site == other.site
                and self.shootid == other.shootid)

    def update(self, new_values_dict):
        if 'title' in new_values_dict:
            self.set_title(new_values_dict.get('title'))
        if 'performers' in new_values_dict:
            self.set_performers(new_values_dict.get('performers'))
        if 'date' in new_values_dict:
            self.set_date(new_values_dict.get('date'))
        if 'site' in new_values_dict:
            self.set_site(new_values_dict.get('site'))
        if 'shootid' in new_values_dict:
            self.set_shootid(new_values_dict.get('shootid'))


def get_correct_api(apis, dir_name):
    scores = []
    for name, api in apis.items():
        if api is None:
            continue

        responsibilities = api.get_site_responsibilities()
        for resp in responsibilities:
            score = fuzz.token_set_ratio(dir_name, resp)
            scores.append((score, api, resp))

    scores.sort(key=lambda f: f[0])
    if scores and scores[-1][0] > 85:
        return scores[-1][1]

    logging.warning('Found no suitable API for folder "{}". '
                    'Not yet supported or consider naming it more appropriate'.format(dir_name))
    return None


def get_ftp_listing(address):
    if address.startswith('ftp://'):
        # TODO: Test
        pro_, to_, server, path_ = address.split('/', 3)
        login, server = server.split('@') if '@' in server else ('', server)
        ftp_server = FTP(server)
        if login:
            user, password = login.split(':')
            ftp_server.login(user, password)

        listing = {}
        _search_ftp_server(ftp_server, path_, listing, 5)
        return listing
    else:
        print('ftps not (yet?) implemented!')


def _search_ftp_server(ftp_server, path_, listing, recursion_depth):
    # TODO: Test
    recursion_depth -= 1
    ftp_server.cwd(path_)
    for name, facts in ftp_server.mlsd(facts=["type", "media-type", "perm"]):
        print(path_, name, facts)
        if "type" in facts and facts["type"] == 'dir':
            if recursion_depth > 0:
                _search_ftp_server(ftp_server, os.path.join(path_, name), recursion_depth)
        else:
            listing[path_] = (name, facts)


def get_http_listing(address):
    # TODO
    return {}


def get_remote_file(address):
    if re.match(r'https?://', address):
        return _get_http_file(address)
    if re.match(r'ftps?://', address):
        return _get_ftp_file(address)


def _get_http_file(address):
    # TODO
    return None


def _get_ftp_file(address):
    # TODO
    return None
