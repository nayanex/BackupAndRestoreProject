import requests


class GetMethod(object):

    def __init__(self, url, header):
        self.url = url
        self.header = header

    def get_method(self):
        print(self.url)
        response = requests.get(self.url, headers=self.header, verify=False)
        return response
