##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

#pylint: disable=E0401
#pylint: disable=C0103

"""
Module for testing backup/gnupg_manager.py script
"""

import unittest
import os
import mock

from backup.gnupg_manager import GnupgManager
from backup.utils import get_home_dir

MOCK_PACKAGE = 'backup.gnupg_manager.'
GPG_KEY_PATH = os.path.join(get_home_dir(), ".gnupg")

MOCK_FILE_PATH = 'mock_file_path'
MOCK_SOURCE_DIR = 'mock_path'
MOCK_OUTPUT_PATH = 'mock_output_path'
MOCK_ENCRYPTED_FILE = 'mock_encrypted_file.gpg'
MOCK_DECRYPTED_FILE = 'mock_encrypted_file'


class GnupgManagerValidateEncryptionKeyTestCase(unittest.TestCase):
    """
    Class for testing validate_encryption_key() method from GnupgManager class
    """

    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_validate_encryption_key_initial_log(self, mock_gpg, mock_manager, mock_logger):
        """
        Test to check the initial log

        """
        mock_manager.gpg_handler = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email,
                                     mock_logger)

        calls = [mock.call("Validating GPG encryption settings.")]

        gnupg_manager.validate_encryption_key()
        gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen.wait')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_validate_encryption_return_value(self, mock_gpg, mock_manager, mock_wait, mock_logger):
        """
        Test to check the return value if result of Popen.wait() = 0
        """
        mock_manager.gpg_handler = mock_gpg
        mock_wait.return_value = 0

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        self.assertIsNone(gnupg_manager.validate_encryption_key())

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen.wait')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_validate_encryption_key_creating_key_log(self, mock_gpg, mock_manager, mock_wait,
                                                      mock_logger):
        """
        Test to check the log values if the key generation has started
        """
        mock_manager.gpg_handler = mock_gpg
        mock_wait.return_value = 1

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        calls = [mock.call("Validating GPG encryption settings."),
                 mock.call("Backup key does not exist yet. Creating a new one.")]

        gnupg_manager.validate_encryption_key()
        gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen.wait')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_validate_encryption_key_generate_key(self, mock_gpg, mock_manager, mock_wait,
                                                  mock_logger):
        """
        Test to check if generation of key is being triggered
        """
        mock_manager.gpg_handler = mock_gpg
        mock_wait.return_value = 1

        calls = [mock.call().gen_key_input(key_length=1024, key_type='RSA',
                                           name_email='user_email',
                                           name_real='user_name')]

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        gnupg_manager.validate_encryption_key()

        mock_gpg.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen.wait')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_validate_encryption_key_exception(self, mock_gpg, mock_manager, mock_wait,
                                               mock_logger):
        """
        Test to check the raise of exception if GPG is not installed
        """
        mock_gpg.return_value = None
        mock_manager.gpg_handler.side_effect = mock_gpg
        mock_wait.return_value = 1

        with self.assertRaises(Exception):
            gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)


