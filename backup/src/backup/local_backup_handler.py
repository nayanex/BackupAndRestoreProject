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
import time
import dill
import multiprocessing as mp
from threading import Lock

from logger import CustomLogger
from performance import collect_performance_data
from utils import check_remote_path_exists, compress_file, create_path, create_remote_dir, \
    remove_path, transfer_file, VolumeOutputKeys

MIN_BKP_LOCAL = 1

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

SUCCESS_FLAG_FILE = "BACKUP_OK"


def unwrapper_process_backup_volume(backup_handler_obj, volume_path, volume_name,
                                    temp_volume_folder_path, remote_backup_path):
    """
    Un-wrapper function.

    Reloads a LocalBackupHandler object when using Multiprocessing map function to execute the
    backup of volumes in parallel.

    Raise an exception if the arguments are not as expected.

    :param backup_handler_obj: LocalBackupHandler object.
    :param volume_path: volume path to be processed.
    :param volume_name: volume name.
    :param temp_volume_folder_path: folder to store temporary files related to this volume.
    :param remote_backup_path: backup location on offsite.

    :return: tuple (volume_name, volume_output, remote_backup_path), when the process
    executed normally.
    """
    loaded_backup_handler_object = dill.loads(backup_handler_obj)
    if not isinstance(loaded_backup_handler_object, LocalBackupHandler):
        raise Exception("Could not unwrap local backup handler object.")

    volume_output = loaded_backup_handler_object.process_volume(volume_path,
                                                                temp_volume_folder_path)

    return volume_name, volume_output, remote_backup_path


