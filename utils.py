import hashlib
import requests
import json


def query_api(type_, query):
    if type_ == 'imdbID':
        ret = query_imdbid(query)

    if ret is not None:
        _decoded = json.loads(ret.text)
        if _decoded.get('Response', False):
            _decoded.pop('Response')
            return _decoded


def query_imdbid(imdb_id):
    try:
        return requests.get("http://www.omdbapi.com", {'i': imdb_id})
    except requests.HTTPError as e:
        return None