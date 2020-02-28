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
from subprocess import Popen

from gnupg import GPG
from logger import CustomLogger
from performance import PerformanceTimeIndex
from thread_pool import ThreadPool, ThreadOutputIndex, MAX_THREAD
from utils import compress_file, decompress_file, get_home_dir, remove_path, timeit, GPG_SUFFIX, \
    PLATFORM_NAME

GPG_KEY_PATH = os.path.join(get_home_dir(), ".gnupg")

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]


class GnupgManager:
    """Class used to store sourced information about gnupg current settings."""

    def __init__(self, gpg_user_name, gpg_user_email, logger, gpg_key_path=GPG_KEY_PATH):
        """
        Initialize GPG Manager class.

        Configure additional parameters:

        gpg_cmd:        gpg command according to the platform.
        gpg_handler:    gpg python object.

        :param gpg_user_name: gpg configured user name.
        :param gpg_user_email: gpg configured email.
        :param logger:  logger object.
        :param gpg_key_path: gpg key path, usually is ~/.gnupg.
        """
        self.gpg_user_name = gpg_user_name
        self.gpg_user_email = gpg_user_email
        self.gpg_key_path = gpg_key_path
        self.gpg_file_extension = ".{}".format(GPG_SUFFIX)

        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

        if 'linux' in PLATFORM_NAME:
            self.gpg_cmd = 'gpg'
            self.gpg_handler = GPG(homedir=self.gpg_key_path)
        elif 'sun' in PLATFORM_NAME:
            self.gpg_cmd = 'gpg2'
            self.gpg_handler = GPG(self.gpg_cmd, gnupghome=self.gpg_key_path)
        else:
            raise Exception("Platform not supported for GNUPG encryption tool.")

        self.validate_encryption_key()

    def validate_encryption_key(self):
        """
        Check the system for the encryption key.

        Creates a new key if there is no one for the informed user.

        If an error occurs, an Exception is raised with the details of the problem.
        """
        self.logger.info("Validating GPG encryption settings.")
        with open(os.devnull, "w") as devnull:
            ret_code = Popen([self.gpg_cmd, "--list-keys", self.gpg_user_email],
                             stdout=devnull, stderr=devnull).wait()
            if ret_code == 0:
                return

        self.logger.info("Backup key does not exist yet. Creating a new one.")

        if self.gpg_handler is not None:
            self.gpg_handler.gen_key(self.gpg_handler.gen_key_input(key_type='RSA',
                                                                    key_length=1024,
                                                                    name_real=self.gpg_user_name,
                                                                    name_email=self.gpg_user_email))
        else:
            raise Exception("GPG program not installed properly in this system.")

    @timeit
    def encrypt_file(self, file_path, output_path, **kwargs):
        """
        Encrypt a file using the gpg strategy.

        The resulting file name will be like <file_path>.gpg.

        For example,
            given a file_path = '~/Documents/file.tgz',

        The resulting encrypted file will be like:
            '~/Documents/file.tgz.gpg'

        If an error occurs, an Exception is raised with the details of the problem.

        :param file_path:   file path to be encrypted.
        :param output_path: path where the encrypted file will be stored.

        :return encrypted file name.
        """
        if not file_path.strip() or not output_path.strip():
            raise Exception("An empty file path or output file path was provided.")

        if not os.path.exists(file_path):
            raise Exception("Informed file does not exist '{}'.".format(file_path))

        self.logger.info("Encrypting file '{}'".format(file_path))

        with open(os.devnull, "w") as devnull:
            output = "{}{}".format(os.path.join(output_path, os.path.basename(file_path)),
                                   self.gpg_file_extension)
            ret_code = Popen([self.gpg_cmd, "--output", output, "-r", self.gpg_user_email,
                              "--cipher-algo", "AES256", "--compress-algo", "none",
                              "--encrypt", file_path], stdout=devnull, stderr=devnull).wait()
            if ret_code != 0:
                raise Exception("Encryption of file {} could not be completed."
                                .format(file_path))
        return output

    def compress_encrypt_file(self, file_path, output_path):
        """
        Compress and encrypt a file using gpg and gz strategies.

        If an error occurs, an Exception is raised with the details of the problem.

        :param file_path:   file path to be encrypted and compressed.
        :param output_path: path where the encrypted and compressed file will be stored.

        :return list with time to encrypt and compress file.
        """
        self.logger.info("Compressing file {}.".format(file_path))

        file_compression_time = []
        compressed_file_path = compress_file(file_path, output_path,
                                             get_elapsed_time=file_compression_time)

        self.logger.log_time("Elapsed time to compress file '{}'".format(file_path),
                             file_compression_time[0])

        file_encryption_time = []
        self.encrypt_file(compressed_file_path, output_path, get_elapsed_time=file_encryption_time)

        self.logger.log_time("Elapsed time to encrypt file '{}'".format(compressed_file_path),
                             file_encryption_time[0])

        if not remove_path(compressed_file_path):
            raise Exception("Unable to remove compressed file '{}'.".format(compressed_file_path))

        process_time = [0.0, 0.0]
        process_time[PerformanceTimeIndex.COMPRESS_TIME.value - 1] = file_compression_time[0]
        process_time[PerformanceTimeIndex.ENCRYPT_TIME.value - 1] = file_encryption_time[0]

        return process_time

    @timeit
    def compress_encrypt_file_list(self, source_dir, output_path, number_threads=MAX_THREAD,
                                   **kwargs):
        """
        Compress and encrypt a list of files in parallel using a thread pool.

        Using thread pool the callback is protected with mutex.

        Raise an exception if the input is invalid.

        :param source_dir: folder where the files to be encrypted are located.
        :param output_path: folder to store encrypted files.
        :param number_threads: number of threads to process the source dir.

        :return true if success.
        """
        if not os.path.exists(source_dir):
            raise Exception("Source directory '{}' does not exist to encrypt.".format(source_dir))

        if not os.path.isdir(source_dir):
            raise Exception("Informed path '{}' is not a directory.".format(source_dir))

        if not os.path.exists(output_path):
            raise Exception("Output directory '{}' does not exist to encrypt.".format(source_dir))

        job_error_list = []
        job_thread_pool = ThreadPool(self.logger, number_threads, GnupgManager.on_file_processed,
                                     job_error_list)

        for file_name in os.listdir(source_dir):
            source_file_path = os.path.join(source_dir, file_name)

            job_thread_pool.create_thread("{}-Thread".format(file_name), self.compress_encrypt_file,
                                          source_file_path, output_path)
        job_thread_pool.start_pool()

        if job_error_list:
            raise Exception("The following errors happened during the decryption of files in the "
                            "directory '{}': {}".format(source_dir, job_error_list))
        return True

    @timeit
    def decrypt_file(self, encrypted_file_path, remove_encrypted=False, **kwargs):
        """
        Decrypt a file using the gpg strategy.

        If an error occurs, an Exception is raised with the details of the problem.

        :param encrypted_file_path: file to be decrypted in the format <file_name>.gpg.
        :param remove_encrypted:    flag to inform if the encrypted file should be deleted after
        decryption.

        :return decrypted file name.
        """
        if not encrypted_file_path.strip():
            raise Exception("An empty file path was provided.")

        if self.gpg_file_extension not in encrypted_file_path:
            raise Exception("Not a valid GPG encrypted file '{}'.".format(encrypted_file_path))

        if not os.path.exists(encrypted_file_path):
            raise Exception("Informed file does not exist '{}'.".format(encrypted_file_path))

        if os.path.isdir(encrypted_file_path):
            raise Exception("Informed path is a directory '{}'.".format(encrypted_file_path))

        self.logger.info("Decrypting file {}.".format(encrypted_file_path))

        dec_filename = encrypted_file_path[0:len(encrypted_file_path) - len(self.gpg_file_extension)]

        with open(os.devnull, "w") as devnull:
            ret_code = Popen([self.gpg_cmd, "--output", dec_filename, "--decrypt",
                              encrypted_file_path], stdout=devnull, stderr=devnull).wait()
            if ret_code != 0:
                raise Exception("Decryption of file '{}' could not be completed."
                                .format(encrypted_file_path))

        if remove_encrypted:
            remove_path(encrypted_file_path)

        return dec_filename

    def decrypt_decompress_file(self, file_path):
        """
        Decrypt and decompress a file using gpg and gz strategies.

        If an error occurs, an Exception is raised with the details of the problem.

        :param file_path:   file path to be decompressed and decrypted.

        :return list with time to decrypt and decompress.
        """
        file_decryption_time = []
        decrypted_file_name = self.decrypt_file(file_path, True,
                                                get_elapsed_time=file_decryption_time)

        self.logger.log_time("Elapsed time to decrypt file '{}'".format(file_path),
                             file_decryption_time[0])

        self.logger.info("Decompressing file {}.".format(decrypted_file_name))

        file_decompression_time = []
        decompress_file(decrypted_file_name, os.path.dirname(decrypted_file_name), True,
                        get_elapsed_time=file_decompression_time)

        self.logger.log_time("Elapsed time to decompress file '{}'".format(decrypted_file_name),
                             file_decompression_time[0])

        process_time = [0.0, 0.0]
        process_time[PerformanceTimeIndex.COMPRESS_TIME.value - 1] = file_decompression_time[0]
        process_time[PerformanceTimeIndex.ENCRYPT_TIME.value - 1] = file_decryption_time[0]

        return process_time

    @timeit
    def decrypt_decompress_file_list(self, source_dir, number_threads=MAX_THREAD, **kwargs):
        """
        Decrypt and decompress a list of files in parallel using a thread pool.

        Using thread pool the callback is protected with mutex.

        Raise an exception if an error happened during the process.

        :param source_dir: folder where the files to be encrypted are located.
        :param number_threads: number of threads to process the source dir.

        :return: true if success.
        """
        if not os.path.exists(source_dir):
            raise Exception("Source directory '{}' does not exist to encrypt.".format(source_dir))

        if not os.path.isdir(source_dir):
            raise Exception("Informed path '{}' is not a directory.".format(source_dir))

        job_error_list = []
        decryption_thread_pool = ThreadPool(self.logger, number_threads,
                                            GnupgManager.on_file_processed, job_error_list)

        for file_name in os.listdir(source_dir):
            source_file_path = os.path.join(source_dir, file_name)

            decryption_thread_pool.create_thread("{}-Thread".format(file_name),
                                                 self.decrypt_decompress_file, source_file_path)
        decryption_thread_pool.start_pool()

        if job_error_list:
            raise Exception("The following errors happened during the decryption of files in the "
                            "directory '{}': {}".format(source_dir, job_error_list))
        return True

    @staticmethod
    def on_file_processed(thread_output, job_error_list):
        """
        Callback function to be executed after a successful file encryption/decryption.

        :param thread_output: thread output after processing the file [thread name, elapsed time].
        :param job_error_list: list to keep track of each thread error.
        """
        error_message = thread_output[ThreadOutputIndex.TH_ERROR.value - 1]
        if error_message is not None:
            job_error_list.append(error_message)

    def __str__(self):
        """Represent GnupgManager object as string."""
        return "({}, {}, {})".format(self.gpg_user_name, self.gpg_user_email, self.gpg_key_path)

    def __repr__(self):
        """Represent GnupgManager object."""
        return self.__str__()
