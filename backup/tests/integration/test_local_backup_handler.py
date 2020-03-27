import glob
import os
import unittest

from backup.utils import validate_metadata, METADATA_FILE_SUFFIX
from backup.local_backup_handler import LocalBackupHandler
from env_setup.test_environment_setup_super import create_path, create_remote_dir, HOST, \
    NUMBER_CUSTOMER, NUMBER_PROCESS, NUMBER_THREADS, NUMBER_VOLUME, remove_path, \
    TEST_REMOTE_BACKUP_PATH, TEST_REMOTE_RPC_FULL_PATH, TEST_TEMP_PATH, TestEnmaasBackupAutomation


class TestUploadTwoBackupsToOffsite(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 3
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = 3
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()

    def tearDown(self):
        remove_path(TEST_TEMP_PATH)

    def test_upload_backup_to_offsite(self):
        create_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)
        create_remote_dir(HOST, TEST_REMOTE_RPC_FULL_PATH)
        create_path(TEST_TEMP_PATH)

        for customer in self.enmaas_config_dic.values():
            bkp_handler = LocalBackupHandler(self.offsite_config,
                                             customer,
                                             self.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             self.notification_manager,
                                             self.logger)

            local_bkp_list = bkp_handler.get_local_backup_list()

            self.assertIsNotNone(local_bkp_list, "Error, backup_list for customer {} is null"
                                 .format(customer.name))

            expected_bkp_list_size = self.number_bkp - 1
            self.assertIs(expected_bkp_list_size,
                          len(local_bkp_list),
                          "Expected {} backups for customer {}. Got {}."
                          .format(expected_bkp_list_size, customer.name, len(local_bkp_list)))
            bkp_handler.process_backup_list()

            offsite_list = self.bkp_tools.get_offsite_backup_dic(customer)

            self.assertIsNotNone(offsite_list,
                                 "Offsite backup list should not be None for customer {}."
                                 .format(customer.name))

            self.assertIs(expected_bkp_list_size, len(offsite_list[customer.name]),
                          "Expected {} backups offsite for customer {}. Got {}."
                          .format(expected_bkp_list_size, customer.name, len(offsite_list)))


class TestUploadOneBackupToOffsite(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 2
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = 3
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()

    def tearDown(self):
        remove_path(TEST_TEMP_PATH)

    def test_upload_backup_to_offsite(self):
        create_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)
        create_remote_dir(HOST, TEST_REMOTE_RPC_FULL_PATH)
        create_path(TEST_TEMP_PATH)

        for customer in self.enmaas_config_dic.values():
            bkp_handler = LocalBackupHandler(self.offsite_config,
                                             customer,
                                             self.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             self.notification_manager,
                                             self.logger)

            local_bkp_list = bkp_handler.get_local_backup_list()

            self.assertIsNotNone(local_bkp_list, "Error, backup_list for customer {} is null"
                                 .format(customer.name))

            expected_bkp_list_size = self.number_bkp - 1
            self.assertIs(expected_bkp_list_size,
                          len(local_bkp_list),
                          "Expected {} backups for customer {}. Got {}."
                          .format(expected_bkp_list_size, customer.name, len(local_bkp_list)))
            bkp_handler.process_backup_list()

            offsite_list = self.bkp_tools.get_offsite_backup_dic(customer)

            self.assertIsNotNone(offsite_list,
                                 "Offsite backup list should not be None for customer {}."
                                 .format(customer.name))

            self.assertIs(expected_bkp_list_size, len(offsite_list[customer.name]),
                          "Expected {} backups offsite for customer {}. Got {}."
                          .format(expected_bkp_list_size, customer.name, len(offsite_list)))


