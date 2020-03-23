# For the snake_case comments
# pylint: disable=C0103

"""
This module is for unit tests from the utils.py script
"""

import unittest
import os
from os import path
import shutil
import hashlib
import time
from subprocess import PIPE, Popen
import tarfile
import binascii
import tempfile
import mock
from backup import utils as utils


SCRIPT_PATH = os.path.dirname(__file__)
TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir")
VALID_COMMAND = "echo Hello World!\n"
VALID_HOST = '127.0.0.1'
INVALID_HOST = "2.3.4."
INVALID_COMMAND = 'bla bla bla'
TIME_SLEEP = 3
FILE_NAME = "volume_file"
DEFAULT_FILE_SIZE = 100 * 1024


class UtilsCreatePathTestCase(unittest.TestCase):
    """
    Test Cases for create_path method in utils.py
    """

    @classmethod
    @mock.patch('os.makedirs', autospec=True)
    def test_create_path_with_valid_path(cls, mock_make_dirs):
        """
        Test if destination directory is created when valid path is provided
        :param mock_make_dirs: mocking os.makedirs method
        """
        utils.create_path(TMP_DIR)
        mock_make_dirs.assert_called_once_with(TMP_DIR)

    def test_create_path_with_no_arguments(self):
        """
        Test if path is created when no argument is provided
        """
        with self.assertRaises(TypeError):
            utils.create_path()

    def test_create_path_with_multiple_arguments(self):
        """
        Test that when attempt creating path with multiple arguments raise TypeError
        """
        with self.assertRaises(TypeError):
            utils.create_path(TMP_DIR, TMP_DIR)

    @classmethod
    @mock.patch.object(os.path, 'exists')
    def test_create_path_already_exists(cls, mock_exists):
        """
        Test if existence of path is being checked
        :param mock_exists: mocking os.path.exists method
        """
        utils.create_path(TMP_DIR)
        mock_exists.assert_called_once_with(TMP_DIR)


class UtilsRemovePathTestCase(unittest.TestCase):
    """
    Test Cases for remove_path method in utils.py
    """

    @mock.patch.object(os.path, 'exists')
    def test_remove_path_non_existent_path(self, mock_exists):
        """
        Test remove path when it does not exist
        :param mock_exists: mocking os.path.exists method
        """
        mock_exists.return_value = False
        self.assertTrue(utils.remove_path(TMP_DIR))

    @classmethod
    @mock.patch.object(os.path, 'isdir')
    @mock.patch.object(os.path, 'exists')
    def test_remove_path_existent_path(cls, mock_exists, mock_isdir):
        """
        Test remove existing path when it is an existing directory
        :param mock_exists: mocking os.path.exists method
        :param mock_isdir: mocking os.path.isdir method
        """
        mock_exists.return_value = True
        utils.remove_path(TMP_DIR)
        mock_isdir.assert_called_once_with(TMP_DIR)

    def test_remove_path_with_no_arguments(self):
        """
        Test remove path when no argument is provided
        """
        with self.assertRaises(TypeError):
            utils.remove_path()

    def test_remove_path_multiple_directories(self):
        """
        Test remove multiple directories
        """
        with self.assertRaises(TypeError):
            utils.remove_path(TMP_DIR, TMP_DIR)

    def test_remove_path_invalid_path(self):
        """
        Test remove invalid path
        """
        with self.assertRaises(TypeError):
            utils.remove_path(1)


class UtilsRunRemoteCommandTestCase(unittest.TestCase):
    """
    Test Cases for popen_communicate method in utils.py
    """

    @mock.patch("backup.utils.TIMEOUT")
    def test_run_remote_command_valid_host_and_command(self, mock_timeout):
        """
        Test open pipe with valid host and valid command
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        stdout, _ = utils.popen_communicate(VALID_HOST, VALID_COMMAND)
        self.assertEquals(stdout, b"Hello World!\n")
        stdout, _ = utils.popen_communicate('localhost', VALID_COMMAND)
        self.assertEquals(stdout, b"Hello World!\n")

    def test_run_remote_command_invalid_host(self):
        """
        Test open pipe with invalid host
        """
        stdout, _ = utils.popen_communicate(INVALID_HOST, VALID_COMMAND)
        self.assertEquals(stdout, "")

    def test_run_remote_command_invalid_command(self):
        """
        Test open pipe with invalid command
        """
        stdout, _ = utils.popen_communicate(VALID_HOST, INVALID_COMMAND)
        self.assertEquals(stdout, "")


class UtilsCheckRemotePathExistsTestCase(unittest.TestCase):
    """
    Test Cases for check_remote_path method in utils.py
    """

    @classmethod
    @mock.patch.object(utils, 'popen_communicate')
    def test_check_remote_path_attempt_run_remote_command(cls, mock_popen):
        """
        Test creation of pipe to connect to remote machine
        :param mock_popen: mocking utils.popen_communicate method
        """
        mock_popen.return_value = "DIR_IS_AVAILABLE", ""
        utils.check_remote_path_exists(VALID_HOST, SCRIPT_PATH)
        mock_popen.assert_called_once()

    @mock.patch("backup.utils.TIMEOUT")
    def test_check_remote_path_non_existent_directory(self, mock_timeout):
        """
        Test nonexistence of directory in remote machine
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        self.assertFalse(utils.check_remote_path_exists(VALID_HOST, TMP_DIR))

    @mock.patch("backup.utils.TIMEOUT")
    def test_check_remote_path_existence(self, mock_timeout):
        """
        Test existence of directory in remote machine
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        self.assertTrue(utils.check_remote_path_exists(VALID_HOST, SCRIPT_PATH))

    @mock.patch("backup.utils.TIMEOUT")
    def test_check_remote_path_in_invalid_host(self, mock_timeout):
        """
        Test existence of directory in invalid host
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        self.assertFalse(utils.check_remote_path_exists(INVALID_HOST, SCRIPT_PATH))


