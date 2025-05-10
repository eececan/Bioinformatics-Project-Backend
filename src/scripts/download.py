import sys
from urllib.request import urlopen, Request
from urllib.parse import urlencode

def url_request(url, data):
    """
    Perform an HTTP URL request and return the HTML source.

    Parameters
    ----------
    url : str
        URL to request
    data : mapping object (ex. dict) or None
        Data to send in HTTP POST. They will be percent-encoded.
    """

    # User-Agent
    headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0' }

    # Prepare POST data for sending
    if data:
        data = urlencode(data).encode("utf-8")

    # Request
    retry = 0
    while retry < 3:
        try:
            req = Request(url, data, headers)
            return urlopen(req, timeout=30).read().decode(encoding="UTF-8")
        except:
            retry += 1
            e = sys.exc_info()[1]
            print(e)
            print("*** Retry (%d) URL:" % retry, url)
    return None