class GnupgManagerEncryptFileTestCase(unittest.TestCase):
    """
    Class for testing encrypt_file() method from GnupgManager class
    """
    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_encrypt_file_empty_file_path(self, mock_gpg, mock_manager, mock_popen, mock_open,
                                          mock_logger):
        """
        Test to check the raise of exception if file_path is empty
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.encrypt_file('', MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message,
                             "An empty file path or output file path was provided.")

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_encrypt_file_empty_output_path(self, mock_gpg, mock_manager, mock_popen, mock_open,
                                            mock_logger):
        """
        Test to check the raise of exception if output_path is empty
        """
        mock_manager.gpg_handler.side_effect = mock_gpg
        mock_open.return_value = mock.MagicMock(spec=file)

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.encrypt_file(MOCK_FILE_PATH, '')

            self.assertEqual(cex.exception.message,
                             "An empty file path or output file path was provided.")

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_encrypt_file_not_exists(self, mock_gpg, mock_manager, mock_os, mock_popen,
                                     mock_open, mock_logger):
        """
        Test to check the raise of exception if file_path does not exist
        """
        mock_os.path.exists.return_value = False
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.encrypt_file(MOCK_FILE_PATH, MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message,
                             "Informed file does not exist '{}'.".format(MOCK_FILE_PATH))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_encrypt_file_log(self, mock_gpg, mock_manager, mock_os, mock_open, mock_popen,
                              mock_logger):
        """
        Test to check the log if encryption has started
        """
        mock_os.path.exists.return_value = True
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        calls = [mock.call("Encrypting file '{}'".format(MOCK_FILE_PATH))]

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            gnupg_manager.encrypt_file(MOCK_FILE_PATH, MOCK_OUTPUT_PATH)
            gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_encrypt_file_encryption_failure(self, mock_gpg, mock_manager, mock_os, mock_open,
                                             mock_popen, mock_logger):
        """
        Test to check the raise of exception if encryption could not be completed
        """
        mock_os.path.exists.return_value = True
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_popen.return_value.wait.return_value = 1
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.encrypt_file(MOCK_FILE_PATH, MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message, "Encryption of file {} could not be completed.".
                             format(MOCK_FILE_PATH))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_encrypt_file_return_value(self, mock_gpg, mock_manager, mock_os, mock_open, mock_popen,
                                       mock_logger):
        """
        Test to check the return value if encryption was successful
        """
        mock_os.path.exists.return_value = True
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            self.assertEqual(type(gnupg_manager.encrypt_file(MOCK_FILE_PATH, MOCK_OUTPUT_PATH)),
                             str)


class GnupgManagerCompressEncryptFileListTestCase(unittest.TestCase):
    """
    Class for testing compress_encrypt_file_list() method from GnupgManager class
    """

    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_compress_encrypt_file_list_path_not_exists(self, mock_gpg, mock_manager, mock_os,
                                                        mock_popen, mock_open, mock_logger):
        """
        Test to check the raise of exception if path doesn't exist
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = False
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message,
                             "Source directory '{}' does not exist to encrypt.".
                             format(MOCK_SOURCE_DIR))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_compress_encrypt_file_list_path_is_not_dir(self, mock_gpg, mock_manager, mock_os,
                                                        mock_popen, mock_open, mock_logger):
        """
        Test to check the raise of exception if path is not a directory
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message,
                             "Informed path '{}' is not a directory.".format(MOCK_SOURCE_DIR))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_compress_encrypt_file_list_out_path_not_exist(self, mock_gpg, mock_manager, mock_os,
                                                           mock_popen, mock_open, mock_logger):
        """
        Test to check the raise of exception if output path is not a directory
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.isdir.return_value = True
        mock_os.path.exists.side_effect = [True, False]
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message,
                             "Output directory '{}' does not exist to encrypt.".
                             format(MOCK_SOURCE_DIR))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'ThreadPool')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_compress_encrypt_file_list_return_value(self, mock_gpg, mock_manager, mock_pool,
                                                     mock_os, mock_popen, mock_open, mock_logger):
        """
        Test to check the return value

        Note: mock_pool is needed due to method's specific logic
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.isdir.return_value = True
        mock_os.path.exists.return_value = True
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            self.assertTrue(gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR,
                                                                     MOCK_OUTPUT_PATH))


class GnupgManagerDecryptFileTestCase(unittest.TestCase):
    """
    Class for testing decrypt_file() method from GnupgManager class
    """

    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_empty_file_path(self, mock_gpg, mock_manager, mock_popen, mock_open,
                                          mock_logger):
        """
        Test to check the raise of exception if file_path is empty
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_file('')

            self.assertEqual(cex.exception.message, "An empty file path was provided.")

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_wrong_suffix(self, mock_gpg, mock_manager, mock_popen, mock_open,
                                       mock_logger):
        """
        Test to check the raise of exception if gpg_suffix is invalid
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_file(MOCK_OUTPUT_PATH)

            self.assertEqual(cex.exception.message, "Not a valid GPG encrypted file '{}'.".
                             format(MOCK_OUTPUT_PATH))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_path_not_exists(self, mock_gpg, mock_manager, mock_os, mock_popen,
                                          mock_open, mock_logger):
        """
        Test to check the raise of exception if encrypted_file_path does not exist
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = False
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_file(MOCK_ENCRYPTED_FILE)

            self.assertEqual(cex.exception.message, "Informed file does not exist '{}'.".
                             format(MOCK_ENCRYPTED_FILE))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_path_is_dir(self, mock_gpg, mock_manager, mock_os, mock_popen,
                                      mock_open, mock_logger):
        """
        Test to check the raise of exception if encrypted_file_path is a directory

        Note: mock_open parameter is needed for successful execution of validate_encryption_key()
        when the instance of GnupgManager is being created
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = True
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_file(MOCK_ENCRYPTED_FILE)

            self.assertEqual(cex.exception.message, "Informed path is a directory '{}'.".
                             format(MOCK_ENCRYPTED_FILE))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_log(self, mock_gpg, mock_manager, mock_os, mock_open, mock_popen,
                              mock_logger):
        """
        Test to check the log if encryption has started
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        calls = [mock.call("Decrypting file {}.".format(MOCK_ENCRYPTED_FILE))]

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            gnupg_manager.decrypt_file(MOCK_ENCRYPTED_FILE)
            gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_failure(self, mock_gpg, mock_manager, mock_os, mock_open, mock_popen,
                                  mock_logger):
        """
        Test to check the raise of exception if decryption has failed
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_popen.return_value.wait.return_value = 1
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_file(MOCK_ENCRYPTED_FILE)

            self.assertEqual(cex.exception.message,
                             "Decryption of file '{}' could not be completed.".
                             format(MOCK_ENCRYPTED_FILE))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_file_return_value(self, mock_gpg, mock_manager, mock_os, mock_open, mock_popen,
                                       mock_logger):
        """
        Test to check the return value
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            self.assertEqual(type(gnupg_manager.decrypt_file(MOCK_ENCRYPTED_FILE)), str)


