# -*- coding:utf-8 -*-

import urllib, json

from google.appengine.api import urlfetch

try:
    import urlparse
    from urllib import urlencode
except:  # For Python 3
    import urllib.parse as urlparse
    from urllib.parse import urlencode


def recursive_urlencode(d):
    """URL-encode a multidimensional dictionary.

    >>> data = {'a': 'b&c', 'd': {'e': {'f&g': 'h*i'}}, 'j': 'k'}
    >>> recursive_urlencode(data)
    u'a=b%26c&j=k&d[e][f%26g]=h%2Ai'
    """
    def recursion(d, base=[]):
        pairs = []

        for key, value in d.items():
            new_base = base + [key]
            if isinstance(value, dict):
                pairs += recursion(value, new_base)
            else:
                new_pair = None
                if len(new_base) > 1:
                    first = urllib.quote(new_base.pop(0))
                    rest = map(lambda x: urllib.quote(x), new_base)
                    new_pair = "%s[%s]" % (first, ']['.join(rest))
                else:
                    new_pair = "%s" % (urllib.quote(unicode(key)))

                if isinstance(value, (list, tuple)):
                    for key, val in enumerate(value):
                        new_pair = '{0}[{1}]={2}'.format(new_pair, key, urllib.quote(unicode(val)))
                        pairs.append(new_pair)
                elif value is not None:
                    new_pair = '{0}={1}'.format(new_pair, urllib.quote(unicode(value)))
                    pairs.append(new_pair)
        return pairs

    return '&'.join(recursion(d))


class requests(object):
    @classmethod
    def _call(cls, url, method, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        if 'auth' in kwargs:
            kwargs['headers']['Authorization'] = 'Basic {0}'.format(
                '{0}:{1}'.format(kwargs['auth'][0], kwargs['auth'][1]).encode('base64').replace("\n", "")
            )

        if 'params' in kwargs:
            # @see http://stackoverflow.com/a/2506477/330867
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(kwargs['params'])

            url_parts[4] = urlencode(query)

            url = urlparse.urlunparse(url_parts)

        payload = None
        if 'data' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
            payload = recursive_urlencode(kwargs['data'])

        if 'json' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            payload = json.dumps(kwargs['json'])

        if 'timeout' not in kwargs:
            kwargs['timeout'] = 3

        deadline = int(kwargs['timeout'])
        urlfetch.set_default_fetch_deadline(deadline)

        if 'files' in kwargs:
            pass

        rpc = urlfetch.create_rpc(deadline=deadline)
        urlfetch.make_fetch_call(
            rpc,
            url=url,
            method=method,
            headers=kwargs['headers'],
            payload=payload
        )

        if kwargs.get('async', False) is False:
            try:
                return Response(rpc.get_result())
            except:
                pass

        return Response(None)

    @classmethod
    def get(cls, url, **kwargs):
        return cls._call(url, urlfetch.GET, **kwargs)

    @classmethod
    def post(cls, url, **kwargs):
        return cls._call(url, urlfetch.POST, **kwargs)

    @classmethod
    def head(cls, url, **kwargs):
        return cls._call(url, urlfetch.HEAD, **kwargs)

    @classmethod
    def put(cls, url, **kwargs):
        return cls._call(url, urlfetch.PUT, **kwargs)

    @classmethod
    def delete(cls, url, **kwargs):
        return cls._call(url, urlfetch.DELETE, **kwargs)

    @classmethod
    def patch(cls, url, **kwargs):
        return cls._call(url, urlfetch.PATCH, **kwargs)


class Response(object):
    def __init__(self, fetched):
        self.status_code = None
        self.content = None
        self.headers = None
        self.fetched = fetched
        if self.fetched is not None:
            self.content = self.fetched.content
            self.status_code = self.fetched.status_code
            self.headers = self.fetched.headers

    def json(self):
        if self.content is None:
            return None

        try:
            return json.loads(self.content)
        except:
            return None

    def headers(self):
        return self.headers

    def get_header(self, name):
        return self.headers.get(name, None)

    def raise_for_status(self):
        if str(self.status_code)[0:1] in ['4', '5']:
            raise FRequestException("{0} status code error".format(self.status_code), self.status_code, self.content)


class FRequestException(Exception):
    def __init__(self, value, status_code, content):
        self.value = value
        self.status_code = status_code
        self.content = content

    def __str__(self):
        return repr(self.value)

    def __repr__(self):
        return repr(self.value)