class TestUploadZeroBackupToOffsite(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 0
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = 3
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()

    def tearDown(self):
        remove_path(TEST_TEMP_PATH)

    def test_upload_backup_to_offsite(self):
        create_remote_dir(HOST, TEST_REMOTE_BACKUP_PATH)
        create_remote_dir(HOST, TEST_REMOTE_RPC_FULL_PATH)
        create_path(TEST_TEMP_PATH)

        for customer in self.enmaas_config_dic.values():
            bkp_handler = LocalBackupHandler(self.offsite_config,
                                             customer,
                                             self.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             self.notification_manager,
                                             self.logger)

            local_bkp_list = bkp_handler.get_local_backup_list()

            self.assertIsNotNone(local_bkp_list, "Error, backup_list for customer {} is null"
                                 .format(customer.name))

            expected_bkp_list_size = 0
            self.assertIs(expected_bkp_list_size,
                          len(local_bkp_list),
                          "Expected {} backups for customer {}. Got {}."
                          .format(expected_bkp_list_size, customer.name, len(local_bkp_list)))

            with self.assertRaises(Exception) as context:
                bkp_handler.process_backup_list()

            self.assertTrue("No backup to be processed for the customer" in
                            context.exception.message, "Wrong exception message.")

            offsite_list = self.bkp_tools.get_offsite_backup_dic(customer)

            self.assertIs(1, len(offsite_list.keys()), "Backup list dictionary size should be 1.")

            self.assertIs(0, len(offsite_list[customer.name]), "Backup list size should be 0.")


class TestLocalCleanupOneBackup(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 1
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()
        cls.create_remote_environment()

    def test_clean_local_backup(self):
        # Check nothing was cleaned.
        for customer in self.enmaas_config_dic.values():
            bkp_handler = LocalBackupHandler(self.offsite_config,
                                             customer,
                                             self.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             self.notification_manager,
                                             self.logger)

            local_bkp_list = bkp_handler.get_local_backup_list()

            self.assertIs(len(local_bkp_list), 1,
                          "Expected {} backups for customer {}. Got {}."
                          .format(1, customer.name, len(local_bkp_list)))

            ret, out = bkp_handler.clean_local_backup(local_bkp_list[0])

            self.assertFalse(ret, "Backup '{}' failed to be removed.".format(local_bkp_list[0]))

            self.assertTrue("Backup not removed".lower() in str(out).lower(),
                            "Backup wrongly removed '{}'.".format(local_bkp_list[0]))


class TestLocalCleanupTwoBackups(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 2
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()
        cls.create_remote_environment()

    def test_clean_local_backup(self):
        for customer in self.enmaas_config_dic.values():
            bkp_handler = LocalBackupHandler(self.offsite_config,
                                             customer,
                                             self.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             self.notification_manager,
                                             self.logger)

            local_bkp_list = bkp_handler.get_local_backup_list()

            expected_list_size = 1
            self.assertIs(len(local_bkp_list), expected_list_size,
                          "Expected {} backups for customer {}. Got {}."
                          .format(expected_list_size, customer.name, len(local_bkp_list)))

            ret, out = bkp_handler.clean_local_backup(local_bkp_list[0])

            self.assertTrue(ret, "Backup '{}' failed to be removed.".format(local_bkp_list[0]))

            self.assertTrue("Backup removed successfully".lower() in str(out).lower(),
                            "Backup not removed '{}'.".format(local_bkp_list[0]))


class TestLocalCleanupThreeBackups(TestEnmaasBackupAutomation):
    @classmethod
    def setUpClass(cls):
        cls.number_bkp = 3
        cls.number_volume = NUMBER_VOLUME
        cls.number_customer = NUMBER_CUSTOMER
        cls.number_threads = NUMBER_THREADS
        cls.number_process = NUMBER_PROCESS

        cls.create_test_objects()
        cls.create_local_environment()
        cls.create_remote_environment()

    def test_clean_local_backup(self):
        # Check nothing was cleaned.
        for customer in self.enmaas_config_dic.values():
            bkp_handler = LocalBackupHandler(self.offsite_config,
                                             customer,
                                             self.gpg_manager,
                                             NUMBER_PROCESS,
                                             NUMBER_THREADS,
                                             self.notification_manager,
                                             self.logger)

            local_bkp_list = bkp_handler.get_local_backup_list()

            expected_list_size = 2
            self.assertIs(len(local_bkp_list), expected_list_size,
                          "Expected {} backups for customer {}. Got {}."
                          .format(expected_list_size, customer.name, len(local_bkp_list)))

            for bkp_path in local_bkp_list:
                ret, out = bkp_handler.clean_local_backup(bkp_path)

                self.assertTrue(ret, "Backup '{}' failed to be removed.".format(local_bkp_list[0]))

                self.assertTrue("Backup removed successfully".lower() in str(out).lower(),
                                "Backup not removed '{}'.".format(local_bkp_list[0]))


class TestEnmaasBackupAutomationValidation(TestEnmaasBackupAutomation):
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

    def test_validate_metadata(self):
        for customer in self.bkp_map.keys():
            for bkp in self.bkp_map[customer].keys():
                for volume in self.bkp_map[customer][bkp]:
                    metadata_file = glob.glob(os.path.join(volume, str('*' + METADATA_FILE_SUFFIX)))

                    self.assertTrue(validate_metadata(volume, metadata_file[0], self.logger),
                                    "Failed to validate the local backup list from customer {}."
                                    .format(customer))

    def test_validate_metadata_missing_file(self):
        customer_name = "CUSTOMER_0"
        volume_name = "volume0"
        file_to_rename = "volume_file0.dat"

        for bkp in self.bkp_map[customer_name].keys():
            volume_path = os.path.join(bkp, volume_name)

            metadata_file = glob.glob(os.path.join(volume_path, str('*' + METADATA_FILE_SUFFIX)))

            os.rename(os.path.join(volume_path, file_to_rename),
                      os.path.join(volume_path, "{}.tmp".format(file_to_rename)))

            self.assertFalse(validate_metadata(volume_path, metadata_file[0], self.logger),
                             "Validation should return false.".format(customer_name))

            os.rename(os.path.join(volume_path, "{}.tmp".format(file_to_rename)),
                      os.path.join(volume_path, file_to_rename))


if __name__ == "__main__":
    TestUploadTwoBackupToOffsite = unittest.TestLoader() \
        .loadTestsFromTestCase(TestUploadTwoBackupsToOffsite)
    TestUploadOneBackupToOffsite = unittest.TestLoader() \
        .loadTestsFromTestCase(TestUploadOneBackupToOffsite)
    TestUploadZeroBackupToOffsite = unittest.TestLoader() \
        .loadTestsFromTestCase(TestUploadZeroBackupToOffsite)
    TestLocalCleanupOneBackup = unittest.TestLoader() \
        .loadTestsFromTestCase(TestLocalCleanupOneBackup)
    TestLocalCleanupTwoBackups = unittest.TestLoader() \
        .loadTestsFromTestCase(TestLocalCleanupTwoBackups)
    TestLocalCleanupThreeBackups = unittest.TestLoader() \
        .loadTestsFromTestCase(TestLocalCleanupThreeBackups)
    TestEnmaasBackupAutomationValidation = unittest.TestLoader() \
        .loadTestsFromTestCase(TestEnmaasBackupAutomationValidation)

    suites = unittest.TestSuite([TestUploadTwoBackupToOffsite,
                                 TestUploadOneBackupToOffsite,
                                 TestUploadZeroBackupToOffsite,
                                 TestLocalCleanupOneBackup,
                                 TestLocalCleanupTwoBackups,
                                 TestLocalCleanupThreeBackups,
                                 TestEnmaasBackupAutomationValidation])

    unittest.TextTestRunner(verbosity=2).run(suites)
