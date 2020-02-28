##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import os
import unittest

from backup.local_backup_handler import LocalBackupHandler
from backup.utils import check_remote_path_exists, remove_remote_dir
from env_setup.test_environment_setup_super import create_path, create_remote_dir, HOST, \
    NUMBER_CUSTOMER, NUMBER_PROCESS, NUMBER_THREADS, NUMBER_VOLUME, remove_path, \
    TEST_REMOTE_BACKUP_PATH, TEST_REMOTE_RPC_FULL_PATH, TEST_TEMP_PATH, TestEnmaasBackupAutomation


class TestEnmaasBackupAutomationRemoteCleanupSixBackups(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 6
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()
        cls.create_remote_environment()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_clean_offsite_backup_three_backups(self):
        ret, out_msg, bkp_cleaned_list = self.bkp_tools.clean_offsite_backup()

        self.assertTrue(ret, "Failed to perform off-site clean up: {}".format(out_msg))

        to_be_deleted = 2 * self.number_customer
        self.assertIs(len(bkp_cleaned_list), to_be_deleted,
                      "Number of deleted backups {} is different from expected {}.".
                      format(len(bkp_cleaned_list), to_be_deleted))


class TestEnmaasBackupAutomationRemoteCleanupFiveBackups(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 5
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()
        cls.create_remote_environment()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_clean_offsite_backup_four_backups(self):
        ret, out_msg, bkp_cleaned_list = self.bkp_tools.clean_offsite_backup()

        self.assertTrue(ret, "Failed to perform off-site clean up: {}".format(out_msg))

        to_be_deleted = 1 * self.number_customer
        self.assertIs(len(bkp_cleaned_list), self.number_customer,
                      "Number of deleted backups {} is different from expected {}."
                      .format(len(bkp_cleaned_list), to_be_deleted))


class TestEnmaasBackupAutomationRemoteCleanupFourBackups(TestEnmaasBackupAutomation):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_clean_offsite_backup_three_backups(self):
        ret, out_msg, bkp_cleaned_list = self.bkp_tools.clean_offsite_backup()

        self.assertTrue(ret, "Failed to perform off-site clean up: {}".format(out_msg))

        to_be_deleted = 0 * self.number_customer
        self.assertIs(len(bkp_cleaned_list), 0,
                      "Number of deleted backups {} is different from expected {}."
                      .format(len(bkp_cleaned_list), to_be_deleted))


class TestEnmaasBackupAutomationRemoteCleanupZeroBackups(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 0
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_clean_offsite_backup_zero_backups(self):
        ret, out_msg, bkp_cleaned_list = self.bkp_tools.clean_offsite_backup()

        self.assertTrue(ret, "Should have returned True with no backups to delete. Returned '{}' "
                             "instead".format(out_msg))

        to_be_deleted = 0
        self.assertIs(len(bkp_cleaned_list), to_be_deleted,
                      "Number of deleted backups {} is different from expected {}."
                      .format(len(bkp_cleaned_list), to_be_deleted))


class TestEnmaasBackupAutomationBackupList(TestEnmaasBackupAutomation):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_offsite_backup_list_per_customer(self):
        for customer in self.enmaas_config_dic.values():
            bkp_list = self.bkp_tools.get_offsite_backup_dic(customer)
            self.assertIsNotNone(bkp_list,
                                 "Failed to retrieve the remote backup list for customer {}."
                                 .format(customer.name))

            retrieved_bkp = len(bkp_list[customer.name])

            self.assertIs(retrieved_bkp,
                          self.number_bkp - 1,
                          "Number of retrieved backups {} is different from {} for customer {}."
                          .format(retrieved_bkp, self.number_bkp - 1, customer.name))

    def test_get_offsite_backup_list_all(self):
        bkp_list = self.bkp_tools.get_offsite_backup_dic()

        self.assertIsNot(bkp_list, None,
                         "Should have returned a dictionary with the backup list per customer.")

        number_customer = len(bkp_list.keys())
        self.assertIs(number_customer, self.number_customer, "Expected {} entries, got {}."
                      .format(self.number_customer, number_customer))

        for enmaas_conf in self.enmaas_config_dic.values():
            if enmaas_conf.name not in bkp_list.keys():
                self.fail("Backup list for customer {} is missing in the returned list."
                          .format(enmaas_conf.name))


class TestEnmaasBackupAutomationEmptyBackupList(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 0
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_offsite_backup_list_per_customer(self):
        for customer in self.enmaas_config_dic.values():
            bkp_list = self.bkp_tools.get_offsite_backup_dic(customer)
            self.assertIs(1, len(bkp_list.keys()), "Should have returned 1 key.")
            self.assertIs(0, len(bkp_list[customer.name]), "Should have returned 0 backups.")

    def test_get_offsite_backup_list_all(self):
        bkp_dic = self.bkp_tools.get_offsite_backup_dic()
        for backup_list in bkp_dic.values():
            self.assertIs(0, len(backup_list), "Should have returned 0 backups.")


class TestEnmaasBackupAutomationRestore(TestEnmaasBackupAutomation):
    def setUp(self):
        self.temp_restore_path = os.path.join('./', 'aux_restore')
        create_path(self.temp_restore_path)

    def tearDown(self):
        remove_path(self.temp_restore_path)

    def test_execute_restore_backup_from_offsite_with_valid_backup_tag(self):
        single_bkp_per_customer = {}

        for customer in self.bkp_map.keys():
            single_bkp_per_customer[customer] = sorted(self.bkp_map[customer].keys())[0]

        for customer_key in single_bkp_per_customer.keys():
            bkp_tag = os.path.basename(single_bkp_per_customer[customer_key])
            ret, _ = self.bkp_tools.execute_restore_backup_from_offsite(customer_key, bkp_tag,
                                                                        self.temp_restore_path)

            self.assertTrue(ret, "Backup {} not finished successfully for customer {}."
                            .format(bkp_tag, customer_key))

            self.assertTrue(os.path.exists(os.path.join(self.temp_restore_path, customer_key,
                                                        bkp_tag)),
                            "Backup not restored {} for customer {}.".format(bkp_tag, customer_key))
            remove_path(self.temp_restore_path)

    def test_execute_restore_backup_from_offsite_with_invalid_backup_tag(self):
        backup_tag = "INVALID"
        for customer_key in self.bkp_map.keys():
            ret, out = self.bkp_tools.execute_restore_backup_from_offsite(customer_key, backup_tag,
                                                                          self.temp_restore_path)

            self.assertFalse(ret, "Should not have found a backup with this name {} "
                                  "for customer {}.".format(backup_tag, customer_key))

            self.assertTrue("not found".lower() in out.lower(),
                            "Should have returned a backup tag not found message instead of '{}'."
                            .format(out))

    def test_execute_restore_backup_from_offsite_with_valid_customer_tag(self):
        for customer_key in self.bkp_map.keys():
            ret, out = self.bkp_tools.execute_restore_backup_from_offsite(customer_key, "",
                                                                          self.temp_restore_path)

            self.assertTrue(ret, "Operation did not finish successfully for customer {}."
                            .format(customer_key))

            self.assertTrue("Returned list of all backups per customer successfully.".lower() in
                            out.lower(), "Operation did not retrieve the list of backups per "
                                         "customer {}.".format(customer_key))

    def test_execute_restore_backup_from_offsite_invalid_customer_tag(self):
        customer_key = "INVALID"

        ret, out = self.bkp_tools.execute_restore_backup_from_offsite(customer_key, "",
                                                                      self.temp_restore_path)

        self.assertFalse(ret, "Should not have found a customer with this name {}."
                         .format(customer_key))

        self.assertTrue("not found".lower() in out.lower(),
                        "Should have returned a customer not found message instead of '{}'."
                        .format(out))

    def test_download_backup_from_offsite(self):
        single_bkp_per_customer = {}

        for customer in self.bkp_map.keys():
            single_bkp_per_customer[customer] = sorted(self.bkp_map[customer].keys())[0]

        for customer_key in single_bkp_per_customer.keys():
            bkp_name = os.path.basename(single_bkp_per_customer[customer_key])
            remote_bkp_path = os.path.join(self.offsite_config.full_path, customer_key, bkp_name)

            restored_backup_path = os.path.join(self.temp_restore_path, bkp_name)

            self.assertTrue(self.bkp_tools.download_backup_from_offsite(customer_key,
                                                                        bkp_name,
                                                                        remote_bkp_path,
                                                                        self.temp_restore_path,
                                                                        restored_backup_path),
                            "Failed to download and process backup '{}' from offsite."
                            .format(remote_bkp_path))

            if not os.path.exists(os.path.join(self.temp_restore_path, bkp_name)):
                self.fail("Failed to download and process backup '{}' from offsite."
                          .format(remote_bkp_path))

            remove_path(self.temp_restore_path)


class TestEnmaasBackupAutomationExecuteBackup(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 4
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_execute_backup_to_offsite_with_cleanup(self):
        create_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)
        create_remote_dir(HOST, TEST_REMOTE_RPC_FULL_PATH)

        self.bkp_tools.execute_backup_to_offsite("", True)

        self.assertTrue(check_remote_path_exists(HOST, TEST_REMOTE_RPC_FULL_PATH),
                        "Remote path '{}' was not created correctly."
                        .format(TEST_REMOTE_RPC_FULL_PATH))

        # Get off-site backups to confirm the numbers are correct.
        offsite_bkp_list = self.bkp_tools.get_offsite_backup_dic()
        self.assertIsNotNone(offsite_bkp_list, "Failed to retrieve the remote backup list.")

        # Check the number of customers are correct on off-site after the backup.
        number_customers = len(offsite_bkp_list.keys())
        self.assertIs(number_customers, self.number_customer,
                      "Invalid number of customers on off-site. Expected {}, got {}."
                      .format(self.number_customer, number_customers))

        # Check the number of backups on off-site per customer.
        for customer in offsite_bkp_list.keys():
            retrieved_bkp = len(offsite_bkp_list[customer])

            self.assertIs(retrieved_bkp,
                          self.number_bkp - 1,
                          "Number of retrieved backups {} is different from {} for customer {}."
                          .format(retrieved_bkp, self.number_bkp - 1, customer))
        # Check that no backup was cleaned.
        for customer in self.enmaas_config_dic.values():
            local_bkp_list = LocalBackupHandler(self.offsite_config,
                                                customer,
                                                self.gpg_manager,
                                                NUMBER_PROCESS,
                                                NUMBER_THREADS,
                                                self.notification_manager,
                                                self.logger).get_local_backup_list()

            self.assertIsNotNone(local_bkp_list,
                                 "Failed to retrieve the local backup list from customer {}."
                                 .format(customer.name))
            self.assertIs(len(local_bkp_list),
                          self.number_bkp - 1,
                          "Number of retrieved backups {} is different from {} for customer {}."
                          .format(len(local_bkp_list), self.number_bkp - 1, customer.name))
        remove_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)

    def test_execute_backup_to_offsite_no_cleanup(self):
        create_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)
        create_remote_dir(HOST, TEST_REMOTE_RPC_FULL_PATH)

        self.bkp_tools.execute_backup_to_offsite()

        self.assertTrue(check_remote_path_exists(HOST, TEST_REMOTE_RPC_FULL_PATH),
                        "Remote path '{}' was not created correctly."
                        .format(TEST_REMOTE_RPC_FULL_PATH))

        # Get off-site backups to confirm the numbers are correct.
        remote_bkp_list = self.bkp_tools.get_offsite_backup_dic()
        self.assertIsNotNone(remote_bkp_list, "Failed to retrieve the remote backup list.")

        # Check the number of customers are correct on off-site after the backup.
        number_customers = len(remote_bkp_list.keys())
        self.assertIs(number_customers, self.number_customer,
                      "Invalid number of customers on off-site. Expected {}, got {}."
                      .format(self.number_customer, number_customers))

        # Check the number of backups on off-site per customer.
        for customer in remote_bkp_list.keys():
            retrieved_bkp = len(remote_bkp_list[customer])

            self.assertIs(retrieved_bkp,
                          self.number_bkp - 1,
                          "Number of retrieved backups {} is different from {} for customer {}."
                          .format(retrieved_bkp, self.number_bkp - 1, customer))

        # Check nothing was cleaned.
        for customer in self.enmaas_config_dic.values():
            local_bkp_list = LocalBackupHandler(self.offsite_config,
                                                customer,
                                                self.gpg_manager,
                                                NUMBER_PROCESS,
                                                NUMBER_THREADS,
                                                self.notification_manager,
                                                self.logger).get_local_backup_list()

            self.assertIsNotNone(local_bkp_list,
                                 "Failed to retrieve the local backup list for customer {}."
                                 .format(customer.name))
            self.assertIs(len(local_bkp_list),
                          self.number_bkp - 1,
                          "Number of retrieved backups {} is different from {} for customer {}."
                          .format(len(local_bkp_list), self.number_bkp - 1, customer.name))
        remove_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)


if __name__ == "__main__":
    TestEnmaasBackupAutomationRemoteCleanupSixBackups = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationRemoteCleanupSixBackups)
    TestEnmaasBackupAutomationRemoteCleanupFiveBackups = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationRemoteCleanupFiveBackups)
    TestEnmaasBackupAutomationRemoteCleanupFourBackups = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationRemoteCleanupFourBackups)
    TestEnmaasBackupAutomationRemoteCleanupZeroBackups = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationRemoteCleanupZeroBackups)
    TestEnmaasBackupAutomationBackupList = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationBackupList)
    TestEnmaasBackupAutomationEmptyBackupList = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationEmptyBackupList)
    TestEnmaasBackupAutomationRestore = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationRestore)
    TestEnmaasBackupAutomationExecuteBackup = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationExecuteBackup)

    suites = unittest.TestSuite([TestEnmaasBackupAutomationRemoteCleanupSixBackups,
                                 TestEnmaasBackupAutomationRemoteCleanupFiveBackups,
                                 TestEnmaasBackupAutomationRemoteCleanupFourBackups,
                                 TestEnmaasBackupAutomationRemoteCleanupZeroBackups,
                                 TestEnmaasBackupAutomationBackupList,
                                 TestEnmaasBackupAutomationEmptyBackupList,
                                 TestEnmaasBackupAutomationRestore,
                                 TestEnmaasBackupAutomationExecuteBackup])

    unittest.TextTestRunner(verbosity=2).run(suites)
