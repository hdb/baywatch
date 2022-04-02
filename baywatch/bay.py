#!/usr/bin/env python

from __future__ import annotations

import requests
import urllib.parse
from datetime import datetime
import json
import os

from baywatch.version import __version__

CATEGORIES = os.path.join(os.path.dirname(__file__), 'data/categories.json')
SHORT_CATEGORIES = os.path.join(os.path.dirname(__file__), 'data/categories_short.json')
MIRRORS = os.path.join(os.path.dirname(__file__), 'data/mirrors.txt')
TRACKERS = os.path.join(os.path.dirname(__file__), 'data/trackers.txt')

class Bay():

    def __init__(self, default_mirror: str | None = None, default_timeout: int = 5, user_agent: str = 'bay-v{}'.format(__version__)) -> None:

        self.mirror_list_url = 'https://proxy-bay.app/list.txt'

        self.timeout = default_timeout
        self.headers = {'User-Agent': user_agent}

        with open(CATEGORIES, 'r') as c:
            self.categories = json.load(c)
        with open(SHORT_CATEGORIES, 'r') as sc:
            self.categories_short = json.load(sc)

        if default_mirror is None:
            self.mirror = self.update_mirror()
        else:
            self.mirror = default_mirror
            mirror_status = self.__requests_get(self.mirror)
            if not mirror_status.ok: self.mirror = self.update_mirror()

        self.announce = self.build_announce_list()

    def get_mirror_list(self, local: bool = False) -> list[str]:
        """Return list of mirrors from published proxy-bay list. Uses local list if 'local' is True or if unable to reach proxy-bay."""

        if local:
            with open(MIRRORS, 'r') as f:
                return f.read().splitlines()

        list_response = self.__requests_get(self.mirror_list_url)
        if not list_response.ok:
            with open(MIRRORS, 'r') as f:
                return f.splitlines()
        return list_response.text.splitlines()[3:]

    def get_mirror_responses(self, update_list: bool = True) -> dict:
        """Get response times from all mirrors (raw microseconds)."""

        if update_list: self.available_mirrors = self.get_mirror_list()
        response_times = {m: self.__requests_get(m).elapsed for m in self.available_mirrors}
        return dict(sorted(response_times.items(), key=lambda t: t[1]))

    def get_active_mirror_response(self) -> str:
        """Return response time of current mirror in seconds (to the millisecond)."""
        return '{0:.3f}'.format(self.__requests_get(self.mirror).elapsed.microseconds / 1000000)

    def update_mirror(self, update_list: bool = True) -> str:
        """Get response times from all mirrors and make fasted mirror active."""
        response_times = self.get_mirror_responses(update_list=update_list)
        return min(response_times, key=response_times.get)

    def build_announce_list(self) -> str:
        """Build announce list"""

        with open(TRACKERS, 'r') as f:
            trackers = f.read().splitlines()
        return '&'.join([f'tr={urllib.parse.quote_plus(t)}' for t in trackers if len(t)>0])

    def search(self, query: str, category: str ='All') -> dict:
        """Return search query."""
        url = '{}/apibay/q.php'.format(self.mirror)
        query = {
            'q': query,
            'cat': self.__category_map(category),
        }
        response = self.__requests_get(url, params=query)
        results = response.json()

        if results[0]['name'] == 'No results returned' and results[0]['id'] == '0':
            return [None]

        results = self.__format_results(results)

        return results

    def browse(self, category: str) -> dict:
        query = 'category:{}'.format(self.__category_map(category))
        return self.search(query)

    def filenames(self, id_no: str| int) -> list:
        """Return filename and filesize data for listing."""

        url = '{}/apibay/f.php'.format(self.mirror)
        response = self.__requests_get(url, params={'id': id_no})
        results = response.json()
        for i,r in enumerate(results):
            try:
                r['name'] = r['name']['0']
                r['size'] = self.__filesize_readable(r['size']['0'])
            except:
                r['name'] = r['name'][0]
                r['size'] = self.__filesize_readable(r['size'][0])
            # r['magnet'] = 'magnet:?xt=urn:btih:{}&dn={}&so={}'.format(init_data['info_hash'], r['name'], i) # 'so=' not handled by clients?

        if len(results) == 1 and results[0]['size'] == '0.0 B':
            return []

        return results

    def description(self, id_no: str| int) -> str:
        """Return user-provided description for listing."""

        url = '{}/apibay/t.php'.format(self.mirror)
        response = self.__requests_get(url, params={'id': id_no})
        results = response.json()
        return results['descr']

    def __requests_get(self, url: str, params: dict| None = None, timeout: int | None = None, headers: dict | None = None) -> requests.models.Response:
        timeout = self.timeout if timeout is None else timeout
        headers = self.headers if headers is None else headers
        return requests.get(url, params=params, timeout=timeout, headers=headers)

    def __category_map(self, cat: str) -> int:
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

    def __filesize_readable(self, num: int | float | str, suffix: str = 'B') -> str:
        """Return human-readable filesize from bytes."""

        num = int(num)
        for unit in ['','K','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return "%3.1f %s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f %s%s" % (num, 'Yi', suffix)

    def __format_results(self, results: dict) -> dict:
        """Generate formatting item details from API response."""

        for r in results:
            r['size'] = self.__filesize_readable(r['size'])
            r['magnet'] = f"magnet:?xt=urn:btih:{r['info_hash']}&dn={urllib.parse.quote_plus(r['name'])}&{self.announce}"
            r['added'] = datetime.strftime(datetime.fromtimestamp(int(r['added'])),'%Y-%m-%d %H:%M')
            r['num_files'] = r['num_files'] if int(r['num_files']) > 0 else '1'
            r['category_name'] = self.__get_key(int(r['category']), self.categories)

        return results

    def __get_key(self, val: str, source_dict: dict) -> str | int | object:
        """Fetch dictionary key with value."""
        for key, value in source_dict.items():
            if val == value:
                return key
