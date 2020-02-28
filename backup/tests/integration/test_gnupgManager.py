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
import unittest

from backup import utils
from backup.gnupg_manager import GnupgManager
from backup.logger import CustomLogger
from env_setup import create_local_mock_environment as mock

logging.disable(logging.CRITICAL)

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]
SCRIPT_PATH = os.path.dirname(__file__)
BKP_TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir")
TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir2")
FILE_NAME = "file"
TEST_IP = "127.0.0.1"


class TestGnupgManagerEncryption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)

        logger = CustomLogger(SCRIPT_FILE, "")
        cls.gpg_manager = GnupgManager("test", "test", logger)

    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)

    def setUp(self):
        utils.create_path(TMP_DIR)

    def tearDown(self):
        utils.remove_path(TMP_DIR)

    def test_validate_encryption_key_success(self):
        self.assertIsNone(self.gpg_manager.validate_encryption_key(),
                          "test_validate_encryption_key_success() has failed.")

    def test_encrypt_file_empty_parameters(self):
        with self.assertRaises(Exception):
            self.gpg_manager.encrypt_file("", "")

    def test_encrypt_file_invalid_input_invalid_output(self):
        with self.assertRaises(Exception):
            self.gpg_manager.encrypt_file("/test1", "/test2")

    def test_encrypt_file_invalid_input_valid_output(self):
        with self.assertRaises(Exception):
            self.gpg_manager.encrypt_file("/test1", BKP_TMP_DIR)

    def test_encrypt_file_valid_input_invalid_output(self):
        with self.assertRaises(Exception):
            self.gpg_manager.encrypt_file(BKP_TMP_DIR, os.path.join(BKP_TMP_DIR, mock.FILE_NAME))

    def test_encrypt_file_valid_input_valid_output(self):
        self.assertTrue(self.gpg_manager
                        .encrypt_file(os.path.join(BKP_TMP_DIR, mock.FILE_NAME), TMP_DIR),
                        "test_encrypt_file_valid_input_valid_output() has failed.")

    def test_encrypt_file_result(self):
        self.gpg_manager.encrypt_file(os.path.join(BKP_TMP_DIR, mock.FILE_NAME), TMP_DIR)
        self.assertTrue(os.path.isfile(os.path.join(TMP_DIR, mock.FILE_NAME + '.gpg')),
                        "test_encrypt_file_result() has failed.")

    def test_encrypt_file_list_valid_path(self):
        ret = self.gpg_manager.compress_encrypt_file_list(BKP_TMP_DIR, TMP_DIR)
        self.assertTrue(os.path.isfile(os.path.join(TMP_DIR, mock.FILE_NAME + '.gz.gpg')),
                        "test_encrypt_file_list_valid_path() has failed.")
        self.assertTrue(ret, "test_encrypt_file_list_valid_path() has failed.")


class TestGnupgManagerDecryption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        cls.gpg_manager = GnupgManager("test", "test", CustomLogger(SCRIPT_FILE, ""))

    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)

    def setUp(self):
        utils.create_path(TMP_DIR)
        self.encrypted_file_path = self.gpg_manager.encrypt_file(os.path.join(BKP_TMP_DIR,
                                                                              mock.FILE_NAME),
                                                                 TMP_DIR)

    def tearDown(self):
        utils.remove_path(TMP_DIR)

    def test_decrypt_file_empty(self):
        with self.assertRaises(Exception):
            self.gpg_manager.decrypt_file("")

    def test_decrypt_file_invalid_path(self):
        with self.assertRaises(Exception):
            self.gpg_manager.decrypt_file("/")

    def test_decrypt_file_valid_path(self):
        self.assertTrue(self.gpg_manager
                        .decrypt_file(os.path.join(TMP_DIR, mock.FILE_NAME + '.gpg')),
                        "test_decrypt_file_valid_path() has failed.")

    def test_decrypt_file_flag(self):
        self.assertTrue(self.gpg_manager
                        .decrypt_file(os.path.join(TMP_DIR, mock.FILE_NAME + '.gpg')),
                        "test_decrypt_file_flag() has failed,")

    def test_decrypt_file_result(self):
        self.gpg_manager.decrypt_file(os.path.join(TMP_DIR, mock.FILE_NAME + '.gpg'))
        self.assertTrue(os.path.isfile(os.path.join(TMP_DIR, mock.FILE_NAME)),
                        "test_decrypt_file_result() has failed")

    def test_decrypt_file_list_valid_path(self):
        utils.remove_path(self.encrypted_file_path)
        file_path = os.path.join(BKP_TMP_DIR, mock.FILE_NAME)
        compressed_file_name = utils.compress_file(file_path, TMP_DIR)
        self.compressed_encrypted_file_path = self.gpg_manager.encrypt_file(compressed_file_name,
                                                                            TMP_DIR)
        utils.remove_path(compressed_file_name)

        ret = self.gpg_manager.decrypt_decompress_file_list(TMP_DIR)
        self.assertTrue(os.path.isfile(os.path.join(TMP_DIR, mock.FILE_NAME)),
                        "test_decrypt_file_list_valid_path() has failed")
        self.assertTrue(ret, "returned value should be a true.")


if __name__ == "__main__":
    TestGnupgManagerEncryption = unittest.TestLoader() \
        .loadTestsFromTestCase(TestGnupgManagerEncryption)
    TestGnupgManagerDecryption = unittest.TestLoader() \
        .loadTestsFromTestCase(TestGnupgManagerDecryption)

    suites = unittest.TestSuite([TestGnupgManagerEncryption, TestGnupgManagerDecryption])

    unittest.TextTestRunner(verbosity=2).run(suites)
