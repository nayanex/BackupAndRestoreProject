import logging
import os
import unittest

from backup import utils as utils
from env_setup import create_local_mock_environment as mock

logging.disable(logging.CRITICAL)

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]
SCRIPT_PATH = os.path.dirname(__file__)
BKP_TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir")
TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir2")
INVALID_PATH = os.path.join(SCRIPT_PATH, "invalid")
COMPRESSED_FILE_PATH = BKP_TMP_DIR + ".gz"
LOCALHOST = "127.0.0.1"
INVALID_IP = "1.2.3.4"
VALID_HOST = "{}@{}".format(utils.get_current_user(), LOCALHOST)
INVALID_HOST = "{}@{}".format("INVALID_USER", INVALID_IP)


class TestUtilsLocal(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)

    def test_create_path_empty(self):
        self.assertFalse(utils.create_path(""), "test_create_path_empty() has failed.")

    def test_create_path_with_multiple_subfolders(self):
        utils.create_path(BKP_TMP_DIR)
        invalid_path = os.path.join(BKP_TMP_DIR, "test1", "test2")
        self.assertTrue(utils.create_path(invalid_path),
                        "test_create_path_with_multiple_subfolders() has failed")

    def test_create_path_valid_path(self):
        self.assertTrue(utils.create_path(BKP_TMP_DIR),
                        "test_create_path_valid_path() has failed")

    def test_create_path_existing_path(self):
        utils.create_path(BKP_TMP_DIR)
        self.assertTrue(utils.create_path(BKP_TMP_DIR),
                        "test_create_path_existing_path()")

    def test_create_path_check_result(self):
        utils.create_path(BKP_TMP_DIR)
        self.assertTrue(os.path.isdir(BKP_TMP_DIR) != 0,
                        "test_create_path_check_result() has failed.")


class TestUtilsLocalRemove(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.create_path(BKP_TMP_DIR)

    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)

    def test_remove_path_empty(self):
        self.assertTrue(utils.remove_path(""),
                        "test_remove_path_empty() has failed.")

    def test_remove_path_invalid_path(self):
        self.assertTrue(utils.remove_path(BKP_TMP_DIR),
                        "test_remove_path_invalid_path() has failed.")

    def test_remove_path_existing_path(self):
        self.assertTrue(utils.remove_path(BKP_TMP_DIR),
                        "test_remove_path_existing_path() has failed")
        self.assertFalse(os.path.exists(BKP_TMP_DIR),
                         "test_remove_path_existing_path() has failed")

    def test_remove_path_check_result(self):
        utils.create_path(BKP_TMP_DIR)
        utils.remove_path(BKP_TMP_DIR)
        self.assertTrue(os.path.isdir(BKP_TMP_DIR) == 0,
                        "test_remove_path_check_result() has failed.")


class TestUtilsRemoteCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)

    @classmethod
    def tearDown(cls):
        utils.remove_path(BKP_TMP_DIR)

    def test_check_remote_path_exists_empty(self):
        self.assertFalse(utils.check_remote_path_exists("", ""),
                         "test_check_remote_path_exists_empty() has failed.")

    def test_check_remote_path_exists_invalid_host(self):
        self.assertFalse(utils.check_remote_path_exists("2.3.4.5", ""),
                         "test_check_remote_path_exists_invalid_host() has failed.")

    def test_check_remote_path_exists_invalid_path(self):
        utils.remove_path(BKP_TMP_DIR)
        self.assertFalse(utils.check_remote_path_exists("{}@{}".format(utils.get_current_user(),
                                                                       LOCALHOST), BKP_TMP_DIR),
                         "test_check_remote_path_exists_invalid_path() has failed.")

    def test_check_remote_path_exists_valid_parameters(self):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        self.assertTrue(utils.check_remote_path_exists("{}@{}".format(utils.get_current_user(),
                                                                      LOCALHOST), BKP_TMP_DIR),
                        "test_check_remote_path_exists_valid_parameters() has failed.")


