import os
import logging
import re

from cv2 import imread
from fuzzywuzzy import fuzz
from ftplib import FTP

from api import KinkAPI



class Settings():
    RECURSION_DEPTH = 5
    interactive = False
    simulation = True
    shootid_template = None
    apis = {}

    def __init__(self, args):
        self.interactive = args.get('interactive', False)
        self.simulation = not args.get('tested', False)
        self._read_shootid_template(args.get('shootid_template', None))
        self.apis = {KinkAPI.name: KinkAPI()}

    def _read_shootid_template(self, template):
        if not template or not os.path.exists(template):
            return
        self.shootid_template = imread(template, 0)


def get_correct_api(apis, dir_name):
    scores = []
    for name, api in apis.items():
        responsibilities = api.get_site_responsibilities()
        for resp in responsibilities:
            score = fuzz.token_set_ratio(dir_name, resp)
            scores.append((score, api, resp))

    scores.sort(key=lambda f: f[0])
    if scores and scores[-1][0] > 85:
        return scores[-1][1]

    logging.warning('Found no suitable API for folder "{}", consider naming it more appropriate'.format(dir_name))
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
        _scan_ftp(ftp_server, path_, listing, 5)
        return listing
    else:
        print('ftps not (yet?) implemented!')


def _scan_ftp(ftp_server, path_, listing, recursion_depth):
    # TODO: Test
    recursion_depth -= 1
    ftp_server.cwd(path_)
    for name, facts in ftp_server.mlsd(facts=["type", "media-type", "perm"]):
        print(path_, name, facts)
        if "type" in facts and facts["type"] == 'dir':
            if recursion_depth > 0:
                _scan_ftp(ftp_server, os.path.join(path_, name), recursion_depth)
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
    ...


def _get_ftp_file(address):
    ...
