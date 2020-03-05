#!/usr/bin/env python

import os
import sys
import argparse
import multiprocessing
from enum import Enum

from thread_pool import MAX_THREAD
from logger import CustomLogger, logging
from backup_settings import ScriptSettings
from offsite_backup_handler import OffsiteBackupHandler
from utils import check_remote_path_exists, create_remote_dir, create_path, get_home_dir, \
    is_valid_ip, log_cli_arguments, validate_boolean_input, validate_host_is_accessible, LOG_SUFFIX

SCRIPT_OPTION_HELP = "Select an option. Options: [1:Backup to cloud, 2: Restore from cloud]"
NUMBER_THREADS_HELP = "Select the number of threads allowed. Defaults to 5."
NUMBER_PROCESSORS_HELP = "Select the number of processors. Defaults to 5."
DO_CLEANUP_HELP = "Whether cleanup NFS and off-site. Defaults to False."
LOG_ROOT_PATH_HELP = "Provide a path to store the logs."
LOG_LEVEL_HELP = "Provide the log level. Options: [CRITICAL, ERROR, WARNING, INFO, DEBUG]."
BACKUP_TAG_HELP = "Provide the backup tag to be restored."
CUSTOMER_NAME_HELP = "Provide the customer name to process upload or restore."
BACKUP_DESTINATION_HELP = "Provide the destination of the restored backup."
USAGE_HELP = "Display detailed help."

SCRIPT_PATH = os.path.dirname(__file__)
SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

CONF_FILE_NAME = 'config.cfg'

MAIN_LOG_FILE_NAME = "bur_{}.{}".format(SCRIPT_FILE, LOG_SUFFIX)
DEFAULT_LOG_ROOT_PATH = os.path.join(get_home_dir(), "backup", "logs")

ExitCodes = Enum('ExitCodes', 'SUCCESS, INVALID_INPUT, CONFIG_FILE_ERROR, '
                              'FAILED_DISK_SPACE_CHECK, INVALID_LOG_PATH')

ScriptOperations = Enum('ScriptOperations', 'BKP_TO_CLOUD, DOWNLOAD_FROM_CLOUD, SIZE')


def main():
    """
    Start the backup/restore processes according to the input.

    1. Validate input parameters.
    2. Read the configuration file and validates it;
    3. Check connection with the off-site environment is up;
    4. Execute the backup/restore for each customer.

    In case of success, return SUCCESS code.

    In case of validation error, exit with one of the error codes specified by ExitCodes enumerator.
    """
    args = parse_arguments()

    logger = CustomLogger(SCRIPT_FILE, args.log_root_path, MAIN_LOG_FILE_NAME, args.log_level)

    if args.usage:
        usage(logger)

    log_cli_arguments(logger)

    validation_error_list = []
    config_object_dic = ScriptSettings(CONF_FILE_NAME, logger).get_config_objects_from_file(
        validation_error_list)

    if validation_error_list:
        logger.log_error_exit(validation_error_list, ExitCodes.CONFIG_FILE_ERROR.value)

    offsite_config = config_object_dic['get_offsite_config']
    enmaas_config_dic = config_object_dic['get_enmaas_config_dic']
    gpg_manager = config_object_dic['get_gnupg_manager']
    notification_handler = config_object_dic['get_notification_handler']

    validate_offsite_backup_server(offsite_config, logger, validation_error_list)

    validate_onsite_backup_locations(enmaas_config_dic, validation_error_list)

    validate_operation_arg(args, validation_error_list)

    if validation_error_list:
        logger.log_error_exit(validation_error_list, ExitCodes.INVALID_INPUT.value)

    args.number_threads = validate_number_of_threads(args.number_threads, logger)
    args.number_processors = validate_number_of_processors(args.number_processors,
                                                           len(enmaas_config_dic.keys()),
                                                           logger)

    backup_handler = OffsiteBackupHandler(gpg_manager,
                                          offsite_config,
                                          enmaas_config_dic,
                                          args.number_threads,
                                          args.number_processors,
                                          notification_handler,
                                          logger)

    total_time = []
    if str(args.script_option) == str(ScriptOperations.BKP_TO_CLOUD.value):
        ret, message = backup_handler.execute_backup_to_offsite(args.customer_name,
                                                                args.do_cleanup,
                                                                get_elapsed_time=total_time)
        if ret:
            logger.log_time("Elapsed time to complete the whole backup process", total_time[0])
        else:
            logger.log_error_exit(message, ExitCodes.FAILED_DISK_SPACE_CHECK.value)

    elif str(args.script_option) == str(ScriptOperations.DOWNLOAD_FROM_CLOUD.value):
        ret, message = backup_handler.execute_restore_backup_from_offsite(args.customer_name,
                                                                          args.backup_tag,
                                                                          args.backup_destination,
                                                                          get_elapsed_time=
                                                                          total_time)
        if ret:
            logger.info(message)
            logger.log_time("Elapsed time to complete the whole backup restore process",
                            total_time[0])
        else:
            logger.error(message)
    else:
        logger.log_error_exit("Operation {} not supported.".format(args.script_option),
                              ExitCodes.INVALID_INPUT.value)

    return ExitCodes.SUCCESS.value


