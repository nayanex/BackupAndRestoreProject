import json
from urlparse import urlparse

import KotobaExceptions
import requests
from requests.auth import HTTPBasicAuth

# from urllib.parse import urlparse


class GenerateSecretKey(object):
    """class for generate SecretKey."""

    # init url, user, password
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password

    # update password
    def update_pass(self, new_password):
        self.password = new_password

    # generate SecretKey from user and password
    def generate_secret_key(self):
        # parse url
        parse_url = urlparse(self.url)
        scheme = parse_url.scheme
        netloc = parse_url.netloc

        auth_header = {'content-type': 'application/json'}
        auth_data = {'userid': self.user, 'password': self.password}
        if "kotoba" in self.url:
            auth_data = {'userid': self.user, 'password': self.password}
            auth_resp = requests.post(
                '{0}://{1}/kotoba/rest/user/authenticate'.format(scheme, netloc), data=json.dumps(
                    auth_data), auth=HTTPBasicAuth(self.user, self.password), headers=auth_header,
                verify=False, stream=True)

            if auth_resp.status_code == 200:
                auth_resp_json = auth_resp.json()
                secret_key = auth_resp_json['data']["secretKey"]
                status_res = auth_resp_json['success']

                self.write_kotoba_secret_key(secret_key, status_res)
            else:
                try:
                    raise KotobaExceptions.AuthenticationError(auth_resp.status_code)
                except KotobaExceptions.AuthenticationError as e:
                    print(e)
                    exit()

        elif "Ronin" in self.url:
            auth_resp = requests.get(
                '{0}://{1}/Ronin/rest/user/authenticate'.format(scheme, netloc),
                data=json.dumps(auth_data), auth=HTTPBasicAuth(self.user, self.password),
                headers=auth_header, verify=False, stream=True)
            with open('secretKey', 'w') as f:
                f.write(auth_resp.text)

    @staticmethod
    def write_kotoba_secret_key(secret_key, status_res):
        if status_res:
            with open('secretKey', 'w') as f:
                f.write(secret_key)
        else:
            try:
                raise KotobaExceptions.SecretKeyGenerateError()
            except KotobaExceptions.SecretKeyGenerateError as e:
                print(e)
                exit()
