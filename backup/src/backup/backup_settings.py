import os
import ConfigParser

from utils import get_home_dir
from logger import CustomLogger
from gnupg_manager import GnupgManager
from notification_handler import NotificationHandler

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

SYSTEM_CONFIG_FILE_ROOT_PATH = os.path.join(get_home_dir(), "backup", "config")
DEFAULT_CONFIG_FILE_ROOT_PATH = os.path.join(os.path.dirname(__file__), 'config')


class SupportInfo:
    """Class used to store sourced information about the support contact."""

    def __init__(self, email, server):
        """
        Initialize Support Info object.

        :param email: support email info.
        :param server: email server.
        """
        self.email = email
        self.server = server

    def __str__(self):
        """Represent Support Info object as string."""
        return "({}, {})".format(self.email, self.server)

    def __repr__(self):
        """Represent Support Info object."""
        return self.__str__()


class OffsiteConfig:
    """Class used to store sourced information about the off-site backup location."""

    def __init__(self, ip, user, path, folder, temp_path, name="AZURE"):
        """
        Initialize Offsite Config object.

        :param ip: ip of the server.
        :param user: user allowed to access the server.
        :param path: path in which the backup folder will be placed.
        :param folder: backup folder's name.
        :param temp_path: temporary folder to store files during the backup process.
        :param name: name of offsite location.
        """
        self.name = name
        self.ip = ip
        self.user = user
        self.path = path
        self.folder = folder
        self.full_path = os.path.join(path, folder)
        self.host = user + '@' + ip
        self.temp_path = temp_path

    def __str__(self):
        """Represent Offsite Config object as string."""
        return "({}, {}, {}, {})".format(self.ip, self.user, self.full_path, self.temp_path)

    def __repr__(self):
        """Represent Offsite Config object."""
        return self.__str__()


class EnmConfig:
    """Class used to store sourced information about the backup location of a customer."""

    def __init__(self, name, path):
        """
        Initialize ENM Config object.

        :param name: deployment name from the configuration section.
        :param path: backup path.
        """
        self.name = name
        self.backup_path = path

    def __str__(self):
        """Represent EnmConfig object as string."""
        return "({}, {})".format(self.name, self.backup_path)

    def __repr__(self):
        """Represent EnmConfig object."""
        return self.__str__()