def parse_arguments():
    """
    Parse input arguments.

    :return: parsed arguments .
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--script_option", default=1, help=SCRIPT_OPTION_HELP)
    parser.add_argument("--number_threads", default=5, help=NUMBER_THREADS_HELP)
    parser.add_argument("--number_processors", default=5, help=NUMBER_PROCESSORS_HELP)
    parser.add_argument("--do_cleanup", default=False, help=DO_CLEANUP_HELP)
    parser.add_argument("--log_root_path", nargs='?', default=DEFAULT_LOG_ROOT_PATH,
                        help=LOG_ROOT_PATH_HELP)
    parser.add_argument("--log_level", nargs='?', default=logging.INFO, help=LOG_LEVEL_HELP)
    parser.add_argument("--backup_tag", help=BACKUP_TAG_HELP)
    parser.add_argument("--customer_name", default="", help=CUSTOMER_NAME_HELP)
    parser.add_argument("--backup_destination", nargs='?', help=BACKUP_DESTINATION_HELP)
    parser.add_argument("--usage", action="store_true", help=USAGE_HELP)

    args = parser.parse_args()

    args.log_level = validate_log_level(args.log_level)
    args.log_root_path = validate_log_root_path(args.log_root_path)
    args.do_cleanup = validate_boolean_input(args.do_cleanup)

    return args


def validate_log_root_path(log_root_path):
    """
    Validate the informed log root path.

    Try to create this path if it does not exist.

    If an error happens exit with INVALID_LOG_PATH error code.

    :param log_root_path: log root path.

    :return validated log root path.
    """
    if log_root_path is None or not log_root_path.strip():
        log_root_path = DEFAULT_LOG_ROOT_PATH

    if not create_path(log_root_path):
        sys.exit(ExitCodes.INVALID_LOG_PATH.value)

    return log_root_path


def validate_log_level(log_level):
    """
    Validate the informed log level. Sets to INFO when the informed value is invalid.

    :param log_level: log level.
    :return validated log level.
    """
    if log_level not in (logging.CRITICAL, logging.ERROR, logging.WARNING,
                         logging.INFO, logging.DEBUG):
        is_invalid_level = False

        try:
            log_level = str(log_level)
        except Exception:
            is_invalid_level = True

        if str(log_level).lower() == "critical":
            log_level = logging.CRITICAL
        elif str(log_level).lower() == "error":
            log_level = logging.ERROR
        elif str(log_level).lower() == "warning":
            log_level = logging.WARNING
        elif str(log_level).lower() == "info":
            log_level = logging.INFO
        elif str(log_level).lower() == "debug":
            log_level = logging.DEBUG
        else:
            is_invalid_level = True

        if is_invalid_level:
            log_level = logging.INFO

    return log_level


def validate_operation_arg(args, validation_error_list=[]):
    """
    Validate script operation argument.

    In case of validation error, exits with error code: INVALID_INPUT.

    :param args:                  input arguments to be validated.
    :param validation_error_list: validation error list.
    """
    try:
        operation = int(args.script_option)
        if operation <= 0 or operation >= ScriptOperations.SIZE.value:
            raise ValueError("Invalid script option: {}".format(operation))

        if operation == int(ScriptOperations.DOWNLOAD_FROM_CLOUD.value):
            if args.backup_destination is None or not args.backup_destination.strip():
                args.backup_destination = ""

            if (args.backup_tag is None or not args.backup_tag.strip()) and \
                    (args.customer_name is None or not args.customer_name.strip()):
                raise ValueError("Inform the backup tag or customer name to do the restore.")
    except ValueError as e:
        validation_error_list.append(e.message)


def validate_number_of_threads(num_threads_to_use, logger):
    """
    Check the provided number of threads to be used if valid.

    :param num_threads_to_use: the number of threads to be checked from the input
    :param logger: logger object.

    :return: the correct number of threads to be used, in this case will
    be equal to the value thread_pool.MAX_THREAD otherwise the provided number is valid, returns it.
    """
    if 0 >= num_threads_to_use or num_threads_to_use > 5:
        logger.warning("Provided invalid number of threads: {}. Changed to: {}."
                       .format(num_threads_to_use, MAX_THREAD))
        return MAX_THREAD
    else:
        return num_threads_to_use


def validate_number_of_processors(num_processors_to_use, num_of_customers, logger):
    """
    Check the provided number of processors to be used if valid.

    :param num_processors_to_use: the number of processors to be checked from the input args
    :param num_of_customers: the number of customers, scanned from the config.cfg file
    :param logger: logger object.

    :return: the correct number of processors to be used, according to the following cases:
    1. if the provided num_processors_to_use is greater than the number of available cores, then:
        1.1 if number of available cores >= num_of_customers,
            then the num_processors_to_use = num_of_customers.
        1.2 otherwise, will only use the available cores on this machine.
    2. if the provided num_processors_to_use was invalid, e.g. a string, then:
        it will be automatically corrected, to be equal to the num_of_customers.
    """
    cpu_count = multiprocessing.cpu_count()
    if cpu_count <= 1:
        logger.warning("Low number of available processors: {}".format(cpu_count))

    try:
        num_processors_to_use = int(num_processors_to_use)
    except ValueError:
        logger.warning("Provided invalid number of processors to use: {}, "
                       "the number of processors to use has been changed to "
                       "the number of customers, which is: {}"
                       .format(num_processors_to_use, num_of_customers))
        num_processors_to_use = num_of_customers

    if num_processors_to_use <= 0 \
            or num_processors_to_use >= cpu_count \
            or num_processors_to_use > num_of_customers:
        if cpu_count >= num_of_customers:
            altered_num_processors = num_of_customers
        else:
            altered_num_processors = cpu_count

        logger.warning(
            "Provided invalid number of processors to use: {}, "
            "the number of available cores: {}, "
            "the number of processors to use has been changed to: {}"
            .format(num_processors_to_use, cpu_count, altered_num_processors))

        num_processors_to_use = altered_num_processors

    else:
        logger.info("The provided number of processors to use: {}, is valid."
                    .format(num_processors_to_use))

    return num_processors_to_use


def validate_onsite_backup_locations(enmaas_config_dic, validation_error_list=[]):
    """
    Check if the on-site paths informed in the configuration file are valid for each customer.

    In case of validation error, the message is appended to the validation error list.

    :param enmaas_config_dic: dictionary with enmaas information for each customer in the
    configuration file.
    :param validation_error_list: validation error list.
    """
    if len(enmaas_config_dic.keys()) == 0:
        validation_error_list.append("No customer defined in the configuration file '{}'. "
                                     "Nothing to do.".format(CONF_FILE_NAME))

    for customer_key in enmaas_config_dic.keys():
        enmaas_config = enmaas_config_dic[customer_key]
        if not os.path.exists(enmaas_config.backup_path):
            validation_error_list.append("Informed path for customer {} does not exist: '{}'.".
                                         format(customer_key, enmaas_config.backup_path))


def validate_offsite_backup_server(offsite_config, logger, validation_error_list=[]):
    """
    Check if the off-site server is up and validates the specified path on that server.

    1. Check if the provided parameters are not empty.
    2. Check if the provided IP is valid;
    3. Check if the provided IP is working;
    4. Verifies if the provided path exists, otherwise tries to create it.

    In case of validation error, the message is appended to the validation error list.

    :param offsite_config: offsite config object.
    :param logger: logger object.
    :param validation_error_list: validation error list.
    """
    if not offsite_config:
        validation_error_list.append("No off-site defined in the configuration file '{}'. "
                                     "Nothing to do.".format(CONF_FILE_NAME))
        return

    if not offsite_config.user.strip() \
            or not offsite_config.path.strip() \
            or not offsite_config.folder.strip():
        validation_error_list.append("There are empty off-site parameters in the configuration "
                                     "file.")

    if not is_valid_ip(offsite_config.ip):
        validation_error_list.append("Informed off-site IP '{}' is not valid.".
                                     format(offsite_config.ip))

    if not validate_host_is_accessible(offsite_config.ip):
        validation_error_list.append("Off-site with this credentials {} is not accessible".
                                     format(offsite_config))

    if not check_remote_path_exists(offsite_config.host, offsite_config.path):
        validation_error_list.append("Informed root backup path does not exist on off-site: '{}'.".
                                     format(offsite_config.path))
    else:
        if not check_remote_path_exists(offsite_config.host, offsite_config.full_path):
            logger.warning("Remote backup location path does not exist, trying to create one.")

            if not create_remote_dir(offsite_config.host, offsite_config.full_path):
                validation_error_list.append("Remote directory could not be created '{}'".
                                             format(offsite_config.full_path))
            logger.info(
                "New remote path '{}' created successfully.".format(offsite_config.full_path))
        else:
            logger.info("Remote directory '{}' already exists".format(offsite_config.full_path))


def usage(logger, exit_code=ExitCodes.SUCCESS.value):
    """
    Display this usage help message whenever the script is run with '--usage' argument.

    :param logger:    logger object.
    :param exit_code: exit code to quit this application with after running this method.
    """
    logger.info("""
        Usage of: '{}'

        This message is displayed when script is run with '--usage' argument.
        ============================================================================================
                                            Overview:
        ============================================================================================
        This script aims at automating the process for off-site upload and download of
        the ENMaaS backup sets, according to the requirements from the Jira issue NMAAS-516
        (https://jira-nam.lmera.ericsson.se/browse/NMAAS-516).

        It basically does the following for each option:

        1. Upload

        1.1 Reads the parameters from a configuration file to retrieve the customer
            deployment names.
        1.2 Traverses each customer directory and upload every good back sets to Azure cloud except
            one last backup.
        1.3 Deletes the backup sets from NFS server directory after successful upload.
        1.4 Deletes any backup sets, other than last 3, from the Azure Cloud.
        1.5 Encrypt the data using gpg tool and compress before uploading to Azure.

        2. Download

        2.1 Accepts the customer name, backup tag or both as input as well as the
            destination directory.
        2.2 Lists the available backup sets for a customer.
        2.3 Extracts and decrypts the backup content after downloading.

        ============================================================================================
                                    Script Flow and Exit Codes:
        ============================================================================================

        This script works as follows:

        1. Validate input parameters.

        2. Validate configuration file information.

        3. For the upload feature, do the following:
            3.1 Create temporary folder to store auxiliary files during the process;
            3.2 Run over all tenants' folders validating the informed path and getting the list of
                valid backups to be uploaded, except the last backup;
            3.3 For all tenants, check the remote location to transfer the backup is available,
                otherwise try to create it;
            3.4 Generate a pool of processes to execute the upload in parallel with all data
                collected so far;
            3.5 Start the pool, which will run the maximum number of processes informed
                by parameter;
            3.6 Each process is responsible for the following tasks:
                - Process each volume in parallel by using a thread pool with the maximum
                    number of threads informed by parameter.
                - Each thread will run over all volumes' files encrypting them,
                    compressing the whole folder and uploading it at the end.
            3.7 After a successful upload, the local backup will be removed, following the
                rule of keeping at least the most recent backup.
            3.8 After the upload of all backups is finished, perform the clean-up
                on the off-site server, as follows:
                - Retrieve the list of current backups stored for each customer,
                    sorted by descending creation date (e.g. most recent backups first)
                - Remove the older backups from each tenants' directory if there are more than 3.

        4. For the download feature, do the following:
            4.1 If the user informs just the customer name, the system queries the remote server for
                the list of available backups.
            4.2 If the user informs just the backup tag, the actual backup path is searched and the
                system tries to download it.
            4.3 If the user informs both backup tag and customer, the system tries to download the
                actual backup folder from the off-site.
            4.4 After a successful download, the system decompress and decrypts the volumes in
                parallel by using the thread pool strategy.
            4.5 The restored backup is stored in the destination location passed by parameter.

        Regarding the upload function, if at any point a problem happens, the upload of a particular
        customer stops and an exception with the reported error is raised. This way, the upload
        of other tenants are not affected.

        Moreover, the following error codes are raised in case of other failures during the process:

        INVALID_INPUT (2):     When there is a problem with one or more input values either in the
        configuration file or in the run command.
        CONFIG_FILE_ERROR (3): When there is a problem in the structure of the configuration
        file.

        ============================================================================================
                                        Configuration File ({}):
        ============================================================================================

        The script depends on a configuration file '{}' for both operations Upload and Restore.

        --------------------------------------------------------------------------------------------
        It must contain the following email variables:

        [SUPPORT_CONTACT]
        EMAIL_TO       Email address to send failure notifications.
        EMAIL_URL      URL of the email service.

        [GNUPG]
        GPG_USER_NAME  User name used by gpg to create a encryption key.
        GPG_USER_EMAIL Use email for gpg usage.

        [OFFSITE_CONN]
        IP             remote ip address.
        USER           server user.
        BKP_PATH       main path where the backup content will be placed.
        BKP_DIR        folder where the customer's backup will be transferred.

        For example:

        [SUPPORT_CONTACT]
        EMAIL_TO=fo-enmaas@ericsson.com
        EMAIL_URL=https://172.31.2.5/v1/emailservice/send

        [GNUPG]
        GPG_USER_NAME="backup"
        GPG_USER_EMAIL="backup@root.com"

        [OFFSITE_CONN]
        IP=159.107.167.73
        USER=solaris
        BKP_PATH=/export/home/solaris/Documents
        BKP_DIR=rpc_backup

        Note: Path variables should not contain quotes.
        --------------------------------------------------------------------------------------------

        --------------------------------------------------------------------------------------------
        Each customer should have a new entry in this configuration file as below:

        [CUSTOMER_NAME]
        CUSTOMER_PATH   path to the customer's volumes.

        For example:
        [CUSTOMER_0]
        CUSTOMER_PATH=/home/jefferson/Documents/mock_open_stack_rpc/customer_deployment_0
        --------------------------------------------------------------------------------------------
        """.format(SCRIPT_FILE, CONF_FILE_NAME, CONF_FILE_NAME))

    sys.exit(exit_code)


if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
