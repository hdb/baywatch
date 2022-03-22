#!/usr/bin/env python

import requests
from datetime import datetime
import sys

import tpb_categories

MIRROR = 'https://tpb23.ukpass.co'

class Bay():

    def __init__(self, default_mirror=None):
        self.mirror_list = 'https://proxy-bay.app/list.txt'

        if default_mirror is None:
            self.mirror = self.updateMirror()
        else:
            self.mirror = default_mirror
            if not requests.get(self.mirror).ok: self.mirror = self.updateMirror()

    def updateMirror(self):
        list_response = requests.get(self.mirror_list)
        if not list_response.ok: return None
        mirrors = list_response.text.splitlines()[3:]
        response_times = {m: requests.get(m).elapsed for m in mirrors}
        return min(response_times, key=response_times.get)

    def __fileSizeReadable(self, num, suffix='B'):
        num = int(num)
        for unit in ['','K','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return "%3.1f %s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f %s%s" % (num, 'Yi', suffix)

    def __formatResults(self, results):

        for r in results:
            r['size'] = self.__fileSizeReadable(r['size'])
            r['magnet'] = 'magnet:?xt=urn:btih:{}&dn={}'.format(r['info_hash'], r['name']).replace(' ', '%20')
            r['added'] = datetime.strftime(datetime.fromtimestamp(int(r['added'])),'%Y-%m-%d %H:%M')
            r['num_files'] = r['num_files'] if int(r['num_files']) > 0 else '1'
            r['category_name'] = self.__get_key(int(r['category']), tpb_categories.categories)

        return results

    def __get_key(self, val, source_dict):
        for key, value in source_dict.items():
            if val == value:
                return key

    def search(self, query, category='All'):
        url = '{}/apibay/q.php'.format(self.mirror)
        query = {
            'q': query,
            'cat': tpb_categories.short[category] if category in tpb_categories.short else tpb_categories.categories[category],
        }
        response = requests.get(url, params=query)
        results = response.json()

        if results[0]['name'] == 'No results returned' and results[0]['id'] == '0':
            return []

        results = self.__formatResults(results)

        return results

    def filenames(self, init_data):
        url = '{}/apibay/f.php'.format(self.mirror)
        response = requests.get(url, params={'id': init_data['id']})
        results = response.json()
        for i,r in enumerate(results):
            r['name'] = r['name']['0']
            r['size'] = self.__fileSizeReadable(r['size']['0'])
            # r['magnet'] = 'magnet:?xt=urn:btih:{}&dn={}&so={}'.format(init_data['info_hash'], r['name'], i) # 'so=' not handled by clients?
        init_data['files'] = results
        return init_data

    def description(self, id_no):
        url = '{}/apibay/t.php'.format(self.mirror)
        response = requests.get(url, params={'id': id_no})
        results = response.json()
        return results['descr']


def main():
    from pprint import pprint

    bay = Bay(MIRROR)
    results = bay.search(sys.argv[1])
    pprint(results)

if __name__ == '__main__':
    main()