class ScriptSettings:
    """
    Class used to store and validate data from the configuration file.

    Configuration file will be checked first in $USER_HOME/backup/config/config.cfg and then at
    the directory "config" in the same level as the script.
    """

    def __init__(self, config_file_name, logger):
        """
        Initialize Script Settings object.

        :param config_file_name: name of the configuration file.
        :param logger: logger object.
        """
        self.config_file_name = config_file_name

        config_root_path = SYSTEM_CONFIG_FILE_ROOT_PATH
        if not os.access(config_root_path, os.R_OK):
            config_root_path = DEFAULT_CONFIG_FILE_ROOT_PATH

        self.config_file_path = os.path.join(config_root_path, config_file_name)

        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

    def get_config_objects_from_file(self, validation_error_list=[]):
        """
        Reads, validates the configuration file and create the main objects used by the system.

        Errors that occur during this process are appended to the validation error list.

        :return: a dictionary with the following objects: notification handler, gnupg manager,
         offsite configuration, customer configuration dictionary, if success; an empty dictionary,
         otherwise.
        """
        if not os.access(self.config_file_path, os.R_OK):
            validation_error_list.append("Configuration file is not accessible '{}'".format(
                self.config_file_path))
            return {}

        config = ConfigParser.ConfigParser()
        config.readfp(open(self.config_file_path))

        self.logger.info("Reading configuration file '%s'.", self.config_file_path)

        config_object_factory_list = [self.get_notification_handler, self.get_gnupg_manager,
                                      self.get_offsite_config, self.get_enmaas_config_dic]

        config_object_dic = {}
        for object_factory in config_object_factory_list:
            try:
                config_object_dic[object_factory.__name__] = object_factory(config)
            except Exception as e:
                validation_error_list.append(e[0])

        if validation_error_list:
            return {}

        return config_object_dic

    def get_notification_handler(self, config):
        """
        Read the support contact information from the config file.

        1. EMAIL_TO: email address of the support team.
        2. EMAIL_URL: email server url.

        If an error occurs, an Exception is raised with the details of the problem.

        :param config: configuration object.

        :return the notification handler with the informed data.
        """
        if not config.has_option('SUPPORT_CONTACT', 'EMAIL_TO'):
            raise Exception("Error reading the configuration file '{}'. Variable '{}' "
                            "is not set in section {}.".format(self.config_file_name,
                                                               'EMAIL_TO', 'SUPPORT_CONTACT'))

        if not config.has_option('SUPPORT_CONTACT', 'EMAIL_URL'):
            raise Exception("Error reading the configuration file '{}'. Variable '{}' "
                            "is not set in section {}.".format(self.config_file_name,
                                                               'EMAIL_URL', 'SUPPORT_CONTACT'))

        support_info = SupportInfo(str(config.get('SUPPORT_CONTACT', 'EMAIL_TO')),
                                   str(config.get('SUPPORT_CONTACT', 'EMAIL_URL')))

        self.logger.info("The following support information was defined: %s.", support_info)

        return NotificationHandler(support_info.email, support_info.server, self.logger)

    def get_gnupg_manager(self, config):
        """
        Read the GPG information from the config file.

        1. GPG_USER_NAME:  gpg configured user name.
        2. GPG_USER_EMAIL: gpg configured email.

        If one of these information is missing in the configuration file,
        an INVALID_INPUT error is raised.

        Configure the GnupgManager according to the provided settings and platform.
        If an error occurs, an Exception is raised with the details of the problem.

        :param config: configuration object.

        :return an object with the gnupg information.
        """
        if not config.has_option('GNUPG', 'GPG_USER_NAME'):
            raise Exception("Error reading the configuration file '{}'. Variable '{}' is not set in"
                            " section {}.".format(self.config_file_name, 'GPG_USER_NAME', 'GNUPG'))

        if not config.has_option('GNUPG', 'GPG_USER_EMAIL'):
            raise Exception("Error reading the configuration file '{}'. Variable '{}' is not set in"
                            " section {}.".format(self.config_file_name, 'GPG_USER_EMAIL', 'GNUPG'))

        try:
            gpg_manager = GnupgManager(str(config.get('GNUPG', 'GPG_USER_NAME')),
                                       str(config.get('GNUPG', 'GPG_USER_EMAIL')),
                                       self.logger)
        except Exception as e:
            raise Exception(e[0])

        self.logger.info("The following gnupg information was defined: %s.", gpg_manager)

        return gpg_manager

    def get_offsite_config(self, config):
        """
        Read the cloud connection details, as well as the backup path.

        1. IP: ip address.
        2. USER: server user.
        3. BKP_PATH: main path where the backup content will be placed.
        4. BKP_DIR: folder where the customer's backup will be transferred.

        If an error occurs, an Exception is raised with the details of the problem.

        :param config: configuration object.

        :return an object with the offsite information.
        """
        if not config.has_option('OFFSITE_CONN', 'IP'):
            raise Exception(
                "Error reading the configuration file '{}'. Variable '{}'"
                " is not set in section '{}'.".format(self.config_file_name, 'IP', 'OFFSITE_CONN'))

        if not config.has_option('OFFSITE_CONN', 'USER'):
            raise Exception(
                "Error reading the configuration file '{}'. Variable '{}' "
                "is not set in section '{}'.".format(self.config_file_name, 'USER', 'OFFSITE_CONN'))

        if not config.has_option('OFFSITE_CONN', 'BKP_PATH'):
            raise Exception(
                "Error reading the configuration file '{}'. Variable '{}' "
                "is not set in section '{}'.".format(self.config_file_name,
                                                     'BKP_PATH', 'OFFSITE_CONN'))

        if not config.has_option('OFFSITE_CONN', 'BKP_DIR'):
            raise Exception(
                "Error reading the configuration file '{}'. Variable '{}' "
                "is not set in section '{}'.".format(self.config_file_name,
                                                     'BKP_DIR', 'OFFSITE_CONN'))

        if not config.has_option('OFFSITE_CONN', 'BKP_TEMP_FOLDER'):
            raise Exception(
                "Error reading the configuration file '{}'. Variable '{}' "
                "is not set in section '{}'.".format(self.config_file_name,
                                                     'BKP_TEMP_FOLDER', 'OFFSITE_CONN'))

        offsite_config = OffsiteConfig(config.get('OFFSITE_CONN', 'IP'),
                                       config.get('OFFSITE_CONN', 'USER'),
                                       config.get('OFFSITE_CONN', 'BKP_PATH'),
                                       config.get('OFFSITE_CONN', 'BKP_DIR'),
                                       config.get('OFFSITE_CONN', 'BKP_TEMP_FOLDER'))

        self.logger.info("The following off-site information was defined: %s.", offsite_config)

        return offsite_config

    def get_enmaas_config_dic(self, config):
        """
        Read customer's deployment details.

        CUSTOMER_PATH: path to the customer's backups.
        If an error occurs, an Exception is raised with the details of the problem.

        :param config: configuration object.

        :return dictionary with the information of all customers in the configuration file.
        """
        config.remove_section('SUPPORT_CONTACT')
        config.remove_section('GNUPG')
        config.remove_section('OFFSITE_CONN')

        sections = config.sections()

        self.logger.info("The following deployments were defined: %s.", sections)

        enmaas_config_dic = {}

        for section in sections:
            if not config.has_option(section, 'CUSTOMER_PATH'):
                raise Exception("Error reading the configuration file '{}'. Variable '{}' "
                                "is not set for customer '{}'.".format(self.config_file_name,
                                                                       'CUSTOMER_PATH', section))

            enmaas_config_dic[section] = EnmConfig(section, config.get(section, "CUSTOMER_PATH"))

        return enmaas_config_dic