class UtilsCreateRemoteDirTestCase(unittest.TestCase):
    """
    Test Cases for create_remote_dir method in utils.py
    """

    @classmethod
    @mock.patch("backup.utils.TIMEOUT")
    @mock.patch.object(utils, 'popen_communicate')
    def test_create_remote_dir_with_valid_host_and_path(cls, mock_popen, mock_timeout):
        """
        Test creation of directory in remote machine with valid host and path
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        :param mock_popen: mocking utils.popen_communicate method
        """
        mock_timeout.return_value = 20
        mock_popen.return_value = "END-OF-COMMAND\nDIR_IS_AVAILABLE\n", ""
        stdout = utils.create_remote_dir(VALID_HOST, TMP_DIR)
        mock_popen.test_assert_called_once()
        assert stdout


class UtilsRemoveRemoteDirTestCase(unittest.TestCase):
    """
    Test Cases for remove_dir_list method in utils.py
    """

    def setUp(self):
        """
        Create testing scenario
        """
        self.dir_list = ['bkps/CUSTOMER/2018-09-10',
                         'bkps/CUSTOMER/2018-09-11',
                         'bkps/CUSTOMER/2018-09-12']

        self.remove_dir_list = []

        for directory in self.dir_list:
            self.remove_dir_list.append(os.path.join(SCRIPT_PATH, directory))
            utils.create_path(self.remove_dir_list[-1])

    def tearDown(self):
        """
        Tear down created scenario
        """
        shutil.rmtree(os.path.join(SCRIPT_PATH, 'bkps'))

    @mock.patch("backup.utils.TIMEOUT")
    def test_remove_remote_dir_list(self, mock_timeout):
        """
        Test remove directory list in valid remote_machine
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        not_removed_list, validated_removed_list = utils.remove_remote_dir(VALID_HOST,
                                                                           self.remove_dir_list)

        self.assertEquals(len(not_removed_list), 0)
        self.assertEquals(len(validated_removed_list), len(self.remove_dir_list))

    def test_remove_remote_dir_empty_list(self):
        """
        Test remove empty directory list from valid remote_machine
        """
        with self.assertRaises(Exception) as e:
            utils.remove_remote_dir(VALID_HOST, [])
        self.assertEquals("Empty list was provided.", e.exception.message)

    @mock.patch("backup.utils.TIMEOUT")
    def test_remove_remote_dir_single_directory(self, mock_timeout):
        """
        Test remove single directory from valid remote_machine
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        not_removed_list, validated_removed_list = utils.remove_remote_dir(VALID_HOST,
                                                                           self.remove_dir_list[0])
        self.assertEquals(len(not_removed_list), 0)
        self.assertEquals(len(validated_removed_list), 1)

    @mock.patch("backup.utils.TIMEOUT")
    def test_remove_remote_dir_invalid_directory(self, mock_timeout):
        """
        Test remove invalid directory from valid remote_machine
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        not_removed_list, validated_removed_list = utils.remove_remote_dir(VALID_HOST, TMP_DIR)
        assert not not_removed_list
        self.assertEquals(len(validated_removed_list), 1)

    @mock.patch("backup.utils.TIMEOUT")
    def test_remove_remote_dir_from_invalid_remote(self, mock_timeout):
        """
        Test remove directory list from invalid remote_machine
        :param mock_timeout: mocking backup.utils.TIMEOUT constant
        """
        mock_timeout.return_value = 20
        with self.assertRaises(Exception) as e:
            utils.remove_remote_dir(INVALID_HOST, self.remove_dir_list)
        self.assertIn("Unable to perform the remove command on offsite due to: ssh: Could not "
                      "resolve hostname", e.exception.message)


class UtilsFindElemDicTestCase(unittest.TestCase):
    """
    Test Cases for find_elem_dic method in utils.py
    """

    def setUp(self):
        """
        Create testing scenario
        """
        self.backup_tag = "2018-08-24"
        self.customer_backup_dic = {'CUSTOMER_0':
                                    ['/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-25',
                                     '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-24',
                                     '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-23'
                                    ]}
        self.item = 'CUSTOMER_0', '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-24'

    def test_find_elem_dic_existent_element(self):
        """
        Test find existent element in dictionary
        """
        key, item = utils.find_elem_dic(self.customer_backup_dic, self.backup_tag)
        self.assertTupleEqual((key, item), self.item)

    def test_find_elem_dic_non_existent_element(self):
        """
        Test find non-existent element in dictionary
        """
        non_existent_backup_tag = "2019-08-26"
        key, item = utils.find_elem_dic(self.customer_backup_dic, non_existent_backup_tag)
        self.assertTupleEqual((key, item), ('', ''))

    def test_find_elem_dic_empty_query(self):
        """
        Test find element in dictionary with empty query
        """
        empty_query = ""
        key, item = utils.find_elem_dic(self.customer_backup_dic, empty_query)
        self.assertTupleEqual((key, item), ('', ''))

    def test_find_elem_dic_empty_dictionary(self):
        """
        Test find element in empty dictionary
        """
        empty_dictionary = ""
        with self.assertRaises(AttributeError):
            utils.find_elem_dic(empty_dictionary, self.backup_tag)


class UtilsGetMD5TestCase(unittest.TestCase):
    """
    Test Cases for get_md5 method in utils.py
    """
    def setUp(self):
        """
        Create testing scenario
        """
        self.test_dir = tempfile.mkdtemp()
        self.temp_file = open(path.join(self.test_dir, 'test.txt'), 'w')
        self.temp_file.write('The bug is on the table')
        self.tempfile_hash = hashlib.md5(open(self.temp_file.name).read()).hexdigest()

    def tearDown(self):
        """
        Tear down created scenario
        """
        shutil.rmtree(self.test_dir)

    def test_get_md5_generated_correctly(self):
        """

        Test MD5 generator
        """
        result = utils.get_md5(self.temp_file.name)
        self.assertEqual(result, self.tempfile_hash)


class UtilsIsValidIpTestCase(unittest.TestCase):
    """
    Test Cases for is_valid_ip method in utils.py
    """

    def test_is_valid_ip(self):
        """
        Test if ip is valid
        """
        self.assertTrue(utils.is_valid_ip(VALID_HOST))

    def test_is_valid_ip_invalid_ip(self):
        """
        Test invalid ip
        """
        self.assertFalse(utils.is_valid_ip(INVALID_HOST))


class UtilsValidateHostIsAccessibleTestCase(unittest.TestCase):
    """
    Test Cases for validate_host_is_accessible method in utils.py
    """

    def test_validate_host_is_accessible(self):
        """
        Test if valid host is accessible
        """
        self.assertTrue(utils.validate_host_is_accessible("localhost"))

    def test_validate_host_is_accessible_invalid_host(self):
        """
        Test invalid host is not accessible
        """
        self.assertFalse(utils.validate_host_is_accessible(INVALID_HOST))


class UtilsTimeItTestCase(unittest.TestCase):
    """
    Test Cases for timeit decorator located in utils.py
    """
    def setUp(self):
        """
        Create testing scenario
        """
        self.elapsed_time_array = []
        self.elapsed_time = 1

    @classmethod
    @utils.timeit
    def dummy_method(cls, good_input=True, **kwargs):
        """
        Dummy method to use with @utils.timeit decorator
        """
        if good_input:
            time.sleep(TIME_SLEEP)
            return "Decorators are a bit brain-melting"
        raise Exception("Dummy Exception!")

    def test_timeit_time_decorated_method_accordingly(self):
        """
        Test if decorated method is timed accordingly
        """
        self.dummy_method(get_elapsed_time=self.elapsed_time_array)
        assert self.elapsed_time_array[0] > TIME_SLEEP
        assert self.elapsed_time_array

    @mock.patch.object(time, 'time')
    def test_timeit_measurement_done_twice(self, mock_time):
        """
        Test if time measurement is done twice in decorated method
        :param mock_time: mocking time.time() method
        """
        self.dummy_method(get_elapsed_time=self.elapsed_time_array)
        self.assertEqual(mock_time.call_count, 2)

    def test_timeit_output_of_decorated_method_is_the_one_expected(self):
        """
        Test if output of decorated method is the one expected
        """
        self.assertEquals(self.dummy_method(get_elapsed_time=self.elapsed_time_array),
                          "Decorators are a bit brain-melting")

    def test_timeit_when_get_elapsed_time_is_not_a_list(self):
        """
        Test if timeit acts when get_elapsed_time variable is not a list
        """
        self.dummy_method(get_elapsed_time=self.elapsed_time)
        self.assertEqual(self.elapsed_time, 1)

    def test_timeit_even_when_exception_is_raised_on_decorated_method(self):
        """
        Test measurement is done even when exception is raised on decorated method
        """
        with self.assertRaises(Exception) as exception:
            self.dummy_method(good_input=False, get_elapsed_time=self.elapsed_time_array)
            assert self.elapsed_time_array[0] > 0
            assert not self.elapsed_time_array
            self.assertEqual("Dummy Exception!", exception.exception.message)


class UtilsCompressFileTestCase(unittest.TestCase):
    """
    Test Cases for compress_file method located in utils.py
    """
    def setUp(self):
        """
        Create testing scenario
        """
        self.test_file_path = os.path.join(SCRIPT_PATH, FILE_NAME)
        self.compressed_file = self.test_file_path + ".gz"
        self.tar_file = self.compressed_file + ".tar"
        self.test_dir = os.path.dirname(self.test_file_path)

        if not os.path.exists(self.test_file_path):
            with open(self.test_file_path, 'wb') as f:
                f.write(os.urandom(DEFAULT_FILE_SIZE))

    def tearDown(self):
        """
        Tear down created scenario
        """
        utils.remove_path(self.test_file_path)
        utils.remove_path(self.compressed_file)
        utils.remove_path(self.tar_file)

    def test_compress_file_is_gzip_compressed_cross_platform(self):
        """
        Test if file is gzip compressed in cross_platform
        """
        utils.compress_file(self.test_file_path)
        with open(self.compressed_file, 'rb') as test_f:
            self.assertEquals(binascii.hexlify(test_f.read(2)), b'1f8b')

    @mock.patch.object(utils, 'gzip_file')
    def test_gzip_file_function_is_being_called(self, mock_gzip_file):
        """
        Test if compress file function is being called
        :param mock_gzip_file: mocking gzip_file method
        """
        utils.compress_file(self.test_file_path)
        self.assertEqual(mock_gzip_file.call_count, 1)

    @mock.patch.object(utils, 'tar_file')
    def test_tar_file_function_is_being_called(self, mock_tar_file):
        """
        Test if compress file function is being called
        :param mock_tar_file: mocking tar_file method
        """
        utils.compress_file(self.test_file_path, None, "w")
        self.assertEqual(mock_tar_file.call_count, 1)

    def test_compress_file_files_inside_compressed_volume_are_not_corrupted(self):
        """
        Test if files inside compressed volume are not corrupted
        """
        utils.compress_file(self.test_file_path)
        utils.compress_file(self.compressed_file, None, "w")
        utils.remove_path(self.compressed_file)
        utils.remove_path(self.test_file_path)

        ret = Popen(['tar', '-C', self.test_dir, '-xf', self.tar_file], stdout=PIPE,
                    stderr=PIPE).wait()
        self.assertEquals(ret, 0)

        ret = Popen(['gunzip', self.compressed_file], stdout=PIPE, stderr=PIPE).wait()
        self.assertEquals(ret, 0)

    def test_compress_file_gzip_file_is_not_corrupted(self):
        """
        Test gzip file is not corrupted
        """
        utils.compress_file(self.test_file_path)
        p = Popen(['gunzip', '-t', self.compressed_file], stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        exitcode = p.returncode
        self.assertEquals(err, '')
        self.assertEquals(out.strip(), "")
        self.assertEquals(exitcode, 0)

    def test_compress_file_invalid_source_path_is_provided(self):
        """
        Test if exception is raised when invalid source path is provided
        """
        with self.assertRaises(Exception) as exception:
            utils.compress_file(TMP_DIR)
            self.assertEqual("File does not exist '{}'".format(TMP_DIR),
                             exception.exception.message)


class UtilsDecompressFileTestCase(unittest.TestCase):
    """
    Test Cases for decompress_file method located in utils.py
    """

    def setUp(self):
        """
        Create testing scenario
        """
        self.dest_dir = os.path.join(os.path.dirname(__file__), 'extract_dir')

    def tearDown(self):
        """
        Tear down created scenario
        """
        shutil.rmtree(self.dest_dir, ignore_errors=True)

    def test_decompress_file_invalid_decompressed_file(self):
        """
        Test if raises exception on invalid decompressed file
        """
        with self.assertRaises(Exception):
            utils.decompress_file(__file__, self.dest_dir)