class LocalBackupHandler:
    """
    Class responsible for executing the backup upload feature for a customer.

    This task is optimized by multi-threading to handle each volume for each backup.

    After the backup is complete, a clean up function might be called to perform housekeeping on
    the local server.
    """

    def __init__(self, offsite_config, customer_conf, gpg_manager, number_process,
                 number_threads, notification_handler, logger):
        """
        Initialize Local Backup Handler object.

        :param offsite_config: details of the offsite server.
        :param customer_conf: details of the local customer server.
        :param gpg_manager: gpg manager object to handle encryption and decryption.
        :param number_process: maximum number of running process at a time.
        :param number_threads: maximum number of running threads at a time.
        :param logger: logger object.
        """
        self.customer_conf = customer_conf
        self.offsite_config = offsite_config
        self.gpg_manager = gpg_manager
        self.number_process = number_process
        self.number_threads = number_threads
        self.notification_handler = notification_handler

        self.backup_output_dic_lock = Lock()
        self.backup_output_dic = {}

        self.remote_root_path = os.path.join(self.offsite_config.full_path, self.customer_conf.name)
        self.temp_customer_root_path = os.path.join(self.offsite_config.temp_path,
                                                    self.customer_conf.name)

        logger_script_reference = "{}_{}".format(SCRIPT_FILE, customer_conf.name)

        self.logger = CustomLogger(logger_script_reference, logger.log_root_path,
                                   logger.log_file_name, logger.log_level)

    def process_backup_list(self):
        """
        Process a list of valid backups for the customer.

        Validates remote and local temporary paths before proceed.

        Processing includes - compression, encryption and uploading tasks.

        If an error occurs before processing the backups, it raises an exception with the details.

        :return true if backup list was processed.
        """
        if not check_remote_path_exists(self.offsite_config.host, self.remote_root_path):
            if not create_remote_dir(self.offsite_config.host, self.remote_root_path):
                raise Exception("Remote directory '{}' could not be created for customer {"
                                "}.".format(self.remote_root_path, self.customer_conf.name))

        local_backup_list = self.get_local_backup_list()
        if local_backup_list is None or not local_backup_list:
            raise Exception("No backup to be processed for the customer {}.".format(
                self.customer_conf.name))

        if not create_path(self.temp_customer_root_path):
            raise Exception("Temporary folder '{}' could not be create for customer {}.".format(
                self.temp_customer_root_path, self.customer_conf.name))

        self.logger.log_info("Doing backup of: {}, directories: {}".format(
            self.customer_conf.name, local_backup_list))

        for current_backup_folder_name in local_backup_list:
            remote_current_backup_path = os.path.join(self.remote_root_path,
                                                      current_backup_folder_name)

            if check_remote_path_exists(self.offsite_config.host, remote_current_backup_path):
                self.logger.warning("Customer {} has a backup with the same name {}. Nothing to "
                                    "do.".format(self.customer_conf.name,
                                                 current_backup_folder_name))
                continue

            if not create_remote_dir(self.offsite_config.host, remote_current_backup_path):
                self.logger.error("Remote directory '{}' could not be created for customer {"
                                  "}".format(remote_current_backup_path, self.customer_conf.name))
                continue

            temp_current_backup_path = os.path.join(self.temp_customer_root_path,
                                                    current_backup_folder_name)

            if not create_path(temp_current_backup_path):
                self.logger.error("Temporary folder '{}' could not be create for backup {"
                                  "}.".format(temp_current_backup_path, current_backup_folder_name))
                continue

            self.process_backup(current_backup_folder_name, temp_current_backup_path,
                                remote_current_backup_path)

        return True

    @collect_performance_data
    def process_backup(self, backup_folder_name, temp_backup_path, remote_backup_path):
        """
        Compress, encrypt and transfer volumes of the current backup to the off-site server.

        If an error occurs, an Exception is raised with the details of the problem.

        :param backup_folder_name: backup directory name.
        :param temp_backup_path: backup temporary directory path.
        :param remote_backup_path: remote backup path.

        :return: backup id, backup output dictionary. Used by annotated method.
        """
        self.backup_output_dic = {}

        local_backup_path = os.path.join(self.customer_conf.backup_path, backup_folder_name)

        time_start = time.time()

        process_pool = mp.Pool(self.number_process)

        for volume_name in os.listdir(local_backup_path):
            volume_path = os.path.join(local_backup_path, volume_name)

            if os.path.isfile(volume_path):
                self.logger.warning("Volume's path is expected to contain just folders. A file '{"
                                    "}' was found.".format(volume_path))
                continue

            temp_volume_folder_path = os.path.join(temp_backup_path, volume_name)

            process_pool.apply_async(unwrapper_process_backup_volume, (dill.dumps(self),
                                                                       volume_path,
                                                                       volume_name,
                                                                       temp_volume_folder_path,
                                                                       remote_backup_path),
                                     callback=self.on_volume_ready)

        process_pool.close()
        process_pool.join()
        time_end = time.time()

        # it is not possible collect the performance data with timeit in this case.
        total_backup_processing_time = time_end - time_start
        volume_error_list = self.get_backup_output_errors(self.backup_output_dic)

        if volume_error_list:
            raise Exception("Failed to process backup '{}' for customer {}, due to: {}".format(
                backup_folder_name, self.customer_conf.name, volume_error_list))

        bur_id = "{}_{}".format(self.customer_conf.name, backup_folder_name)

        return bur_id, self.backup_output_dic, total_backup_processing_time

    def on_volume_ready(self, unwrapper_process_backup_volume_return_tuple):
        """
        Callback returned after a volume is processed. If no error happened with this volume,
        it starts transferring it to offsite.

        Populate the backup dictionary with details of the volume's processing.

        :param: unwrapper_process_backup_volume_return_tuple: apply_async callback argument list.
        Expected to have the return values of the function unwrapper_process_backup_volume.
        """
        volume_name = unwrapper_process_backup_volume_return_tuple[0]
        volume_output = unwrapper_process_backup_volume_return_tuple[1]
        remote_backup_path = unwrapper_process_backup_volume_return_tuple[2]

        volume_output[VolumeOutputKeys.rsync_output.name] = None
        volume_output[VolumeOutputKeys.transfer_time.name] = None

        if volume_output[VolumeOutputKeys.status.name]:
            compressed_volume_path = volume_output[VolumeOutputKeys.volume_path.name]

            try:
                rsync_output, transfer_time = self.transfer_backup_volume_to_offsite(
                    compressed_volume_path, remote_backup_path)

                volume_output[VolumeOutputKeys.rsync_output.name] = rsync_output
                volume_output[VolumeOutputKeys.transfer_time.name] = transfer_time

            except Exception as transfer_exception:
                volume_output[VolumeOutputKeys.status.name] = False
                volume_output[VolumeOutputKeys.output.name] = transfer_exception.message

        with self.backup_output_dic_lock:
            self.backup_output_dic[volume_name] = volume_output

    def get_backup_output_errors(self, backup_output_per_volume_dic):
        """
        Validate the processed volumes of a single backup.

        The validation is done by getting all the returned error messages for that volume.

        :param backup_output_per_volume_dic: result of the backup processing.
        :return: list with eventual errors from backup_output
        """
        failed_volume_error_message_list = []

        for key in backup_output_per_volume_dic.keys():
            if not backup_output_per_volume_dic[key][VolumeOutputKeys.status.name]:
                error_message = backup_output_per_volume_dic[key][
                    VolumeOutputKeys.output.name]
                failed_volume_error_message_list.append(error_message)
                self.logger.error(error_message)

        return failed_volume_error_message_list

    def process_volume(self, volume_path, tmp_volume_path):
        """
        Process a single volume folder by encrypting each file and compressing the folder in the
        end.

        :param volume_path:       path of the volume.
        :param tmp_volume_path:   local temporary path to store auxiliary files.
        """

        self.logger.log_info("Process_id: {}, processing volume: {}, for: {}".format(
            os.getpid(), volume_path, self.customer_conf.name))

        volume_output_dic = {}

        volume_output_dic[VolumeOutputKeys.volume_path.name] = ""
        volume_output_dic[VolumeOutputKeys.processing_time.name] = 0.0
        volume_output_dic[VolumeOutputKeys.tar_time.name] = 0.0
        volume_output_dic[VolumeOutputKeys.output.name] = ""
        volume_output_dic[VolumeOutputKeys.status.name] = False

        try:
            if not create_path(tmp_volume_path):
                raise Exception("Temporary folder could not be created for customer {}."
                                .format(self.customer_conf.name))

            self.logger.info("Compressing and encrypting files from volume '{}'.".format(
                volume_path))

            total_volume_process_time = []
            self.gpg_manager.compress_encrypt_file_list(volume_path, tmp_volume_path,
                                                        self.number_threads,
                                                        get_elapsed_time=total_volume_process_time)

            self.logger.log_time("Elapsed time to process the volume '{}'".format(
                volume_path), total_volume_process_time[0])

            self.logger.info("Archiving volume directory '{}' for customer {}.".format(
                tmp_volume_path, self.customer_conf.name))

            volume_tar_time = []
            compressed_volume_path = compress_file(tmp_volume_path, None, "w",
                                                   get_elapsed_time=volume_tar_time)

            self.logger.log_time("Elapsed time to archive the volume '{}'".format(tmp_volume_path),
                                 volume_tar_time[0])

            if not remove_path(tmp_volume_path):
                raise Exception("Error while deleting temporary path '{}' from customer {}."
                                .format(tmp_volume_path, self.customer_conf.name))

            volume_output_dic[VolumeOutputKeys.volume_path.name] = compressed_volume_path
            volume_output_dic[VolumeOutputKeys.processing_time.name] = total_volume_process_time[0]
            volume_output_dic[VolumeOutputKeys.tar_time.name] = volume_tar_time[0]
            volume_output_dic[VolumeOutputKeys.status.name] = True

        except Exception as e:
            volume_output_dic[VolumeOutputKeys.output.name] = \
                "Error while processing volume {} from customer {} due to: {}.".format(
                    volume_path, self.customer_conf.name, e[0])

        return volume_output_dic

    def transfer_backup_volume_to_offsite(self, tmp_customer_volume_path, remote_dir):
        """
        Transfer a backup already compressed and encrypted to the offsite.

        Raise an exception when an error occurs.

        :param tmp_customer_volume_path: temporary folder where the backup volumes are stored.
        :param remote_dir:               remote location to send the backup.

        :return: elapsed time to transfer the backup.
        """
        try:
            target_dir = "{}:{}".format(self.offsite_config.host, remote_dir)

            self.logger.info("Transferring volume '{}' to '{}'".format(tmp_customer_volume_path,
                                                                       target_dir))

            transfer_time = []
            rsync_output = transfer_file(tmp_customer_volume_path, target_dir,
                                         get_elapsed_time=transfer_time)

            self.logger.log_time("Elapsed time to transfer volume '{}'".format(
                tmp_customer_volume_path), transfer_time[0])

        except Exception as e:
            backup_name = os.path.basename(tmp_customer_volume_path)

            raise Exception("Error while transferring volume {} for customer {} to offsite, due "
                            "to {}.".format(backup_name, self.customer_conf.name, e.message))
        finally:
            if not remove_path(tmp_customer_volume_path):
                raise Exception("Error to delete temporary path '{}' from customer {}."
                                .format(tmp_customer_volume_path, self.customer_conf.name))

        return rsync_output, transfer_time[0]

    def clean_local_backup(self, customer_backup_path):
        """
        Clean the local customer's folder, keeping at least MAX_BKP_NFS stored.

        :param customer_backup_path:  path to the customer's backup folder in NFS.

        :return tuple (true, message) if the backup path was cleaned with no errors.
                tuple (false, message), otherwise.
        """
        self.logger.log_info("Performing the clean up on NFS path '{}'.".format(
            self.customer_conf.backup_path))

        number_backup_dir = 0
        for backup_dir in os.listdir(os.path.normpath(self.customer_conf.backup_path)):
            if os.path.isfile(os.path.join(self.customer_conf.backup_path, backup_dir)):
                continue
            number_backup_dir += 1

        self.logger.info("There are currently {} backups in the folder '{}'.".format(
            number_backup_dir, self.customer_conf.backup_path))

        if number_backup_dir > MIN_BKP_LOCAL:
            self.logger.info("Removing backup '{}' from NFS server.".format(customer_backup_path))

            if not remove_path(customer_backup_path):
                return False, "Error while deleting folder '{}' from NFS server." \
                    .format(customer_backup_path)
        else:
            return False, "Backup NOT removed '{}'. Just {} backup found." \
                .format(customer_backup_path, MIN_BKP_LOCAL)

        return True, "Backup removed successfully '{}'.".format(customer_backup_path)

    def get_local_backup_list(self):
        """
        Return a list of recent backup folders after validation against success flag.

        Do not return the most recent valid backup when there are more than
        MIN_BKP_LOCAL in the system.

        :return: a list of backup folders to be uploaded, when it exists,
                 None when an error happens.
        """
        source_dir = self.customer_conf.backup_path

        if not os.path.exists(source_dir):
            self.logger.error("Invalid backup source path '{}'.".format(source_dir))
            return None

        self.logger.info("Getting the list of valid backups from '{}'.".format(source_dir))

        valid_dir_list = []
        for backup_folder in os.listdir(source_dir):
            backup_path = os.path.join(source_dir, backup_folder)

            if os.path.isfile(backup_path):
                self.logger.warning("Found a file '{}' inside backup list folder.".format(
                    backup_path))
                continue

            if not os.path.exists(os.path.join(backup_path, SUCCESS_FLAG_FILE)):
                self.logger.warning("Backup '{}' does not have a success flag. Skipping this "
                                    "one.".format(backup_path))
                continue

            valid_dir_list.append(backup_folder)

        valid_dir_list.sort(key=lambda s: os.path.getmtime(os.path.join(source_dir, s)),
                            reverse=True)

        if len(valid_dir_list) > MIN_BKP_LOCAL:
            del valid_dir_list[0]

        print MIN_BKP_LOCAL
        return valid_dir_list
