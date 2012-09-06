"""
wbdata.fetcher: retrieve and cache queries
"""

#Copyright (C) 2012  Oliver Sherouse <Oliver DOT Sherouse AT gmail DOT com>

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, unicode_literals

import datetime
import json
import logging
import os.path
import time

try:  # python 2
    import cPickle as pickle
    from urllib2 import urlopen
    from urllib import urlencode
except ImportError:  # python 3
    import pickle
    from urllib.request import urlopen
    from urlllib.parse import urlencode

import appdirs

CACHEDIR = appdirs.user_cache_dir("wbdata", appauthor="wbdata")
if not os.path.exists(CACHEDIR):
    os.mkdir(CACHEDIR)
CACHEPATH = os.path.join(CACHEDIR, "cache")
PER_PAGE = 1000
DATE_IDX = 0
DATA_IDX = 1
TRIES = 5


class Fetcher(object):
    """
    An object with a cache to retrieve and page responses from the World
    Bank API
    """
    def __init__(self):
        """@todo: to be defined """
        try:
            with open(CACHEPATH) as cachefile:
                self.cache = pickle.load(cachefile)
        except IOError:
            self.cache = {}

    def fetch(self, query_url, args=None, cached=True):
        """fetch data from the World Bank API or from cache

        :query_url: the base url to be queried
        :args: a dictionary of GET arguments
        :cached: use the cache
        :returns: a list of dictionaries containing the response to the query
        """
        if not args:
            args = []
        args.extend([("format", "json"), ("per_page", PER_PAGE)])
        query_url = "?".join((query_url, urlencode(args)))
        logging.debug("Query using {0}".format(query_url))
        print(query_url)
        if cached and query_url in self.cache:
            results = self.cache[query_url][DATA_IDX]
        else:
            results = self.__get_paged_data(query_url)
            self.cache[query_url] = (datetime.date.today().toordinal(),
                                     results)
            self.sync_cache()
        return results

    def prune(self, age=30):
        """Delete all entries more than age days old

        :age: the max age (in days) of an entry
        """
        min_date = datetime.date.today().toordinal() - 30
        for i in self.cache:
            if self.cache[i][DATE_IDX] < min_date:
                del(self.cache[i])
        self.sync_cache()

    def sync_cache(self):
        """Sync cache to disk"""
        with open(CACHEPATH, 'wb') as cachefile:
            pickle.dump(self.cache, cachefile,
                        protocol=pickle.HIGHEST_PROTOCOL)

    def __get_paged_data(self, query_url):
        results = []
        original_url = query_url
        while 1:
            thistry = 0
            while 1:
                try:
                    query = urlopen(query_url)
                    response = json.load(query)
                    query.close()
                    break
                except StandardError as e:
                    if thistry < TRIES:
                        continue
                    else:
                        raise e
            results.extend(response[1])
            this_page = response[0]['page']
            pages = response[0]['pages']
            logging.debug("Processed page {0} of {1}".format(this_page, pages))
            if this_page == pages:
                break
            query_url = original_url + "&page={0}".format(int(this_page + 1))
            time.sleep(1)
        return results