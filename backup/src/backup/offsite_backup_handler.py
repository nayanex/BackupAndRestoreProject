import os
import dill
import collections
import multiprocessing as mp

from logger import CustomLogger
from performance import VolumeOutputKeys
from local_backup_handler import LocalBackupHandler
from utils import BLOCK_SIZE, check_offiste_disk_space, check_onsite_disk_space_restore, \
    create_path, decompress_file, find_elem_dic, get_elem_dic, get_free_disk_space, \
    get_onsite_backups_size, popen_communicate, prepare_send_notification_email, remove_path, \
    remove_remote_dir, split_folder_list, sufficient_onsite_disk_space, timeit, transfer_file, \
    validate_volume_level_metadata

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

MAX_BKP_OFFSITE = 3


def unwrapper_restore_volume(offsite_backup_handler_obj, volume_name, local_backup_path):
    """
    Un-wrapper function.

    Reload an OffsiteBackupHandler object when using Multiprocessing map function to restore
    backups in parallel.

    :param offsite_backup_handler_obj: OffsiteBackupHandler object.
    :param volume_name: volume name.
    :param local_backup_path: path where the restored backup should be stored.

    :return: tuple (volume name, volume output), when the process executed normally.
             None, otherwise.
    """
    loaded_offsite_backup_handler_object = dill.loads(offsite_backup_handler_obj)
    if not isinstance(loaded_offsite_backup_handler_object, OffsiteBackupHandler):
        return None

    volume_output = loaded_offsite_backup_handler_object.restore_volume(volume_name,
                                                                        local_backup_path)

    return volume_name, volume_output