class GnupgManagerDecryptDecompressTestCase(unittest.TestCase):
    """
    Class for testing decrypt_decompress_file() method from GnupgManager class
    """

    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_decompress_log_time_logs(self, mock_gpg, mock_manager, mock_os, mock_popen,
                                              mock_open, mock_logger):
        """
        Test to check the log_time logs
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with mock.patch('backup.utils.os') as mocked_os:
                mocked_os.path.exists.return_value = True

                gnupg_manager.decrypt_decompress_file(MOCK_ENCRYPTED_FILE)

                first_log = gnupg_manager.logger.log_time.mock_calls[0][1][0]
                second_log = gnupg_manager.logger.log_time.mock_calls[1][1][0]

                self.assertRegexpMatches(first_log, "Elapsed time to decrypt file '{}'".
                                         format(MOCK_ENCRYPTED_FILE))

                self.assertRegexpMatches(second_log, "Elapsed time to decompress file '{}'".
                                         format(MOCK_DECRYPTED_FILE))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_decompress_info_logs(self, mock_gpg, mock_manager, mock_os, mock_popen,
                                          mock_open, mock_logger):
        """
        Test to check the info logs
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        calls = [mock.call("Decompressing file {}.".format(MOCK_DECRYPTED_FILE))]

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with mock.patch('backup.utils.os') as mocked_os:
                mocked_os.path.exists.return_value = True

                gnupg_manager.decrypt_decompress_file(MOCK_ENCRYPTED_FILE)
                gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_decompress_return_value(self, mock_gpg, mock_manager, mock_os, mock_popen,
                                             mock_open, mock_logger):
        """
        Test to check the return value
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with mock.patch('backup.utils.os') as mocked_os:
                mocked_os.path.exists.return_value = True

                self.assertEqual(type(gnupg_manager.decrypt_decompress_file(MOCK_ENCRYPTED_FILE)),
                                 list)


class GnupgManagerDecryptDecompressFileListTestCase(unittest.TestCase):
    """
    Class for testing decrypt_decompress_file_list() method from GnupgManager class
    """

    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_decompress_file_list_path_not_exists(self, mock_gpg, mock_manager, mock_os,
                                                          mock_popen, mock_open, mock_logger):
        """
        Test to check the raise of exception if source_dir path does not exist
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = False
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_decompress_file_list(MOCK_SOURCE_DIR)

            self.assertEqual(cex.exception.message,
                             "Source directory '{}' does not exist to encrypt.".
                             format(MOCK_SOURCE_DIR))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_decrypt_decompress_file_list_path_is_not_dir(self, mock_gpg, mock_manager, mock_os,
                                                          mock_popen, mock_open, mock_logger):
        """
        Test to check the raise of exception if source_dir path does not exist
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            with self.assertRaises(Exception) as cex:
                gnupg_manager.decrypt_decompress_file_list(MOCK_SOURCE_DIR)

            self.assertEqual(cex.exception.message,
                             "Informed path '{}' is not a directory.".format(MOCK_SOURCE_DIR))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'ThreadPool')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_compress_encrypt_file_list_return_value(self, mock_gpg, mock_manager, mock_pool,
                                                     mock_os, mock_popen, mock_open, mock_logger):
        """
        Test to check the raise of exception if output path is not a directory

        Note: mock_pool is needed due to method's specific logic
        """
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_os.path.isdir.return_value = True
        mock_os.path.exists.return_value = True
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            self.assertTrue(gnupg_manager.decrypt_decompress_file_list(MOCK_SOURCE_DIR))


class GnupgManagerOnFileProcessedTestCase(unittest.TestCase):
    """
    Class for testing decompress_decrypt_file_list() method from GnupgManager class
    """

    @classmethod
    def setUpClass(cls):
        cls.gpg_user_name = 'user_name'
        cls.gpg_user_email = 'user_email'
        cls.gpg_cmd = 'gpg'

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'ThreadOutputIndex')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_on_file_processed_error_message(self, mock_gpg, mock_manager, mock_open, mock_popen,
                                             mock_index, mock_logger):
        """
        Test to check the return value if error_message is not empty
        """
        mock_thread_output = ['mock1', 'mock2']
        mock_index.TH_ERROR.value = 1
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            self.assertIsNone(gnupg_manager.on_file_processed(mock_thread_output, []))

    @mock.patch(MOCK_PACKAGE + 'CustomLogger')
    @mock.patch(MOCK_PACKAGE + 'ThreadOutputIndex')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open', create=True)
    @mock.patch(MOCK_PACKAGE + 'GnupgManager')
    @mock.patch(MOCK_PACKAGE + 'GPG')
    def test_on_file_processed_no_error_message(self, mock_gpg, mock_manager, mock_open, mock_popen,
                                                mock_index, mock_logger):
        """
        Test to check the return value if error_message is not empty
        """
        mock_thread_output = [None, 'mock2']
        mock_index.TH_ERROR.value = 1
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_manager.gpg_handler.side_effect = mock_gpg

        gnupg_manager = GnupgManager(self.gpg_user_name, self.gpg_user_email, mock_logger)

        with open(os.devnull, "w") as devnull:
            mock_popen.stdout.return_value = devnull

            self.assertIsNone(gnupg_manager.on_file_processed(mock_thread_output, []))
