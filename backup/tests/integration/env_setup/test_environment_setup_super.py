##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import logging
import os
from unittest import TestCase

from create_local_mock_environment import create_mock_env, CUSTOMER_NAME

from backup.backup_settings import EnmConfig, OffsiteConfig
from backup.gnupg_manager import GnupgManager
from backup.local_backup_handler import LocalBackupHandler
from backup.logger import CustomLogger
from backup.notification_handler import NotificationHandler
from backup.offsite_backup_handler import OffsiteBackupHandler
from backup.utils import create_path, create_remote_dir, get_current_user, \
    remove_path, remove_remote_dir

logging.disable(logging.CRITICAL)

LOCALHOST = '127.0.0.1'
LOCAL_USER = get_current_user()
HOST = "{}@{}".format(LOCAL_USER, LOCALHOST)

SCRIPT_PATH = os.path.dirname(__file__)
TEST_RPC_BKP_FOLDER = 'rpc_bkp_test'
TEST_LOCAL_BACKUP_PATH = os.path.join(SCRIPT_PATH, TEST_RPC_BKP_FOLDER)
TEST_REMOTE_BACKUP_PATH = os.path.join(SCRIPT_PATH, 'mock_azure')
TEST_REMOTE_RPC_FULL_PATH = os.path.join(TEST_REMOTE_BACKUP_PATH, TEST_RPC_BKP_FOLDER)
TEST_TEMP_PATH = os.path.join(SCRIPT_PATH, 'temp_path')
SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

NUMBER_BKP = 4
NUMBER_VOLUME = NUMBER_THREADS = 3
NUMBER_CUSTOMER = NUMBER_PROCESS = 2


class TestEnmaasBackupAutomation(TestCase):
    """
    Super class to handle the environment setup for the backup script unit tests.

    It will create the local and remote environments with the default specifications.

    In order to specify different settings, just override the setUpClass/tearDownClass methods.
    """

    def __init__(self, *args, **kwargs):
        super(TestEnmaasBackupAutomation, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.number_bkp = NUMBER_BKP
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()
        cls.create_remote_environment()

    @classmethod
    def tearDownClass(cls):
        cls.remove_local_environment()
        cls.remove_remote_environment()
        cls.remove_test_objects()

    @classmethod
    def create_local_environment(cls):
        create_path(TEST_LOCAL_BACKUP_PATH)
        create_mock_env(TEST_LOCAL_BACKUP_PATH, cls.number_customer,
                        cls.number_bkp, cls.number_volume)

        cls.bkp_map = {}
        for customer in cls.enmaas_config_dic.values():
            cls.bkp_map[customer.name] = {}

            for bkp_dir in os.listdir(customer.backup_path):
                bkp_path = os.path.join(customer.backup_path, bkp_dir)
                cls.bkp_map[customer.name][bkp_path] = []

                for volume in os.listdir(bkp_path):
                    volume_path = os.path.join(bkp_path, volume)
                    if os.path.isdir(volume_path):
                        cls.bkp_map[customer.name][bkp_path].append(volume_path)

    @staticmethod
    def remove_local_environment():
        remove_path(TEST_LOCAL_BACKUP_PATH)

    @classmethod
    def create_remote_environment(cls):
        create_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)
        create_remote_dir(HOST, TEST_REMOTE_RPC_FULL_PATH)
        create_path(TEST_TEMP_PATH)

        for customer in cls.enmaas_config_dic.values():
            bkp_manager = LocalBackupHandler(cls.offsite_config,
                                             customer,
                                             cls.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             cls.notification_manager,
                                             cls.logger)

            bkp_manager.process_backup_list()

        remove_path(TEST_TEMP_PATH)

    @staticmethod
    def remove_remote_environment():
        remove_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)

    @classmethod
    def create_test_objects(cls):
        cls.enmaas_config_dic = {}
        for i in range(0, cls.number_customer):
            customer_name = "CUSTOMER_{}".format(i)
            customer_folder = '{}{}'.format(CUSTOMER_NAME, i)
            cls.enmaas_config_dic[customer_name] = EnmConfig(customer_name,
                                                             os.path.join(TEST_LOCAL_BACKUP_PATH,
                                                                          customer_folder))

        cls.offsite_config = OffsiteConfig(LOCALHOST,
                                           LOCAL_USER,
                                           TEST_REMOTE_BACKUP_PATH,
                                           TEST_RPC_BKP_FOLDER,
                                           TEST_TEMP_PATH)

        cls.logger = CustomLogger(SCRIPT_FILE, "")
        cls.notification_manager = NotificationHandler("test", "test", cls.logger)
        cls.gpg_manager = GnupgManager('backup', 'backup@root.com', cls.logger)

        cls.bkp_tools = OffsiteBackupHandler(cls.gpg_manager,
                                             cls.offsite_config,
                                             cls.enmaas_config_dic,
                                             cls.number_threads,
                                             cls.number_process,
                                             cls.notification_manager,
                                             cls.logger)

    @classmethod
    def remove_test_objects(cls):
        for enmaas_config in cls.enmaas_config_dic.values():
            del enmaas_config

        cls.enmaas_config_dic.clear()

        del cls.offsite_config
        del cls.bkp_tools