class OffsiteBackupHandler:
    """
    Responsible for handling the BUR features.

    Upload or download backup, as well as remote clean up for a set of customers.
    """

    def __init__(self, gpg_manager, offsite_config, enmaas_config_dic,
                 number_threads, number_processors, notification_handler, logger):
        """
        Initialize Offsite Backup Handler object.

        :param gpg_manager: gpg manager object to handle decrypt/encrypt tasks.
        :param offsite_config: information about the remote server.
        :param enmaas_config_dic: information list about customers.
        :param number_threads: number of allowed running threads at a time.
        :param number_processors: number of allowed running process at a time.
        :param notification_handler: notification_handler object to notify via email if some
               error occurs while processing a backup
        :param logger: logger object.
        """
        self.gpg_manager = gpg_manager
        self.offsite_config = offsite_config
        self.enmaas_config_dic = enmaas_config_dic

        self.number_threads = number_threads
        self.number_processors = number_processors

        self.notification_handler = notification_handler

        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

        self.single_backup_output_dic = {}

    @timeit
    def execute_restore_backup_from_offsite(self, customer_name, backup_tag, backup_destination,
                                            **kwargs):
        """
        Execute the restoration of the backup based on the input parameters.

        Check if the desired customer exists before calling the restore function.

        :param customer_name:      customer name to retrieve the backup, empty if all backups
                                   should be retrieved.
        :param backup_tag:         backup tag to be retrieved from the off-site location.
        :param backup_destination: path where the backup will be downloaded.

        :return: tuple (true, success message) if the process occurred successfully,
                 tuple (false, error message) otherwise.
        """
        try:
            enmaas_query_config = None
            restored_backup_path = ""
            clean_restored_folder_on_error = True

            if customer_name is not None and customer_name.strip():
                enmaas_query_config = get_elem_dic(self.enmaas_config_dic, customer_name)
                if enmaas_query_config is None:
                    raise Exception("Customer {} not found.".format(customer_name))

            customer_backup_dic = self.get_offsite_backup_dic(enmaas_query_config)

            if backup_tag is None or not backup_tag.strip():
                self.logger.info("Retrieved list of backups per customer: {}".format(
                    customer_backup_dic))

                return True, "Returned list of all backups per customer successfully."

            customer_name, backup_path_to_be_retrieved, backup_destination = \
                self.validate_backup_download_info(customer_backup_dic, backup_tag,
                                                   backup_destination)

            backup_folder_name = os.path.basename(backup_path_to_be_retrieved)
            restored_backup_path = os.path.join(backup_destination, backup_folder_name)

            if os.path.exists(restored_backup_path):
                clean_restored_folder_on_error = False
                raise Exception("A backup with the same tag already exists in '{}' "
                                "folder.".format(restored_backup_path))

            self.download_backup_from_offsite(customer_name, backup_tag,
                                              backup_path_to_be_retrieved, backup_destination,
                                              restored_backup_path)
        except Exception as e:
            error_message = "Error while restoring backup tag {} to destination '{}', " \
                            "due to {}.".format(backup_tag, backup_destination, e[0])

            email_subject = "Could not download backup with tag {} from offsite.".format(backup_tag)
            prepare_send_notification_email(self.notification_handler,
                                            email_subject,
                                            error_message)

            if restored_backup_path.strip() and clean_restored_folder_on_error:
                self.clean_local_backup_path(restored_backup_path, self.logger)

            return False, error_message

        return True, "Backup recovery '{}' to destination '{}' executed successfully.".format(
            backup_path_to_be_retrieved, backup_destination)

    def validate_backup_download_info(self, customer_backup_dic, backup_tag, backup_destination):
        """
        Validate the backup information to retrieve it from the offsite.

        Raise an exception is something gets wrong.

        :param customer_backup_dic: dictionary with backups per customer.
        :param backup_tag:          backup tag to be retrieved from the off-site location.
        :param backup_destination:  path where the backup will be downloaded.

        :return: tuple (customer_name, backup_path to retrieve from offsite, backup_destination)
        if the process occurred successfully.
        """
        customer_name, backup_path_to_be_retrieved = find_elem_dic(customer_backup_dic, backup_tag)

        if not backup_path_to_be_retrieved.strip():
            raise Exception("Backup tag {} not found on off-site.".format(backup_tag))

        if not backup_destination.strip():
            backup_destination = self.enmaas_config_dic[customer_name].backup_path
            self.logger.warning("Backup destination field not informed. Default location '{}' used"
                                .format(backup_destination))
        else:
            backup_destination = os.path.join(backup_destination, customer_name)

        has_sufficient_space_for_restore, log_message = check_onsite_disk_space_restore(
            backup_path_to_be_retrieved, self.offsite_config.host, backup_destination, BLOCK_SIZE)

        if not has_sufficient_space_for_restore:
            raise Exception(log_message)

        self.logger.info(log_message)

        return customer_name, backup_path_to_be_retrieved, backup_destination

    def get_offsite_backup_dic(self, enmaas_config=None):
        """
        Query the off-site server looking for the list of available backups.

        If the customer_name is empty, retrieves the available backup from all customers, otherwise
        it gets just the ones from a particular customer.

        :param enmaas_config: customer object whose backup list should be retrieved, None if all
               customers should be searched.

        :return: map containing the list of available backups in the off-site by customer name.
        """
        remote_root_backup_path = os.path.join(self.offsite_config.path, self.offsite_config.folder)

        enmaas_config_list = self.enmaas_config_dic.values()
        if enmaas_config is not None:
            enmaas_config_list = [enmaas_config]

        self.logger.info("Looking for available backups for customers: {}.".format(
            enmaas_config_list))

        ssh_get_sorted_dir_list = ""
        backup_list_by_customer_dic = collections.OrderedDict()

        for enmaas_config in enmaas_config_list:
            ssh_get_sorted_dir_list += "ls -dt {}/*/\necho END-OF-COMMAND\n" \
                .format(os.path.join(remote_root_backup_path, enmaas_config.name))
            backup_list_by_customer_dic[enmaas_config.name] = []

        stdout, _ = popen_communicate(self.offsite_config.host, ssh_get_sorted_dir_list)

        output_folder_by_customer_list = stdout.split('END-OF-COMMAND')

        customer_idx = 0
        for key in backup_list_by_customer_dic.keys():
            if customer_idx > len(output_folder_by_customer_list):
                break

            backup_list_by_customer_dic[key] = split_folder_list(output_folder_by_customer_list[
                                                                     customer_idx])
            customer_idx += 1

        return backup_list_by_customer_dic

    def download_backup_from_offsite(self, customer_name, backup_tag, backup_path_to_retrieve,
                                     backup_restore_destination, restored_backup_path):
        """
        Download and restore the backup to the destination directory.

        1. Downloads the informed backup given by restore_backup_path to the destination.
        2. Decompress all volumes and delete the compressed files;
        3. Decrypt all files inside the volumes and delete the decrypted files.

        :param customer_name: customer name whose backup is being downloaded.
        :param backup_tag: backup tag to be retrieved.
        :param backup_path_to_retrieve: backup path on remote location to be downloaded.
        :param backup_restore_destination: local backup destination.
        :param restored_backup_path: actual restored backup folder.

        :return: tuple (backup tag, backup output, rsync output, transfer time)
        """
        self.logger.info("Restoring backup '{}' to destination '{}'.".format(
            backup_path_to_retrieve, backup_restore_destination))

        if not create_path(backup_restore_destination):
            raise Exception("Destination folder '{}' could not be created.".format(
                backup_restore_destination))

        source_remote_dir = "{}:{}".format(self.offsite_config.host, backup_path_to_retrieve)

        self.logger.info("Downloading backup '{}'.".format(source_remote_dir))

        transfer_time = []
        rsync_output = transfer_file(source_remote_dir, backup_restore_destination,
                                     get_elapsed_time=transfer_time)

        self.logger.log_time("Elapsed time to download backup with tag {}".format(
            backup_tag), transfer_time[0])

        self.single_backup_output_dic = {}

        process_pool = mp.Pool(self.number_processors)

        for volume_name in os.listdir(restored_backup_path):
            if os.path.isdir(os.path.join(restored_backup_path, volume_name)):
                continue

            process_pool.apply_async(unwrapper_restore_volume, (dill.dumps(self),
                                                                volume_name,
                                                                restored_backup_path),
                                     callback=self.add_volume_job_stats_to_backup_output_dic)

        process_pool.close()
        process_pool.join()

        volume_error_list = self.get_backup_output_errors()

        if len(volume_error_list) > 0:
            raise Exception("Failed to process backup '{}' for customer {}, due to: {}".format(
                backup_restore_destination, customer_name, volume_error_list))

        if not validate_volume_level_metadata(restored_backup_path, self.logger):
            raise Exception("Retrieved backup '{}' could not be validated against "
                            "metadata.".format(restored_backup_path))

        return backup_tag, self.single_backup_output_dic, rsync_output, transfer_time[0]

    def get_backup_output_errors(self):
        """
        Validate the processed volumes of a single backup.

        The validation is done by getting all the returned error messages for that volume.

        :return: list with eventual errors from backup_output
        """
        failed_volume_error_message_list = []

        for key in self.single_backup_output_dic.keys():
            if not self.single_backup_output_dic[key][VolumeOutputKeys.status.name]:
                error_message = self.single_backup_output_dic[key][VolumeOutputKeys.output.name]
                failed_volume_error_message_list.append(error_message)
                self.logger.error(error_message)

        return failed_volume_error_message_list

    def add_volume_job_stats_to_backup_output_dic(self, *args):
        """
        Update the backup output dictionary with the results of volume job.

        :param: *args: return of self.process_volume.
        """
        volume_name = args[0][0]
        volume_stats = args[0][1]

        self.single_backup_output_dic[volume_name] = volume_stats

    @staticmethod
    def clean_local_backup_path(local_backup_path, logger):
        """
        Try to clean local backup path after unsuccessful restoration.

        :param local_backup_path: path to the unsuccessful restored backup.
        :param logger: logger object.
        """
        if os.path.exists(local_backup_path):
            logger.warning("Cleaning unsuccessful restoration path '{}' from the local system"
                           .format(local_backup_path))

            if not remove_path(local_backup_path):
                logger.error("Could not delete unsuccessful restoration path '{}'."
                             .format(local_backup_path))

    def get_dir_list_to_remove(self):
        """
        Get the list of oldest directories to be removed for each customer from the offsite.

        :return: list with the directories to be removed or empty.
        """
        dir_list_by_customer_dic = self.get_offsite_backup_dic()

        remove_dir_list = []
        for customer in dir_list_by_customer_dic.keys():
            number_backup_per_customer = len(dir_list_by_customer_dic[customer])
            if number_backup_per_customer > MAX_BKP_OFFSITE:
                self.logger.info("Off-site location for customer {} has {} backups. Removing the "
                                 "{} oldest.".format(customer, number_backup_per_customer,
                                                     number_backup_per_customer - MAX_BKP_OFFSITE))

                # ignore the first MAX_BKP_OFFSITE most recent backups in this list.
                for removable_backup in dir_list_by_customer_dic[customer][MAX_BKP_OFFSITE:]:
                    remove_dir_list.append(removable_backup)
            else:
                self.logger.warning("Customer {} has just {} backup(s) off-site. Nothing to "
                                    "do.".format(customer, number_backup_per_customer))
        return remove_dir_list

    def clean_offsite_backup(self):
        """
        Connect to the off-site server and cleans old backups for each customer.

        Keeps most recent backups equivalent to number MAX_BKP_OFFSITE .

        1. Retrieve the list of directories (backups) from each customer.
        2. Check if it is necessary to delete older backups and add the path to a list.
        3. Try to remove the selected backups from the list for all customers.

        :return tuple (true, success message, list of removed directories), if no problem happened
                during the process,
                tuple (false, error message, list of removed directories) otherwise.
        """
        self.logger.log_info("Performing the clean up on off-site server.")

        remove_dir_list = self.get_dir_list_to_remove()

        if len(remove_dir_list) == 0:
            return True, "Off-site clean up finished successfully with no backup to be removed.", []

        try:
            not_removed_list, validated_removed_list = remove_remote_dir(self.offsite_config.host,
                                                                         remove_dir_list)
        except Exception as e:
            return False, e.message, []

        if len(not_removed_list) != 0:
            log_message = "Following backups were not removed: {}".format(not_removed_list)
            return False, log_message, validated_removed_list

        return True, "Off-site clean up finished successfully.", validated_removed_list

    def restore_volume(self, volume_name, volume_root_path):
        """
        Go through all volumes, decompressing and decrypting the files.

        :param volume_name:      volume name.
        :param volume_root_path: volume root path.
        """
        volume_output_dic = {}

        volume_output_dic[VolumeOutputKeys.processing_time.name] = 0.0
        volume_output_dic[VolumeOutputKeys.tar_time.name] = 0.0
        volume_output_dic[VolumeOutputKeys.output.name] = ""
        volume_output_dic[VolumeOutputKeys.status.name] = False

        volume_full_path = os.path.join(volume_root_path, volume_name)

        try:
            if not os.path.exists(volume_full_path):
                raise Exception("Volume path '{}' does not exist.".format(volume_full_path))

            self.logger.info("Extracting volume {}.".format(volume_full_path))

            volume_extraction_time = []
            decompress_file(volume_full_path, volume_root_path, True,
                            get_elapsed_time=volume_extraction_time)

            self.logger.log_time("Elapsed time to extract volume '{}'".format(volume_full_path),
                                 volume_extraction_time[0])

            decompressed_volume_dir = os.path.join(volume_root_path, volume_name.split('.')[0])

            self.logger.info("Decrypting and decompressing files from volume '{}'.".format(
                decompressed_volume_dir))

            tot_volume_process_time = []
            self.gpg_manager.decrypt_decompress_file_list(decompressed_volume_dir,
                                                          self.number_threads,
                                                          get_elapsed_time=tot_volume_process_time)

            self.logger.log_time("Elapsed time to process the volume '{}'".format(
                decompressed_volume_dir), tot_volume_process_time[0])

            volume_output_dic[VolumeOutputKeys.processing_time.name] = tot_volume_process_time[0]
            volume_output_dic[VolumeOutputKeys.tar_time.name] = volume_extraction_time[0]
            volume_output_dic[VolumeOutputKeys.status.name] = True

        except Exception as e:
            volume_output_dic[VolumeOutputKeys.output.name] = \
                "Error while restoring volume {} due to: {}.".format(volume_name, e.message)

        return volume_output_dic

    def get_customer_enmaas_config_list(self, customer_name=""):
        """
        Get customer enmaas config list to be processed.

        If no customer_name is specified, get all customers' config list.

        Raise an exception in case of error.

        :param customer_name: customer name or empty string.

        :return: list with all enmaas config objects or one from the specified customer.
        """
        if not customer_name.strip():
            return self.enmaas_config_dic.values()

        customer_enmaas_config = get_elem_dic(self.enmaas_config_dic, customer_name)
        if customer_enmaas_config is None:
            raise Exception("Customer name {} not found in the configuration file.".
                            format(customer_name))

        return [customer_enmaas_config]

    def get_local_backup_handler_dic(self, customer_name):
        """
        Get the list of LocalBackupHandler objects per customer to process the backup.

        Raise an exception in case of error.

        :param customer_name: customer name or empty string.

        :return: tuple (list of backup handler objects, total backup size)
        """
        max_required_space_mb = 0
        local_backup_handler_dic = {}
        enmaas_conf_list = self.get_customer_enmaas_config_list(customer_name)

        for enmaas_conf in enmaas_conf_list:
            if not os.path.exists(enmaas_conf.backup_path):
                self.logger.error("Backup path '{}' does not exist for customer {}".
                                  format(enmaas_conf.backup_path, enmaas_conf.name))
                continue

            backup_handler = LocalBackupHandler(self.offsite_config,
                                                enmaas_conf,
                                                self.gpg_manager,
                                                self.number_processors,
                                                self.number_threads,
                                                self.notification_handler,
                                                self.logger)

            valid_value, log_message, backup_size = \
                get_onsite_backups_size(backup_handler.get_local_backup_list(),
                                        backup_handler.customer_conf.backup_path,
                                        BLOCK_SIZE)

            if not valid_value:
                raise Exception(log_message)

            self.logger.info(log_message)

            max_required_space_mb += backup_size

            local_backup_handler_dic[enmaas_conf.name] = backup_handler

        return local_backup_handler_dic, max_required_space_mb

    @timeit
    def execute_backup_to_offsite(self, customer_name="", cleanup=False, **kwargs):
        """
        Run through all customer's deployments and processes the backup of their volumes.

        Procedure flow is:

        1. Creates a temporary local folder to store the files to be uploaded.
        2. For each deployment do:
            2.1 Validate the remote backup location;
            2.2 Get valid backups to be uploaded;
            2.3 For each valid backup: compress, encrypt and transfer their volumes
                to the remote location.
                2.3.4 Compressed and encrypted data will be placed in a temporary folder
                      before being transferred.
            2.4 If something gets wrong in the process, handle the error and move
                to the next customer.

        3. Deletes the temporary files at the end.

        :param customer_name:          desired customer name to execute the backup.
        :param cleanup:                flag to whether one should do the house keeping of NFS
                                       and off-site server.
        :returns: tuple (true, empty string) when success,
                  tuple (false, error message) otherwise.
        """
        try:
            if not create_path(self.offsite_config.temp_path):
                raise Exception("Temporary folder '{}' could not be created.".format(
                    self.offsite_config.temp_path))

            local_backup_handler_map, max_required_space_mb = \
                self.get_local_backup_handler_dic(customer_name)

            has_sufficient_space_upload, error_message = \
                self.check_disk_space_upload(max_required_space_mb, BLOCK_SIZE)

            if not has_sufficient_space_upload:
                raise Exception(error_message)

            for local_backup_handler in local_backup_handler_map.values():
                local_backup_handler.process_backup_list()

            if cleanup:
                ret, out_msg, removed_dir = self.clean_offsite_backup()
                if not ret:
                    raise Exception("Error while performing the clean up off-site due to {}."
                                    .format(out_msg))

                self.logger.info("{}: Removed directories were: {}".format(out_msg, removed_dir))

        except Exception as e:
            error_message = "Error while processing backup due to: {}.".format(e.message)
            self.logger.error(error_message)

            email_subject = "Could not process backups to offsite."
            prepare_send_notification_email(self.notification_handler, email_subject, error_message)

            return False, e[0]

        finally:
            if not remove_path(self.offsite_config.temp_path):
                self.logger.error("Error while deleting temporary folder '{}'.".format(
                    self.offsite_config.temp_path))

        return True, ""

    def check_disk_space_upload(self, max_required_space_mb, block_size):
        """
        Check if there is available space onsite and offsite to upload the backup.

        :param max_required_space_mb: total size of the backups to be run in the current
        job.
        :param block_size: whether MB, GB or TB, used with the log message for better readability.

        :return: tuple (true, empty string) when there is available space;
                 tuple (false, error message), otherwise.
        """
        self.logger.info("The maximum required free disk space to process all valid backups: {} {}".
                         format(max_required_space_mb, block_size))

        valid_value, log_message, free_disk_space_for_tmp_mb = get_free_disk_space(
            self.offsite_config.temp_path)

        if not valid_value:
            return False, log_message

        if not sufficient_onsite_disk_space(free_disk_space_for_tmp_mb, max_required_space_mb):
            log_message = ("Not enough free disk space to store the processed backups "
                           "under: {}, current free space: {} {}, required free space: {} {}"
                           .format(self.offsite_config.temp_path, free_disk_space_for_tmp_mb,
                                   block_size, max_required_space_mb, block_size))
            return False, log_message

        self.logger.info("The estimated required free disk space: {} {} to hold the processed "
                         "backups under: {}, is satisfied, available space: {} {}".
                         format(max_required_space_mb, block_size, self.offsite_config.temp_path,
                                free_disk_space_for_tmp_mb, block_size))

        sufficient_offsite_disk_space, log_message = \
            check_offiste_disk_space(self.offsite_config.host,
                                     self.offsite_config.full_path,
                                     max_required_space_mb,
                                     block_size)

        if not sufficient_offsite_disk_space:
            return False, log_message

        self.logger.info(log_message)

        return True, ""
