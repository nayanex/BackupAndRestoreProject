#!/usr/bin/env python

"""
Utils script for common use
"""
import ConfigParser
import json
import logging
import os
import subprocess
import sys
import urllib2
import requests

from requests.exceptions import RequestException

SCRIPT_NAME = os.path.basename(__file__)
LOG = logging.getLogger(SCRIPT_NAME)


def send_mail(email_url, sender, receiver, subject, message):
    """
    Prepares and sends e-mail over configured e-mail service via EMAIL_URL
    configuration property if Deployment's health check has failed.

    Args:
        email_url: url for e-mail service
        sender: from address the email is being sent
        receiver: receiver of the email
        subject: e-mail health check subject.
        message: e-mail health check message.

    Returns:
        True if the e-mail was sent. False if it failed.

    Raises:
        Nothing
    """
    LOG.info("Sending e-mail from '%s' to '%s'.", sender, receiver)

    personalisations = [{"to": [{"email": receiver}], "subject": subject}]
    json_string = {"personalizations": personalisations,
                   "from": {"email": sender},
                   "content": [{"type": "text/plain", "value": message}]}

    post_data = json.dumps(json_string).encode("utf8")
    hdrs = {'cache-control': 'no-cache', 'content-type': 'application/json'}
    req = urllib2.Request(email_url, data=post_data, headers=hdrs)

    try:
        response = urllib2.urlopen(req, timeout=10)
        if response.code == 200:
            LOG.info("Sent e-mail to: '%s'.", receiver)
            return True
        else:
            msg = "Failed to send e-mail to: '%s'. Bad response: '%s' - '%s'"
            LOG.error(msg, receiver, response.status_code, response)
    except urllib2.URLError as error:
        LOG.error("Failed to send e-mail to: '%s'. Exception: %s", receiver, error)

    return False


def err_exit(msg, code=1, log=None):
    """Print and optionally log an error message then exit

    Args:
       msg:  str error message
       code: int exit code, default 1
       log:  logger object, default None

    Returns:
        Nothing.  System exit.

    Raises:
        Nothing.
    """
    if log:
        log.error(msg)

    print msg
    sys.exit(code)


def to_seconds(duration):
    """Converts time string to second, where string is of form,
       3h, 5m, 20s etc

    Args:
       duration: str with numeric value suffixed with h, s, or m

    Returns:
        int: Seconds represented by the duration

    Raises:
        ValueError, KeyError if the string cannot be parsed.
    """

    try:
        units = {"s": 1, "m": 60, "h": 3600}
        return int(duration[:-1]) * units[duration[-1]]
    except KeyError:
        raise KeyError('Unit invalid or not informed (must be \'s\', \'h\' or \'m\')')
    except (ValueError, NameError):
        raise ValueError('The value informed is in the wrong format')


def get_logger(cfg, customer):
    """Configures and returns a logger object

    Args:
       cfg: Object holding ini file configuration, including logging config
       customer: Name of customer to prepend log file name with

    Returns:
        log: Log object

    Raises: AttributeError, ConfigParser.NoOptionError,
            ConfigParser.NoSectionError
    """
    log = logging.getLogger(SCRIPT_NAME)

    log_fmt = cfg.get("logging.format", raw=True)
    log_date = cfg.get("logging.datefmt", raw=True)
    log_file = cfg.get("logging.log_file")
    log_dir = os.path.dirname(log_file)
    log_file = os.path.basename(log_file)
    log_file = log_dir + '/' + customer + '_' + log_file

    log_level = getattr(logging, cfg.get("logging.level").upper(), None)

    logging.basicConfig(level=log_level,
                        format=log_fmt,
                        datefmt=log_date,
                        filename=log_file)

    return log


def post_http(url, data, log):
    """Post HTTP request.

    Args:
        url (str): URL to POST
        data (str): Data to POST
        log (Logger): Instance of Logger class

    Returns:
        dict: JSON response data

    Raises:
        ValueError, RequestException
    """
    log.info('POST request: %s', url)
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}

    try:
        result = requests.post(url, data=data, headers=headers)
        result.raise_for_status()
    except (ValueError, RequestException,
            requests.exceptions.RequestException) as err:
        log.error("Failed to post http request: %s" % err)
        return {}
    try:
        return result.json()
    except ValueError:
        return {}


def get_http_request(url, log):
    """Get HTTP request.

    Args:
        url (str): URL to GET
        log (Logger): Instance of Logger class

    Returns:
        list: of dicts representing JSON response data

    Raises:
        Nothing
    """
    log.info('GET request: %s', url)
    try:
        result = requests.get(url)
        result.raise_for_status()
    except (ValueError, RequestException,
            requests.exceptions.RequestException) as err:
        log.error("Failed to get http request: %s" % err)
        return []

    try:
        return result.json()
    except ValueError as err:
        log.error("Could not decode response: %s" % err)
        return []


def cmd(command, is_logging=True):
    """Runs subprocess and returns exit code, stdout & stderr

    Args:
       command: Command and its arguments to run
       is_logging: if it should log or not the command

    Returns:
        tuple: return code (int), stdout (str), stderr (str)

    Raises: Nothing
    """
    LOG.info("Running command: " + command)

    try:
        process = subprocess.Popen(command,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        LOG.info("Return code: " + str(process.returncode))

    except Exception:
        LOG.error("Failed to run %s" % command)
        return 1

    if is_logging:
        if stdout:
            LOG.info("STDOUT: " + stdout)
        if stderr:
            LOG.info("STDERR: " + stderr)
    return process.returncode, stdout, stderr


class Cfg(object):
    """ Class to handle config file parameter reading
    """

    def __init__(self):
        self.conf = ConfigParser.SafeConfigParser()

    def read_config(self, config_file):
        """
        Create an object with configurations passed by within 'config_file'
        :param config_file: An .ini file with detailed configuration to be used in the script
        :return: self with the configuration items
        """
        self.conf.read(config_file)

    def get(self, key, raw=False):
        """
        Get a value from the items
        :param raw: True if is to be brought without any format
        :param key: 'key' is in format 'section.option' param for ConfigParser.
        :return: a boolean value from the configuration file
        """
        section, option = key.split('.', 1)
        return self.conf.get(section, option, raw)

    def get_int(self, key):
        """
        Get a int value from the items
        :param key: 'key' is in format 'section.option' param for ConfigParser.
        :return: a boolean value from the configuration file
        """
        section, option = key.split('.', 1)
        return self.conf.getint(section, option)

    def get_bool(self, key):
        """
        Get a boolean value from the items
        :param key: 'key' is in format 'section.option' param for ConfigParser.
        :return: a boolean value from the configuration file
        """
        section, option = key.split('.', 1)
        return self.conf.getboolean(section, option)
