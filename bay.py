#!/usr/bin/env python

import requests
from datetime import datetime
import sys
import json

MIRROR = 'https://tpb23.ukpass.co'
CATEGORIES = 'categories.json'
SHORT_CATEGORIES = 'categories_short.json'

class Bay():

    def __init__(self, default_mirror=None, timeout=5):
        self.mirror_list_url = 'https://proxy-bay.app/list.txt'
        self.timeout = timeout
        self.available_mirrors = self.get_mirror_list()
        with open(CATEGORIES, 'r') as c:
            self.categories = json.load(c)
        with open(SHORT_CATEGORIES, 'r') as sc:
            self.categories_short = json.load(sc)

        if default_mirror is None:
            self.mirror = self.update_mirror()
        else:
            self.mirror = default_mirror
            mirror_status = requests.get(self.mirror, timeout=self.timeout)
            if not mirror_status.ok: self.mirror = self.update_mirror()

    def get_mirror_list(self):
        """Return list of mirrors from published proxy-bay list."""

        list_response = requests.get(self.mirror_list_url, timeout=self.timeout)
        if not list_response.ok:
            print('unable to connect to {} : status code {}'.format(self.mirror_list_url, list_response.status_code))
            return None
        return list_response.text.splitlines()[3:]

    def get_mirror_responses(self, update_list=True):
        """Get response times from all mirrors (raw microseconds)."""

        if update_list: self.available_mirrors = self.get_mirror_list()
        response_times = {m: requests.get(m).elapsed for m in self.available_mirrors}
        return dict(sorted(response_times.items(), key=lambda t: t[1]))

    def get_active_mirror_response(self):
        """Return response time of current mirror in seconds (to the millisecond)."""
        return '{0:.3f}'.format(requests.get(self.mirror, timeout=self.timeout).elapsed.microseconds / 1000000)

    def update_mirror(self, update_list=True):
        """Get response times from all mirrors and make fasted mirror active."""
        response_times = self.get_mirror_responses(update_list=update_list)
        return min(response_times, key=response_times.get)

    def search(self, query, category='All'):
        """Return search query."""
        url = '{}/apibay/q.php'.format(self.mirror)
        query = {
            'q': query,
            'cat': self.__category_map(category),
        }
        response = requests.get(url, params=query, timeout=self.timeout)
        results = response.json()

        if results[0]['name'] == 'No results returned' and results[0]['id'] == '0':
            return [None]

        results = self.__format_results(results)

        return results

    def browse(self, category):
        query = 'category:{}'.format(self.__category_map(category))
        return self.search(query)

    def filenames(self, id_no):
        """Return filename and filesize data for listing."""

        url = '{}/apibay/f.php'.format(self.mirror)
        response = requests.get(url, params={'id': id_no}, timeout=self.timeout)
        results = response.json()
        for i,r in enumerate(results):
            try:
                r['name'] = r['name']['0']
                r['size'] = self.__filesize_readable(r['size']['0'])
            except:
                r['name'] = r['name'][0]
                r['size'] = self.__filesize_readable(r['size'][0])
            # r['magnet'] = 'magnet:?xt=urn:btih:{}&dn={}&so={}'.format(init_data['info_hash'], r['name'], i) # 'so=' not handled by clients?
        return results

    def description(self, id_no):
        """Return user-provided description for listing."""

        url = '{}/apibay/t.php'.format(self.mirror)
        response = requests.get(url, params={'id': id_no}, timeout=self.timeout)
        results = response.json()
        return results['descr']

    def __category_map(self, cat):
        """Mapping category or abbreviated category to ID."""

        if cat in self.categories_short:
            return self.categories_short[cat]

        categories_no_case = {k.lower(): v for k,v in self.categories.items()}
        video_categories = {k.split('/')[-1]: v for k,v in categories_no_case.items() if str(v).startswith('2')}
        cat = cat.lower()
        if cat in video_categories:
            return video_categories[cat]
        elif cat in categories_no_case:
            return categories_no_case[cat]
        else:
            return 0

    def __filesize_readable(self, num, suffix='B'):
        """Return human-readable filesize from bytes."""

        num = int(num)
        for unit in ['','K','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return "%3.1f %s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f %s%s" % (num, 'Yi', suffix)

    def __format_results(self, results):
        """Generate formatting item details from API response."""

        for r in results:
            r['size'] = self.__filesize_readable(r['size'])
            r['magnet'] = 'magnet:?xt=urn:btih:{}&dn={}'.format(r['info_hash'], r['name']).replace(' ', '%20')
            r['added'] = datetime.strftime(datetime.fromtimestamp(int(r['added'])),'%Y-%m-%d %H:%M')
            r['num_files'] = r['num_files'] if int(r['num_files']) > 0 else '1'
            r['category_name'] = self.__get_key(int(r['category']), self.categories)

        return results

    def __get_key(self, val, source_dict):
        """Fetch dictionary key with value."""
        for key, value in source_dict.items():
            if val == value:
                return key

def main():
    from pprint import pprint

    bay = Bay(MIRROR)
    results = bay.search(sys.argv[1], sys.argv[2])
    pprint(results)

if __name__ == '__main__':
    main()