class TestUtilsRemoteCreate(unittest.TestCase):
    @classmethod
    def tearDown(cls):
        utils.remove_path(BKP_TMP_DIR)

    def test_create_remote_dir_empty(self):
        self.assertFalse(utils.create_remote_dir("", ""),
                         "test_create_remote_dir_empty() has failed.")

    def test_create_remote_dir_invalid_host(self):
        self.assertFalse(utils.create_remote_dir("2.3.4.5", ""),
                         "test_create_remote_dir_invalid_host() has failed.")

    def test_create_remote_dir_invalid_path(self):
        utils.create_path(BKP_TMP_DIR)
        ret = utils.create_remote_dir("{}@{}".format(utils.get_current_user(), LOCALHOST),
                                      BKP_TMP_DIR)
        self.assertFalse(ret, "test_create_remote_dir_invalid_path() has failed.")

    def test_create_remote_dir_valid_parameters(self):
        self.assertTrue(utils.create_remote_dir("{}@{}".format(utils.get_current_user(), LOCALHOST),
                                                BKP_TMP_DIR),
                        "test_create_remote_dir_valid_parameters() has failed")

    def test_create_remote_dir_check_result(self):
        utils.create_remote_dir("{}@{}".format(utils.get_current_user(), LOCALHOST), BKP_TMP_DIR)
        self.assertTrue(utils.check_remote_path_exists("{}@{}".format(utils.get_current_user(),
                                                                      LOCALHOST), BKP_TMP_DIR),
                        "test_create_remote_dir_check_result() has failed.")


class TestUtilsRemoteRemove(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)

    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)

    def test_remove_remote_dir_empty(self):
        with self.assertRaises(Exception) as context:
            utils.remove_remote_dir("2.3.4.5", "")

        self.assertEqual("Empty directory was provided.", context.exception.message,
                         "test_remove_remote_dir_empty() has failed.")

    def test_remove_remote_dir_invalid_host(self):
        with self.assertRaises(Exception) as context:
            utils.remove_remote_dir("", "directory")

        self.assertEqual("Empty host was provided.", context.exception.message,
                         "test_remove_remote_dir_invalid_host() has failed.")

    def test_remove_remote_dir_invalid_path(self):
        with self.assertRaises(Exception) as context:
            utils.remove_remote_dir(INVALID_HOST, INVALID_PATH)

        self.assertTrue("Unable to perform the remove command on offsite" in
                        context.exception.message,
                        "test_remove_remote_dir_invalid_path() has failed.")

    def test_remove_remote_dir_valid_parameters(self):
        not_removed_list, removed_list = utils.remove_remote_dir(VALID_HOST, BKP_TMP_DIR)

        self.assertTrue(len(not_removed_list) == 0, "There are directories not removed.")
        self.assertTrue(len(removed_list) == 1, "Removed list should have one element.")
        self.assertTrue(removed_list[0] == BKP_TMP_DIR, "Removed list should have the path {}."
                        .format(BKP_TMP_DIR))

    def test_remove_remote_dir_check_result(self):
        utils.remove_remote_dir(VALID_HOST, BKP_TMP_DIR)
        self.assertFalse(utils.check_remote_path_exists(VALID_HOST, BKP_TMP_DIR),
                         "test_remove_remote_dir_check_result() has failed.")


class TestUtilsCompressionSuper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)

    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)
        utils.remove_path(COMPRESSED_FILE_PATH)


class TestUtilsCompress(TestUtilsCompressionSuper):
    def test_compress_file_empty(self):
        with self.assertRaises(Exception):
            utils.compress_file("")

    def test_compress_file_invalid_source_path(self):
        with self.assertRaises(Exception):
            utils.remove_path(BKP_TMP_DIR)
            utils.compress_file(BKP_TMP_DIR)

    def test_compress_file_valid_parameters(self):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        self.assertTrue(utils.compress_file(BKP_TMP_DIR),
                        "test_compress_file_valid_parameters() has failed.")


