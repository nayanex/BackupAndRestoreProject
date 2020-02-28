from GetMethod import GetMethod
import Headers
from PostMethod import PostMethod
import SecretKey


class Response(object):

    def __init__(self, url, user, password, method, data_post=''):
        self.url = url
        self.user = user
        self.password = password
        self.method = method
        self.data_post = data_post
        print('\n\n#####################Starting#####################\n\n')
        secret_key = SecretKey.GenerateSecretKey(url, user, password)
        secret_key.generate_secret_key()
        self.header = Headers.Header(self.url, self.user).headers()

        '''
        my_file = Path("secretKey")
        if my_file.is_file():
            pass
        else:
            gene_SecretKey=SecretKey.GenerateSecretKey(url,user,password)
            gene_SecretKey.generateSecretKey()
        header=Headers.Header(self.url,self.user).headers()
        '''

    def re_init(self):
        secret_key = SecretKey.GenerateSecretKey(self.url, self.user, self.password)
        secret_key.generate_secret_key()
        self.header = Headers.Header(self.url, self.user, self.password).headers()

    def response(self):
        if self.method == 'GET':
            res = GetMethod(self.url, self.header).get_method()
            if res.status_code == 200:
                print("Code: {}".format(res.status_code))
                print('\n\n#####################Finished#####################\n\n')
            elif res.status_code == 401:
                self.re_init()
                res = GetMethod(self.url, self.header).get_method()
                print("Code: {}".format(res.status_code))
            else:
                print("Code: {}".format(res.status_code))
        elif self.method == 'POST':
            res = PostMethod(self.url, self.data_post, self.header).post_method()
            if res.status_code == 200:
                print('\n\n#####################Finished#####################\n\n')
            elif res.status_code == 401:
                self.re_init()
                res = PostMethod(self.url, self.data_post, self.header).post_method()
            else:
                print("Code: {}".format(res.status_code))
        else:
            print("Arguments Are Not Valid.")
            return
        return res


'''
if __name__ == '__main__':
    r = Response()
    r.init("https://cix0007.us.cixsoft.net:8090/kotoba/rest/applications/agents/"
           "addAgent?appid=0cbc6611-f554-3bd0-809a-388dc95a615b", "admin", "floatingman",
           "POST","[{'key':'4ee78fe4-9324-3600-a4f4-4fedc88c81e8','value':'AD SERVER'}]")

    print(r.response().json())

'''
