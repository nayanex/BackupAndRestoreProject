##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# For the snake_case comments
# pylint: disable=C0103

"""
This module is for unit tests from the local_backup_handler.py script
"""

import unittest
import os
import logging
from backup.local_backup_handler import *
from backup.notification_handler import *
from backup.logger import CustomLogger
from backup.backup_settings import *
import getpass
from os import path
import shutil
import tempfile
import mock
import time
from backup import utils as utils

SCRIPT_PATH = os.path.dirname(__file__)
SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

MIN_BKP_LOCAL = 1
VALID_IP = '127.0.0.1'
INVALID_HOST = "2.3.4."
VALID_USERNAME = getpass.getuser()
BKP_TEMP_FOLDER = os.path.join(SCRIPT_PATH, "tmp")
BKP_PATH = os.path.join(SCRIPT_PATH, "mock")
BKP_FOLDER = "rpc_bkps"
CUSTOMERS = ("CUSTOMER0", "CUSTOMER1", "CUSTOMER2", "CUSTOMER3")
INVALID_CUSTOMER_LOCAL_DEPLOY_PATH = os.path.join(SCRIPT_PATH, "rpc_bkps/no_customer_deployment")
SUPPORT_INFO_EMAIL = "fo-enmaas@ericsson.com"
SUPPORT_INFO_SERVER = "https://172.31.2.5/v1/emailservice/send"
OFFSITE_CFG = OffsiteConfig(VALID_IP, VALID_USERNAME, BKP_PATH, BKP_FOLDER, BKP_TEMP_FOLDER)
TMP_CUSTOMER_LOCAL_PATH = os.path.join(BKP_TEMP_FOLDER, CUSTOMERS[0])
REMOTE_CUSTOMER_PATH = os.path.join(BKP_PATH, BKP_FOLDER, CUSTOMERS[0])
GPG_MANAGER = ("backup", "backup@root.com", "/home/username/.gnupg")
NUMBER_OF_PROCESS = 2
NUMBER_OF_THREADS = 5
LOGGER = CustomLogger(SCRIPT_FILE)
NOTIFICATION_HANDLER = NotificationHandler(SUPPORT_INFO_EMAIL, SUPPORT_INFO_SERVER, LOGGER)
INVALID_CUSTOMER_CFG = EnmConfig(CUSTOMERS[0], INVALID_CUSTOMER_LOCAL_DEPLOY_PATH)
INVALID_LOCAL_BKP_HANDLER = LocalBackupHandler(OFFSITE_CFG, INVALID_CUSTOMER_CFG, GPG_MANAGER,
                                               NUMBER_OF_PROCESS, NUMBER_OF_THREADS,
                                               NOTIFICATION_HANDLER, LOGGER)


def create_customers_enmaas_cfg(customers=[CUSTOMERS[0]]):
    """
    Create list of enmaas configuration for customers provided, if no list of customer is
    provided as parameter, by default enmaas configuration for customer 0 is created.
    :param customers: list of customers
    :return: list of enmaas configuration for customers provided
    """
    customers_enmaas_cfg = []
    for index, item in enumerate(customers):
        valid_local_customer_path = os.path.join(SCRIPT_PATH, "rpc_bkps/customer_deployment_" +
                                                 str(index))
        utils.create_path(valid_local_customer_path)
        customers_enmaas_cfg.append(EnmConfig(CUSTOMERS[index], valid_local_customer_path))
    customers_enmaas_cfg = customers_enmaas_cfg[0] if len(customers_enmaas_cfg) == 1 else \
        customers_enmaas_cfg
    return customers_enmaas_cfg


def create_list_of_local_bkp_handler_objects(customer_enmaas_cfg_list=[]):
    """
    Create a list of local backup handlers for customers enmaas configuration provided, if no
    configuration is provided, by default EnmConfig and LocalBackuphandler objects are created for
    customer 0.
    :param customer_enmaas_cfg_list: list of enmaas configuration for determined customers
    :return: list of LocalBackuphandler objects
    """
    local_bkp_handler_list = []
    if not customer_enmaas_cfg_list:
        valid_local_customer_path = os.path.join(SCRIPT_PATH, "rpc_bkps/customer_deployment_0")
        utils.create_path(valid_local_customer_path)
        customer_enmaas_cfg_list.append(EnmConfig(CUSTOMERS[0], valid_local_customer_path))
    for customer_enmaas_cfg in customer_enmaas_cfg_list:
        local_bkp_handler = LocalBackupHandler(OFFSITE_CFG, customer_enmaas_cfg, GPG_MANAGER,
                                               NUMBER_OF_PROCESS, NUMBER_OF_THREADS,
                                               NOTIFICATION_HANDLER, LOGGER)
        local_bkp_handler_list.append(local_bkp_handler)
    local_bkp_handler_list = local_bkp_handler_list[0] if len(local_bkp_handler_list) == 1 else \
        local_bkp_handler_list
    return local_bkp_handler_list


def create_bkp_folders(bkp_list, backup_path, alternate_flag_ok=False):
    """
    create backup folders for determined customer
    :param bkp_list:
    :param backup_path:
    :param alternate_flag_ok:
    :return:
    """
    bkp_path_list_customer = []
    for bkp_folder in bkp_list:
        customer_bkp_path = os.path.join(backup_path, bkp_folder)
        bkp_path_list_customer.append(customer_bkp_path)
        utils.create_path(customer_bkp_path)
        if (is_bkp_folder_date_even(bkp_folder) and alternate_flag_ok) or not alternate_flag_ok:
            bkp_path_list_customer.append(customer_bkp_path)
            open(os.path.join(customer_bkp_path, "BACKUP_OK"), 'w').close()
    return order_backups_from_newest_to_oldest(bkp_path_list_customer)