class TestUtilsDecompress(TestUtilsCompressionSuper):
    def test_decompress_file_empty(self):
        with self.assertRaises(Exception):
            utils.decompress_file("", "")

    def test_decompress_file_invalid_source_path(self):
        with self.assertRaises(Exception):
            utils.remove_path(BKP_TMP_DIR)
            utils.decompress_file(BKP_TMP_DIR, "")

    def test_decompress_file_invalid_output_path(self):
        with self.assertRaises(Exception):
            utils.decompress_file(BKP_TMP_DIR, TMP_DIR)

    def test_decompress_file_valid_parameters(self):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        utils.compress_file(BKP_TMP_DIR)
        utils.remove_path(BKP_TMP_DIR)
        self.assertTrue(utils.decompress_file(COMPRESSED_FILE_PATH, SCRIPT_PATH),
                        "test_decompress_file_valid_parameters() has failed.")

    def test_decompress_file_flag(self):
        utils.create_path(BKP_TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        utils.compress_file(BKP_TMP_DIR)
        utils.remove_path(BKP_TMP_DIR)
        self.assertTrue(utils.decompress_file(COMPRESSED_FILE_PATH, SCRIPT_PATH, True),
                        "test_decompress_file_flag() has failed.")


class TestUtilsTransfer(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        utils.remove_path(BKP_TMP_DIR)
        utils.remove_path(TMP_DIR)

    def test_transfer_file_empty(self):
        with self.assertRaises(Exception):
            utils.transfer_file("", "")

    def test_transfer_file_invalid_source_valid_path(self):
        with self.assertRaises(Exception):
            utils.transfer_file(BKP_TMP_DIR, TMP_DIR)

    def test_transfer_file_valid_source_invalid_path(self):
        with self.assertRaises(Exception):
            utils.transfer_file(TMP_DIR, "{}@{}:{}"
                                .format(utils.get_current_user(), LOCALHOST,
                                        os.path.join(BKP_TMP_DIR, mock.FILE_NAME)))

    def test_transfer_file_valid_parameters_send(self):
        utils.create_path(BKP_TMP_DIR)
        utils.create_path(TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        self.assertTrue(utils.transfer_file("{}@{}:{}"
                                            .format(utils.get_current_user(), LOCALHOST,
                                                    os.path.join(BKP_TMP_DIR, mock.FILE_NAME)),
                                            TMP_DIR),
                        "test_transfer_file_valid_parameters_receive() has failed.")

    def test_transfer_file_valid_parameters_receive(self):
        utils.create_path(BKP_TMP_DIR)
        utils.create_path(TMP_DIR)
        mock.create_mock_file(BKP_TMP_DIR, 100)
        self.assertTrue(utils.transfer_file(BKP_TMP_DIR, TMP_DIR),
                        "test_transfer_file_valid_parameters_send() has failed.")


if __name__ == "__main__":
    TestUtilsLocal = unittest.TestLoader().loadTestsFromTestCase(TestUtilsLocal)
    TestUtilsLocalRemove = unittest.TestLoader().loadTestsFromTestCase(TestUtilsLocalRemove)
    TestUtilsRemoteCheck = unittest.TestLoader().loadTestsFromTestCase(TestUtilsRemoteCheck)
    TestUtilsRemoteCreate = unittest.TestLoader().loadTestsFromTestCase(TestUtilsRemoteCreate)
    TestUtilsRemoteRemove = unittest.TestLoader().loadTestsFromTestCase(TestUtilsRemoteRemove)
    TestUtilsCompress = unittest.TestLoader().loadTestsFromTestCase(TestUtilsCompress)
    TestUtilsDecompress = unittest.TestLoader().loadTestsFromTestCase(TestUtilsDecompress)
    TestUtilsTransfer = unittest.TestLoader().loadTestsFromTestCase(TestUtilsTransfer)

    suites = unittest.TestSuite([TestUtilsLocal, TestUtilsLocalRemove, TestUtilsRemoteCheck,
                                 TestUtilsRemoteCreate, TestUtilsRemoteRemove, TestUtilsCompress,
                                 TestUtilsDecompress, TestUtilsTransfer])

    unittest.TextTestRunner(verbosity=2).run(suites)
