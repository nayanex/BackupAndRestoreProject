import base64
import hashlib
import hmac
import time
from urlparse import urlparse


class Header(object):

    def __init__(self, url, user, password=''):
        self.user = user
        self.url = url
        self.password = password
        with open('secretKey', 'r') as f:
            self.secret_key = f.read()

    def headers(self):
        cur_time = str(round(time.time() * 1000))
        signing = hmac.new(self.secret_key.encode(), (urlparse(self.url).path + cur_time).encode(),
                           hashlib.sha1)
        str_encode = self.user + ":" + signing.hexdigest()
        header = {'Authorization': 'HMAC '.encode() + base64.b64encode(str_encode.encode()),
                  'time': cur_time,
                  'content-type': 'application/json'}
        print(header)
        return header


'''
if __name__=='__main__':
    h=Header("https://cix0007.us.cixsoft.net:8090/kotoba/rest/agent/allAgents?_dc=1484343770124",
             'admin')
    h.headers()
'''
