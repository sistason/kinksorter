import hashlib
import requests
import json


def interactive_query(file_path, likely_date=''):
    # TODO: query which movie
    """
    new_query = likely_date
    do
      result = query(new_query)
      answer = input($formated_result okay? Y, n, new_query)
      parse_answer
    until not answer
    return result
    """

    if likely_date:
        result = query_api('date', likely_date)

    return {}

def interactive_confirm(file_path, result):
    print('Is this okay?')
    print('{} -> {}'.format(file_path, result))
    answer = input('Y, n?')
    return True if not answer or answer.lower().startswith('y') else False

def interactive_choose_kinkid(file_path, likely_ids):
    # TODO: query by input() or Qt
    return likely_ids[0]

def query_api(type_, query):
    ret = None
    if type_ == 'id':
        ret = query_for_id(query)
    if type_ == 'name':
        ret = query_for_name(query)
    if type_ == 'date':
        ret = query_for_date(query)

    if ret is not None:
        _decoded = json.loads(ret.text)
        if _decoded.get('Response', False):
            _decoded.pop('Response')
            return _decoded


def query_for_id(kink_id):
    try:
        "iafd.com"
    except requests.HTTPError as e:
        return None

def query_for_name(name):
    ...

def query_for_date(date):
    ...