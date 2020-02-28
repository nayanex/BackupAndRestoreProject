#!/usr/bin/env python
##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################


import unittest
import mock
import os
from backup.notification_handler import NotificationHandler
from urllib2 import URLError


MOCK_PACKAGE = 'backup.notification_handler.'


class TestSendEmail(unittest.TestCase):
    """
    Class for testing send_mail function from backup.notification_handler.py script
    """
    @classmethod
    def setUpClass(cls):
        """
        Setup for the tests
        """
        cls.email_to = 'mock@email'
        cls.email_url = 'http://mock'
        cls.from_name = 'mock'
        cls.email_from = cls.from_name + '@ericsson.com'
        cls.subject = 'mock_subject'
        cls.message = 'mock_message'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_sending_log(self, mock_handler, mock_logger):
        """
        Test to check the log to notify about the attempt to send the email is generated:
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        mock_handler.return_value.code = 200
        calls = [mock.call("Sending email from {} to {} with subject '{}'.".format(
            self.email_from, self.email_to, self.subject))]
        handler.send_mail(self.from_name, self.subject, self.message)
        mock_logger.return_value.log_info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_successful_send_log(self, mock_handler, mock_logger):
        """
        Test to check the log if the email was sent successfully
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        mock_handler.return_value.code = 200
        calls = [mock.call("Email sent successfully to: '{}'.".format(self.email_to))]

        handler.send_mail(self.from_name, self.subject, self.message)
        mock_logger.return_value.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_successful_send_return_value(self, mock_handler, mock_logger):
        """
        Test to check the return value if the email was sent successfully:
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)
        mock_handler.return_value.code = 200

        self.assertTrue(handler.send_mail(self.from_name, self.subject, self.message))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    def test_send_email_empty_deployment_name_log(self, mock_logger):
        """
        Test to check the log if deployment name is not provided
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        calls = [mock.call("An empty sender was informed.")]

        handler.send_mail("", self.subject, self.message)
        mock_logger.return_value.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    def test_send_email_empty_deployment_name_return_value(self, mock_logger):
        """
        Test to check the return value if deployment name is not provided
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)
        self.assertFalse(handler.send_mail('', self.subject, self.message))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_bad_response(self, mock_handler, mock_logger):
        """
        Test to check the log if the email was not sent due to bad response
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        mock_handler.return_value.code = 300
        mock_handler.return_value.response_code = 404
        mock_handler.return_value.Exception = "Bad response: Code: {}, Response: {}".format(
            mock_handler.return_value.status_code, mock_handler.return_value)

        calls = [mock.call("Failed to send email to {} due to: {}".format(
            self.email_to, mock_handler.return_value.Exception))]

        handler.send_mail(self.from_name, self.subject, self.message)
        mock_logger.return_value.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_bad_response_return_value(self, mock_handler, mock_logger):
        """
        Test to check the return value if the email was not sent due to bad response
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        mock_handler.return_value.code = 300

        self.assertFalse(handler.send_mail(self.from_name, self.subject, self.message))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_url_error(self, mock_handler, mock_logger):
        """
        Test to check the log if the email_url is invalid
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        mock_handler.side_effect = URLError("reason")

        calls = [mock.call("Failed to send email to {} due to: {}".format(
            self.email_to, mock_handler.side_effect))]

        handler.send_mail(self.from_name, self.subject, self.message)
        mock_logger.return_value.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'urllib2.urlopen')
    def test_send_email_url_error_return_value(self, mock_handler, mock_logger):
        """
        Test to check the return value if the email_url is invalid
        """
        handler = NotificationHandler(self.email_to, self.email_url, mock_logger)

        mock_handler.side_effect = URLError("reason")

        self.assertFalse(handler.send_mail(self.from_name, self.subject, self.message))