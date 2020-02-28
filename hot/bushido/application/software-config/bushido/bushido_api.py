import base64
from hashlib import sha1
import hmac
import json
import sys
from time import time
import urllib2
from urlparse import urlparse


class BushidoApi(object):

    def __init__(self):
        self.url = sys.argv[1].strip()
        self.user = sys.argv[2].strip()
        self.password = sys.argv[3].strip()
        self.post_data = sys.argv[4].strip()

        print("=====================api info==============================")
        print("url: {}, user: {}, password: {}, post_data: {}"
              .format(self.url, self.user, self.password, self.post_data))

        self.bushido_header = self.create_bushido_header()

    def create_bushido_header(self):
        try:
            secret_key = self.generate_secret_key()
        except Exception as e:
            print(e)
            exit()

        cur_time = str(round(time() * 1000))
        signing = hmac.new(secret_key.encode(), (urlparse(self.url).path + cur_time).encode(),
                           sha1)
        str_encode = self.user + ":" + signing.hexdigest()
        header = {"Authorization": "HMAC %s".encode() % base64.b64encode(str_encode.encode()),
                  "time": cur_time,
                  "Content-Type": "application/json"}
        print(header)
        return header

    def generate_secret_key(self):
        parse_url = urlparse(self.url)
        scheme = parse_url.scheme
        netloc = parse_url.netloc

        auth_data = {"userid": self.user, "password": self.password}

        if "kotoba" in self.url:
            kotoba_request = self.create_request("{0}://{1}/kotoba/rest/user/authenticate"
                                                 .format(scheme, netloc), auth_data)
            kotoba_auth_resp = urllib2.urlopen(kotoba_request)
            if kotoba_auth_resp.code == 200:
                auth_resp_json = json.load(kotoba_auth_resp)
                secret_key = auth_resp_json["data"]["secretKey"]
                status_res = auth_resp_json["success"]

                if status_res:
                    return secret_key
                else:
                    raise SecretKeyGenerateError()
            else:
                raise AuthenticationError(kotoba_auth_resp.status_code)

        elif "Ronin" in self.url:
            ronin_request = self.create_request("{0}://{1}/Ronin/rest/user/authenticate"
                                                .format(scheme, netloc), auth_data)
            ronin_auth_resp = urllib2.urlopen(ronin_request)
            return ronin_auth_resp.read()

    def create_request(self, url, json_data):
        req = urllib2.Request(url, data=json.dumps(json_data))
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Basic %s" % self.encode_user_password())
        return req

    def send_request(self):
        response = self.send_post_request()
        if response.code == 200:
            print("\n\n#####################Cluster creation finished#####################\n\n")
            return json.load(response)
        elif response.code == 401:
            self.bushido_header = self.create_bushido_header()
            response = self.send_post_request()
            if response.code != 200:
                raise CreateClusterError(response.code)
        else:
            raise CreateClusterError(response.code)

    def send_post_request(self):
        request = urllib2.Request(self.url, data=json.dumps(self.post_data),
                                  headers=self.bushido_header)
        return urllib2.urlopen(request)

    def encode_user_password(self):
        return base64.b64encode("%s:%s" % (self.user, self.password))


class CreateClusterError(Exception):
    def __init__(self, error_code):
        Exception.__init__(self, "Unable to create cluster. Error code: {}".format(error_code))


class AuthenticationError(Exception):
    def __init__(self, error_code):
        if error_code == 401:
            Exception.__init__(self,
                               "Authentication Error, Please Check Your Credentials! "
                               "Error Code: {}, Please Refer to "
                               "'https://en.wikipedia.org/wiki/List_of_HTTP_status_codes' "
                               "For More Info".format(error_code))
        else:
            Exception.__init__(self, "Error Code: {}, Please Refer to "
                                     "'https://en.wikipedia.org/wiki/List_of_HTTP_status_codes' "
                                     "For More Info".format(error_code))


class SecretKeyGenerateError(Exception):
    def __init__(self, err="Secert Key Generate Error"):
        Exception.__init__(self, err)


class ArgumentsError(Exception):
    def __init__(self, err):
        Exception.__init__(self, "The Argument Given Is Not Valid. Invalid Argument: {}"
                           .format(err))


class ArgumentNotValidError(Exception):
    def __init__(self,
                 err="Arguments Not Valid! Format: python '/path/to/file' url "
                     "user password GET/POST (post data if is post)"):
        Exception.__init__(self, err)


bushido_api = BushidoApi()
bushido_api.send_request()