def is_bkp_folder_date_even(bkp_folder):
    """
    asdfsdfasdfasdf
    :param bkp_folder:
    :return:
    """
    return int(bkp_folder.split('-').pop()) % 2 == 0


def order_backups_from_newest_to_oldest(bkp_path_list_customer):
    """
    adfasdfasdf
    :param bkp_path_list_customer:
    :return: list of backup ordered by date they were last modified
    """
    ordered_bkp_list = []
    bkp_path_list_customer.sort(key=lambda x: os.path.getmtime(x))
    bkp_path_list_customer.reverse()
    for bkp_path in bkp_path_list_customer:
        ordered_bkp_list.append(bkp_path.split('/').pop())
    return ordered_bkp_list


class LocalBackupHandlerInitTestCase(unittest.TestCase):
    """
    Test Cases for initialization of LocalBackupHandler object
    """
    def setUp(self):
        """
        Create testing scenario
        """
        self.customer0_enmaas_cfg = create_customers_enmaas_cfg()
        self.local_bkp_handler = create_list_of_local_bkp_handler_objects()

    def test_init_proper_arguments(self):
        """
        Test if constructor for LocalBackupHandler initializes properly
        """
        self.assertEquals(self.local_bkp_handler.offsite_config, OFFSITE_CFG)
        self.assertEquals(self.local_bkp_handler.gpg_manager, GPG_MANAGER)
        self.assertIsInstance(self.local_bkp_handler.logger, CustomLogger)
        self.assertEquals(self.local_bkp_handler.notification_handler, NOTIFICATION_HANDLER)
        self.assertEquals(self.local_bkp_handler.number_process, NUMBER_OF_PROCESS)
        self.assertEquals(self.local_bkp_handler.number_threads, NUMBER_OF_THREADS)
        self.assertEquals(self.local_bkp_handler.customer_conf.name, self.customer0_enmaas_cfg.name)
        self.assertEquals(self.local_bkp_handler.customer_conf.backup_path,
                          self.customer0_enmaas_cfg.backup_path)
        self.assertEquals(self.local_bkp_handler.remote_root_path, REMOTE_CUSTOMER_PATH)
        self.assertEquals(self.local_bkp_handler.temp_customer_root_path, TMP_CUSTOMER_LOCAL_PATH)

    def test_init_no_args(self):
        """
        Test that exception is raised when constructor of LocalBackupHandler is called with
        improper arguments
        """
        with self.assertRaises(TypeError):
            LocalBackupHandler()


class LocalBackupHandlerGetLocalBackupListTestCase(unittest.TestCase):
    """
    Test Cases for initialization of LocalBackupHandler object
    """
    def setUp(self):
        """
        Create mock Rackspace folder structure for certain customers
        """
        self.ordered_bkp_list_ctm1 = []
        self.ordered_bkp_list_ctm3 = []

        self.customers_enmaas_cfg = create_customers_enmaas_cfg(CUSTOMERS)
        self.local_bkp_handler_list = create_list_of_local_bkp_handler_objects(self.customers_enmaas_cfg)
        self.bkp_list = ['2018-10-06', '2018-10-05', '2018-10-07', '2018-10-04']

        self.ordered_bkp_list_ctm1 = create_bkp_folders(self.bkp_list,
                                                        self.customers_enmaas_cfg[1].backup_path)

        self.ordered_bkp_list_ctm2 = create_bkp_folders([self.bkp_list[0]],
                                                        self.customers_enmaas_cfg[2].backup_path)

        self.ordered_bkp_list_ctm3 = create_bkp_folders(self.bkp_list,
                                                        self.customers_enmaas_cfg[3].backup_path)

    def test_get_local_backup_list_no_backup_folders_available(self):
        """
        Tests that an empty list is returned when there is none backup folder available
        """
        valid_dir_list = self.local_bkp_handler_list[0].get_local_backup_list()
        self.assertFalse(valid_dir_list)

    def test_get_local_backup_invalid_customer_src_dir(self):
        """
        Test that None is returned when invalid customer source directory is provided for backup
        operation
        """
        valid_dir_list = INVALID_LOCAL_BKP_HANDLER.get_local_backup_list()
        self.assertIsNone(valid_dir_list)

    def test_get_local_backup_list_MIN_BKP_LOCAL_less_then_valid_bkp_list_len(self):
        """
        Test that the_oldest backups are being returned according to the MIN_BACKUP LOCAL
        """
        self.ordered_bkp_list_ctm1 = self.ordered_bkp_list_ctm1[MIN_BKP_LOCAL:]
        valid_dir_list = self.local_bkp_handler_list[1].get_local_backup_list()
        self.assertTrue(set(self.ordered_bkp_list_ctm1).issubset(valid_dir_list))
        self.assertTrue(len(valid_dir_list), 3)

    def test_get_local_backup_list_MIN_BKP_LOCAL_equals_valid_backup_list_length(self):
        """
        Test that even if only one backup folder is available it is going to be backed up.
        """
        valid_dir_list = self.local_bkp_handler_list[2].get_local_backup_list()
        self.assertEquals(['2018-10-06'], valid_dir_list)
        self.assertTrue(len(valid_dir_list), 1)

    def test_get_local_backup_list_return_only_backups_with_successful_flags(self):
        """
        Tests that only backups with the success flag are returned
        """
        self.ordered_bkp_list_ctm3 = self.ordered_bkp_list_ctm3[MIN_BKP_LOCAL:]
        valid_dir_list = self.local_bkp_handler_list[3].get_local_backup_list()
        self.assertTrue(len(valid_dir_list), 1)
        self.assertEquals(self.ordered_bkp_list_ctm3, valid_dir_list)

#get_backup_output_errors
#clean_local_backup

