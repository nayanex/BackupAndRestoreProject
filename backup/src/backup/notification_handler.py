import json
import os
import urllib2

from backup.logger import CustomLogger

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]
SEP1 = "-------------------------------------------------------------------------------------------"
SEP2 = "==========================================================================================="


class NotificationHandler:
    """Responsible for handling the BUR notification mails."""

    def __init__(self, email_to, email_url, logger):
        """
        Initialize Notification Handler object.

        :param email_to: where to send notification email.
        :param email_url: which email service to use.
        :param logger: which logger to use.

        :return true, if success;
                false, otherwise.
        """
        self.email_to = email_to
        self.email_url = email_url
        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

    def send_mail(self, deployment_name_as_from, subject, message):
        """
        Prepare and sends notification email whenever an error happens during BUR process.

        Read email service configuration attribute EMAIL_URL.

        Raise exceptions if an error happens.

        :param deployment_name_as_from: Deployment's name.
        :param subject: notification email subject.
        :param message: notification email message.
        """
        if not deployment_name_as_from.strip():
            self.logger.error("An empty sender was informed.")
            return False

        from_sender = "{}@ericsson.com".format(str(deployment_name_as_from).strip().lower())

        self.logger.log_info("Sending email from {} to {} with subject '{}'.".format(from_sender,
                                                                                     self.email_to,
                                                                                     subject))

        json_string = {"personalizations": [{"to": [{"email": self.email_to}], "subject": subject}],
                       "from": {"email": from_sender},
                       "content": [{"type": "text/plain", "value": message}]}

        post_data = json.dumps(json_string).encode("utf8")

        req = urllib2.Request(self.email_url, data=post_data,  # nosec
                              headers={'cache-control': 'no-cache',
                                       'content-type': 'application/json'})
        try:
            response = urllib2.urlopen(req, timeout=10)  # nosec
            if response.code != 200:
                raise Exception("Bad response: Code: {}, Response: {}".format(response.status_code,
                                                                              response))
        except urllib2.URLError as e:
            self.logger.error("Failed to send email to {} due to: {}".format(self.email_to, e))
            return False

        except Exception as e:
            self.logger.error("Failed to send email to {} due to: {}".format(self.email_to, e[0]))
            return False

        self.logger.info("Email sent successfully to: '{}'.".format(self.email_to))

        return True
