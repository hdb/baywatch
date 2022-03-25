#!/usr/bin/env python

import requests
from datetime import datetime
import sys
import json

import tpb_categories

MIRROR = 'https://tpb23.ukpass.co'

class Bay():

    def __init__(self, default_mirror=None):
        self.mirror_list_url = 'https://proxy-bay.app/list.txt'
        self.available_mirrors = self.getMirrorList()

        if default_mirror is None:
            self.mirror = self.updateMirror()
        else:
            self.mirror = default_mirror
            mirror_status = requests.get(self.mirror)
            if not mirror_status.ok: self.mirror = self.updateMirror()

    def getMirrorList(self):
        list_response = requests.get(self.mirror_list_url)
        if not list_response.ok:
            print('unable to connect to {} : status code {}'.format(self.mirror_list_url, list_response.status_code))
            return None
        return list_response.text.splitlines()[3:]

    def getMirrorResponses(self, update_list=True):
        if update_list: self.available_mirrors = self.getMirrorList()
        response_times = {m: requests.get(m).elapsed for m in self.available_mirrors}
        return dict(sorted(response_times.items(), key=lambda t: t[1]))

    def getActiveMirrorResponse(self):
        """Return time in seconds (to the millisecond)."""
        return '{0:.3f}'.format(requests.get(self.mirror).elapsed.microseconds / 1000000)

    def updateMirror(self, update_list=True):
        response_times = self.getMirrorResponses(update_list=update_list)
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
            return [None]

        results = self.__formatResults(results)

        return results

    def filenames(self, id_no):
        url = '{}/apibay/f.php'.format(self.mirror)
        response = requests.get(url, params={'id': id_no})
        results = response.json()
        for i,r in enumerate(results):
            try:
                r['name'] = r['name']['0']
                r['size'] = self.__fileSizeReadable(r['size']['0'])
            except:
                r['name'] = r['name'][0]
                r['size'] = self.__fileSizeReadable(r['size'][0])
            # r['magnet'] = 'magnet:?xt=urn:btih:{}&dn={}&so={}'.format(init_data['info_hash'], r['name'], i) # 'so=' not handled by clients?
        return results

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
