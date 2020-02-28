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
        Exception.__init__(self, "The Argument Given Is Not Valid. Invalid Argument:{}".format(err))


class ArgumentNotValidError(Exception):

    def __init__(self,
                 err="Arguments Not Valid! Format: python '/path/to/file' url "
                     "user password GET/POST (post data if is post)"):
        Exception.__init__(self, err)
