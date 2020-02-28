import requests


class PostMethod(object):

    def __init__(self, url, post_data, header):
        self.url = url
        self.post_data = post_data
        self.header = header

    def post_method(self):
        response = requests.post(self.url, headers=self.header, verify=False,
                                 data=self.post_data, stream=True)
        return response
