import json
import sys

from Response import Response


class UserInteractiveResponse(object):

    def __init__(self):
        self.url = sys.argv[1].strip()
        self.user = sys.argv[2].strip()
        self.password = sys.argv[3].strip()
        self.method = sys.argv[4].strip()
        if self.method == 'POST':
            self.post_data = sys.argv[5].strip()
            print("=====================api info==============================")
            print(self.url, self.user, self.password, self.method, self.post_data)
        else:
            print("=====================api info==============================")
            print(self.url, self.user, self.password, self.method)

    def user_interactive(self):
        if self.method == 'POST':
            res = Response(self.url, self.user, self.password, self.method, self.post_data)
        elif self.method == 'GET':
            res = Response(self.url, self.user, self.password, self.method)
        else:
            print("Arguments Are Not Valid.")
            sys.exit(1)
        try:
            data = res.response().json()
            print(json.dumps(data, indent=1))
        except Exception as exception:
            print(exception)
            print(res.response())
            sys.exit(1)


uir = UserInteractiveResponse()
uir.user_interactive()
