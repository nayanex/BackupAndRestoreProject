import os
import sys
import pwd
import glob
import json
import time
import gzip
import shutil
import socket
import hashlib
from enum import Enum
from threading import Timer
from subprocess import PIPE, Popen
from tarfile import TarFile, TarError

from rsync_manager import RsyncManager

LOG_SUFFIX = "log"
TAR_SUFFIX = "tar"
GZ_SUFFIX = "gz"
GPG_SUFFIX = "gpg"
METADATA_FILE_SUFFIX = "_metadata"

TIMEOUT = 120
NUMBER_TRIES = 3
LOG_LEVEL = "LogLevel=ERROR"

BLOCK_SIZE = "MB"

PLATFORM_NAME = str(sys.platform).lower()

TAR_CMD = "tar"
if 'sun' in PLATFORM_NAME:
    TAR_CMD = "gtar"

MetadataKeys = Enum('MetadataKeys', 'objects, md5')

VolumeOutputKeys = Enum('VolumeOutputKeys', 'volume_path, processing_time, tar_time, output, '
                                            'status, rsync_output, transfer_time')


def create_path(path):
    """
    Create a path in the local storage.

    :param path: path to be created.

    :return: true if path already exists or was successfully created,
             false otherwise.
    """
    if os.path.exists(path):
        return True
    try:
        os.makedirs(path)
    except Exception:
        return False
    return True


def remove_path(path):
    """
    Delete a path from local storage.

    :param path:   file name to be removed.

    :return: true if path does not exist or was successfully deleted,
             false otherwise.
    """
    if not os.path.exists(path):
        return True

    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except Exception:
        return False

    return True


def popen_communicate(host, command):
    """
    Use Popen library to communicate to a remote server by using ssh protocol.

    :param host: remote host to connect.
    :param command: command to execute on remote server.

    :return: pair stdout, stderr from communicate command,
             empty string pair, otherwise.
    """
    if host == "" or command == "":
        return "", ""

    ssh = Popen(['ssh', '-o', LOG_LEVEL, host, 'bash'],
                stdin=PIPE, stdout=PIPE, stderr=PIPE)

    timer = Timer(TIMEOUT, lambda process: process.kill(), [ssh])

    try:
        timer.start()
        stdout, stderr = ssh.communicate(command)
    finally:
        if not timer.is_alive():
            stderr = "Command '{}' timeout.".format(command)
        timer.cancel()

    return stdout, stderr


def check_remote_path_exists(host, path):
    """
    Check if a remote path exists.

    :param host:   remote host address, e.g. user@host_ip
    :param path:   remote path to be verified.

    :return: false, if the path does not exist,
             true, otherwise
    """
    ssh_check_dir_command = """
    if [ -d {} ]; then echo "DIR_IS_AVAILABLE"; fi\n
    """.format(path, path)

    stdout, _ = popen_communicate(host, ssh_check_dir_command)

    if stdout.strip() != "DIR_IS_AVAILABLE":
        return False

    return True


def split_folder_list(folder_list_string=""):
    """
    Split a string of paths separated by \n returned from an ls command.

    :param folder_list_string: list of path in string format separed by \n.

    :return: parsed list of path.
    """
    folder_list = []
    for folder_path in folder_list_string.split('\n'):
        folder_path = folder_path.strip()

        if not folder_path or folder_path == '.':
            continue

        # Removing last slash to avoid errors while handling this path.
        if folder_path[len(folder_path) - 1] == '/':
            folder_path = folder_path[0:len(folder_path) - 1]

        folder_list.append(folder_path)

    return folder_list


def create_remote_dir(host, full_path):
    """
    Try to create a remote directory with ssh commands.

    :param host:      remote host address, e.g. user@host_ip
    :param full_path: full path to be created.

    :return: true, if directory was successfully created
             false, otherwise.
    """
    ssh_create_dir_commands = """
    mkdir {}\n
    echo END-OF-COMMAND\n
    if [ -d {} ]; then echo "DIR_IS_AVAILABLE"; fi\n
    """.format(full_path, full_path)

    stdout, stderr = popen_communicate(host, ssh_create_dir_commands)

    if not stderr:
        split_output = stdout.split("END-OF-COMMAND")

        if len(split_output) < 2 or not split_output[1].strip() == "DIR_IS_AVAILABLE":
            return False
    else:
        return False

    return True


def remove_remote_dir(host, dir_list=[]):
    """
    Remove the informed directory list from the remote server.

    An exception is raised if a problem happens during the process.

    :param host:     remote host address, e.g. user@host_ip
    :param dir_list: directory list.

    :return: tuple (list of not removed directories, list of validated removed directories).
    """
    if not host.strip():
        raise Exception("Empty host was provided.")

    if isinstance(dir_list, str):
        if not dir_list.strip():
            raise Exception("Empty directory was provided.")
        dir_list = [dir_list]

    if not dir_list:
        raise Exception("Empty list was provided.")

    remove_dir_cmd = ""

    for d in dir_list:
        folder_path = d.strip()
        remove_dir_cmd += "rm -rf {}\n".format(folder_path)

    stdout, stderr = popen_communicate(host, remove_dir_cmd)

    if stderr.strip():
        raise Exception("Unable to perform the remove command on offsite due to: {}".format(stderr))

    return validate_path_list_removed_from_offsite(host, dir_list)


def validate_path_list_removed_from_offsite(host, remove_dir_list=[]):
    """
    Check the list of removed dirs, to validate if they were successfully deleted from offsite.

    :param host: remote host to do the validation.
    :param remove_dir_list: list of directories supposed to be removed.

    :return: list of not removed directories, list of validated removed directories.
    """
    not_removed_list = []
    validated_removed_list = []
    for removed_path in remove_dir_list:
        if not check_remote_path_exists(host, removed_path):
            validated_removed_list.append(removed_path)
        else:
            not_removed_list.append(removed_path)

    return not_removed_list, validated_removed_list


def get_elem_dic(dic, key):
    """
    Find and get element from dictionary.

    :param dic: dictionary.
    :param key: key to the value.
    :return: value referred by the key, if exists,
             None otherwise.
    """
    if not isinstance(dic, dict):
        return None

    if key in dic.keys():
        return dic[key]

    return None


def find_elem_dic(dic, query):
    """
    Find element in a map of arrays.

    :param dic: map object.
    :param query:   query string.

    :return:        tuple (key, item) that was found,
                    tuple ("", "") otherwise.
    """
    if not str(query).strip():
        return "", ""

    for key in dic.keys():
        for item in dic[key]:
            if query in str(item):
                return key, item
    return "", ""


def get_md5(filename):
    """
    Calculate the MD5 code for the specified file path.

    :param filename: file name whose md5 should be calculated.

    :return: md5 code if calculated successfully,
             empty string otherwise.
    """
    if not os.path.exists(filename):
        return ""

    hash_md5 = hashlib.md5()  # nosec
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def is_valid_ip(ip):
    """
    Validate if provided IP is valid.

    :param ip: IP in string format to be validated.

    :return: true if ip is valid,
             false, otherwise.
    """
    try:
        socket.inet_aton(ip)
    except socket.error:
        return False

    return True


def validate_host_is_accessible(ip):
    """
    Validate host is accessible.

    :param ip: remote host IP.

    :return: true, if host is accessible,
             false, otherwise.
    """
    with open(os.devnull, "w") as devnull:
        ret_code = Popen(["ping", "-c", "1", ip], stdout=devnull, stderr=devnull).wait()
        return ret_code == 0


def timeit(method):
    """Calculate the elapsed time to execute a function. Decorator function."""
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        if 'get_elapsed_time' in kw:
            if isinstance(kw['get_elapsed_time'], list):
                kw['get_elapsed_time'].append(te - ts)

        return result

    return timed


@timeit
def compress_file(source_path, output_path=None, mode="w:gz", **kwargs):
    """
    Compress or archive a path using tarfile module.

    This function expects a mode to be either "w:gz", referring to compressing with gzip, or "w",
    which uses no compression.

    Output file is placed in the same directory as the original file by default,
    if no output_path is specified.

    If an error occurs, an Exception is raised with the details of the problem.

    :param source_path: file/folder path to be compressed.
    :param output_path: destination folder of the compressed file.
    :param mode:        compression mode to write file (w:gz) or tar mode (w).

    :return compressed file path.
    """
    if not os.path.exists(source_path):
        raise Exception("File '{}' does not exist.".format(source_path))

    if mode not in ["w", "w:", "w:gz"]:
        raise Exception("Provided invalid mode '{}'.".format(mode))

    if output_path is None or not output_path.strip():
        output_path = os.path.dirname(source_path)

    if not os.path.exists(output_path):
        raise Exception("Output path '{}' does not exist.".format(output_path))

    try:
        if GZ_SUFFIX in mode:
            compressed_file_path = gzip_file(source_path, output_path)
        else:
            compressed_file_path = tar_file(source_path, output_path)

    except Exception as e:
        raise Exception("Error while compressing file '{}' to destination '{}' due to {"
                        "}.".format(source_path, output_path, e.message))

    return compressed_file_path


@timeit
def decompress_file(source_path, output_path, remove_compressed=False, **kwargs):
    """
    Decompress a file using the tar strategy.

    If an error occurs, an Exception is raised with the details of the problem.

    :param source_path:       file to be decompressed.
    :param output_path:       file path of the output file.
    :param remove_compressed: flag to inform if the compressed file should be deleted at the end.

    :return true, when the function executed without errors,
            raise an exception otherwise.
    """
    if not os.path.exists(source_path):
        raise Exception("File does not exist '{}'".format(source_path))

    file_list = []
    if os.path.isdir(source_path):
        for f in os.listdir(source_path):
            file_path = os.path.join(source_path, f)
            file_list.append(file_path)
    else:
        file_list.append(source_path)

    try:
        for file_path in file_list:
            if is_tar_file(file_path):
                untar_file(file_path, output_path)
            elif is_gzip_file(file_path):
                gunzip_file(file_path, output_path)
            else:
                raise Exception("File format not supported for decompressing. "
                                "Supported files are .tar and .gz")

            if remove_compressed:
                remove_path(file_path)

    except Exception as e:
        raise Exception("Error while decompressing file '{}' due to {}.".format(source_path,
                                                                                e.message))

    return True


def gzip_file(file_path, file_destination):
    """
    Compress file using gzip strategy.

    :param file_path: file to be compressed.
    :param file_destination: destination folder.

    :return: full compressed file path.
    """
    try:
        compressed_file_name = "{}.{}".format(os.path.basename(file_path), GZ_SUFFIX)

        compressed_file_path = os.path.join(file_destination, compressed_file_name)

        compress_command = "gzip -r -c {} > {}".format(file_path, compressed_file_path)

        ret = Popen(compress_command, shell=True).wait()

        if int(ret) != 0:
            raise Exception("Gzip command returned error code: {}.".format(ret))

    except Exception as e:
        raise Exception("gzip_file failed due to: {}.".format(e.message))

    return compressed_file_path


def tar_file(file_path, file_destination):
    """
    Archive file using tar strategy.

    It raises an exception if an error occurs.

    :param file_path: file to be archived.
    :param file_destination: destination folder.

    :return: full archived file path.
    """
    try:
        archived_file_name = "{}.{}".format(os.path.basename(file_path), TAR_SUFFIX)

        tar_file_path = os.path.join(file_destination, archived_file_name)

        compress_command = "{} -cf {} -C {} {}".format(TAR_CMD, tar_file_path, os.path.dirname(
            file_path), os.path.basename(file_path))

        ret = Popen(compress_command, shell=True).wait()

        if int(ret) != 0:
            raise Exception("Tar command returned error code: {}.".format(ret))

    except Exception as e:
        raise Exception("tar_file failed due to: {}.".format(e.message))

    return tar_file_path


def gunzip_file(file_path, file_destination):
    """
    Decompress file using gzip strategy.

    It raises an exception if an error occurs.

    :param file_path: file to be decompressed.
    :param file_destination: destination folder.

    :return true if success.
    """
    try:
        if GZ_SUFFIX not in file_path:
            raise Exception("Invalid file path '{}'.".format(file_path))

        decompressed_file_name = os.path.basename(file_path).replace(".{}".format(
            GZ_SUFFIX), "")

        decompress_command = "gunzip -c {} > {}".format(file_path, os.path.join(
            file_destination, decompressed_file_name))

        ret = Popen(decompress_command, shell=True).wait()

        if int(ret) != 0:
            raise Exception("Gunzip command returned error code: {}.".format(ret))

    except Exception as e:
        raise Exception("gunzip_file failed due to: {}.".format(e.message))

    return True


def untar_file(file_path, file_destination):
    """
    Decompress file using tar strategy.

    It raises an exception if an error occurs.

    :param file_path: file to be decompressed.
    :param file_destination: destination folder.

    :return true if success.
    """
    try:
        if TAR_SUFFIX not in file_path:
            raise Exception("Invalid file path '{}'.".format(file_path))

        decompress_command = "{} -C {} -xf {}".format(TAR_CMD, file_destination, file_path)

        ret = Popen(decompress_command, shell=True).wait()

        if int(ret) != 0:
            raise Exception("Tar command returned error code: {}.".format(ret))

    except Exception as e:
        raise Exception("untar_file failed due to: {}.".format(e.message))

    return True


def is_gzip_file(file_path):
    """
    Check whether the informed file path is in gzip format.

    :param file_path: file path.

    :return: whether the path refers to a gzip file or not.
    """
    if not file_path.strip():
        raise Exception("File path is empty.")

    with gzip.open(file_path) as compressed_file:
        try:
            compressed_file.read()
        except IOError:
            return False

    return True


def is_tar_file(file_path):
    """
    Check whether the informed file path is in tar format.

    :param file_path: file path.

    :return: whether the path refers to a tar file or not.
    """
    if not file_path.strip():
        raise Exception("File path is empty.")

    with open(file_path, "r") as compressed_file:
        try:
            TarFile(fileobj=compressed_file)
        except TarError:
            return False

    return True


@timeit
def transfer_file(source_path, target_path, **kwargs):
    """
    Transfer a file from the source to a target location by using RsyncManager.

    If the source_path refers to a remote location, the following format is expected:

        e.g. host@ip:/path/to/remote/file

    In this case the receive function will be called, otherwise, the send function is used.

    If an error occurs, an Exception is raised with the details of the problem.

    :param source_path: file name to be transferred or retrieved.
    :param target_path: remote location.

    :return true, when the function executed without errors,
            raise an exception otherwise.
    """
    if '@' in source_path:
        rsync_output = RsyncManager(source_path, target_path, NUMBER_TRIES).receive()
    else:
        rsync_output = RsyncManager(source_path, target_path, NUMBER_TRIES).send()

    return rsync_output


def get_home_dir():
    """
    Get home directory for the current user.

    :return: home directory.
    """
    return os.path.expanduser("~")


def get_current_user():
    """
    Get current user name.

    :return: current user.
    """
    for name in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
        user = os.environ.get(name)
        if user:
            return user
    return pwd.getpwuid(os.getuid())[0]


def get_path_to_docs():
    """
    Get documents directory for the current user.

    :return: documents directory.
    """
    return os.path.join(get_home_dir(), "Documents")


def validate_boolean_input(bool_arg):
    """
    Convert an input value into boolean.

    :param bool_arg: value to be converted into boolean.
    :return: converted value into boolean.
    """
    if isinstance(bool_arg, str):
        return bool_arg.lower() in ("yes", "true", "t", "1")

    return bool_arg


def prepare_send_notification_email(notification_handler, email_subject, error_list):
    """
    Prepare a the e-mail notification message including the error list.

    :param notification_handler: notification handler object.
    :param email_subject: subject of the email.
    :param error_list: error list during the process.

    :return: true, if success; false otherwise.
    """
    email_body = "The following errors happened during this operation:\n"

    if not isinstance(error_list, list):
        error_list = [error_list]

    for error in error_list:
        email_body += error + "\n"

    return notification_handler.send_mail("OffsiteBur", email_subject, email_body)


def get_onsite_backups_size(valid_backups_folders, source_dir, block_size):
    """
    Loop over all valid backups for customer, to calculate the required onsite free disk space.

    :param valid_backups_folders: onsite valid backup folder name.
    :param source_dir: path to onsite valid backup.
    :param block_size: whether MB, GB or TB, used with the log message for better readability.

    :return: tuple: true, informative log message, the valid backup size
             or
             tuple: false, exception message, -1, in case of any failure.
    """
    backup_size = 0
    for backup_folder in valid_backups_folders:
        valid_backup_dir_path = os.path.join(source_dir, backup_folder)

        valid_value, log_message, backup_value = get_backup_size(valid_backup_dir_path)

        if valid_value:
            backup_size += backup_value
        else:
            return False, log_message, -1

    log_message = ("The backup size at path: {},  is: {} {}".format(source_dir,
                                                                    backup_size,
                                                                    block_size))

    return True, log_message, backup_size


def get_backup_size(backup_path):
    """
    Get the backup size on disk.

    :param backup_path: the full backup path on disk.
    :return: tuple: true, empty message to be ignored, the valid backup size.
             or
             tuple: false, exception message, -1, in case of any failure.
    """
    du = Popen(["du", "-sm", backup_path], stdout=PIPE)
    splitline = ""
    for line in du.stdout:
        splitline = line.split()

    log_message = ""
    try:
        backup_size = int(splitline[0])
    except Exception as e:
        log_message = ("Exception while getting backup size, for the path: {}, "
                       "exception message: {}"
                       .format(backup_path, str(e)))
        return False, log_message, -1

    return True, log_message, backup_size


def get_free_disk_space(backup_temp_path):
    """
    Get the free space for the disk where the backup is located.

    :param backup_temp_path: the full backup path on disk.
    :return: tuple: true, empty message to be ignored, the valid backup size.
             or
             tuple: false, exception message, -1, in case of any failure.
    """
    df = Popen(["df", "-k", backup_temp_path], stdout=PIPE)
    for line in df.stdout:
        splitline = line.split()

    mounted_on = ""
    log_message = ""
    try:
        free_disk_space = int(splitline[3])
        free_disk_space_mb = free_disk_space / 1000  # block size in MB
        mounted_on = str(splitline[5])
    except Exception as e:
        log_message = ("Exception while getting free disk space, where the path: {},"
                       " is mounted on: {}, exception message: {}."
                       .format(backup_temp_path, mounted_on, str(e)))
        return False, log_message, -1

    return True, log_message, free_disk_space_mb


def sufficient_onsite_disk_space(free_disk_space_for_tmp_mb, max_required_space_mb):
    """
    Check whether the disk has sufficient free space to temporarily hold the processed backups.

    :param free_disk_space_for_tmp_mb: the free disk space to check.
    :param max_required_space_mb: the required disk space to processed to backup processing.
    :return: True if the disk has sufficient free space, False otherwise.
    """
    if free_disk_space_for_tmp_mb <= max_required_space_mb:
        return False
    return True


def check_offiste_disk_space(host, backup_path_at_offsite, max_required_space_mb, block_size):
    """
    Check whether the disk on offsite has sufficient free disk space to store the backups.

    :param host: offsite machine to connect to, OFFSITE_USERNAME@OFFISTE_IP.
    :param backup_path_at_offsite: full backup path at offsite.
    :param max_required_space_mb: the required space at offsite.
    :param block_size: whether MB, GB or TB, used with the log message for better readability.
    :return: tuple: true, informative message if there's enough disk space offsite.
             or
             tuple: false, error message if there's no enough disk space offsite.
             or
             tuple: false, exception message, in case of any failure.
    """
    command = "df -k " + backup_path_at_offsite

    stdout, stderr = popen_communicate(host, command)

    try:
        std_output_list = stdout.split('\n')
        if std_output_list is None or len(std_output_list) <= 0:
            log_message = ("Invalid output from offsite while checking disk space for path: {}"
                           .format(backup_path_at_offsite))
            return False, log_message

        file_system_disk_summary = str(std_output_list[1])
        file_summary_values = file_system_disk_summary.split()

        offsite_free_disk_space = int(file_summary_values[3])
        offsite_free_disk_space_mb = offsite_free_disk_space / 1000  # block size in MB

        if offsite_free_disk_space_mb <= max_required_space_mb:
            log_message = "Insufficient disk space at offsite for the path: {}, " \
                          "available disk space: {} {}, required disk space {} {}" \
                .format(backup_path_at_offsite, offsite_free_disk_space_mb, block_size,
                        max_required_space_mb, block_size)
            return False, log_message

    except Exception as e:
        log_message = ("Exception while getting free disk space on offsite, for the path: {} "
                       "exception message: {}."
                       .format(backup_path_at_offsite, str(e)))
        return False, log_message

    log_message = ("The estimated required free disk space on offsite for the path: {}, "
                   "is satisfied, the required space: {} {}, the available space: {} {}"
                   .format(backup_path_at_offsite, max_required_space_mb, block_size,
                           offsite_free_disk_space_mb, block_size))
    return True, log_message


def check_onsite_disk_space_restore(backup_path_offiste, host, bkp_restore_path, block_size):
    """
    Check whether the disk onsite has enough free space, to download the backup from offsite.

    :param backup_path_offiste: backup path to be restored from offsite.
    :param host: offsite machine to connect to, OFFSITE_USERNAME@OFFISTE_IP.
    :param bkp_restore_path: the destination path where the downloaded backup will be stored.
    :param block_size: whether MB, GB or TB, used with the log message for better readability.
    :return: tuple: true, informative message if there's enough disk space to restore the backup.
             or
             tuple: false, message if there's no enough disk space onsite to restore the backup.
             or
             tuple: false, exception message, in case of any failure.
    """
    valid, bkp_restore_path, log_msg = get_active_part_bkp_restore_destination(bkp_restore_path)
    if not valid:
        return False, log_msg

    valid, error_message, free_disk_space_onsite_mb = get_free_disk_space(bkp_restore_path)
    if not valid:
        return False, error_message

    valid, error_message, bkp_size_offsite_mb = get_offsite_backup_size(backup_path_offiste, host)
    if not valid:
        return False, error_message

    has_enough_space_to_restore = sufficient_onsite_disk_space_restore(bkp_size_offsite_mb,
                                                                       free_disk_space_onsite_mb)

    if has_enough_space_to_restore:
        log_msg = "The backup restore destination: {} has enough disk space: {} {}, " \
                  "to restore the backup: {} with size: {} {}."\
            .format(bkp_restore_path, free_disk_space_onsite_mb, block_size,
                    backup_path_offiste, bkp_size_offsite_mb, block_size)
        return True, log_msg
    else:
        log_msg = "The backup restore destination: {} doesn't have enough disk space " \
                  "to restore the backup: {} from offsite, " \
                  "the least required disk space: {} {}, " \
                  "but the available disk space: {} {}." \
            .format(bkp_restore_path, backup_path_offiste, bkp_size_offsite_mb, block_size,
                    free_disk_space_onsite_mb, block_size)
        return False, log_msg


def get_active_part_bkp_restore_destination(backup_destination):
    """
    Get the physical backup restore destination path, to perform disk space check on it.

    :param backup_destination: the provided backup restore destination path as input from console.
    :return: tuple: true, restore backup destination after shrinking, informative message,
             if the restore backup destination path or path head at least, exist.
             or
             tuple: false, if neither the restore backup destination path nor the path head exist.
    """
    starts_with_dot = str(backup_destination)[0] == '.'
    absolute_path = os.path.isabs(backup_destination)
    if not starts_with_dot and not absolute_path:
        log_message = "The provided backup restore destination '{}' is not a valid path, " \
                      "the path should start with '.' or '/' ."\
            .format(backup_destination)
        return False, backup_destination, log_message

    original_bkp_destination = backup_destination
    while not path_exist(backup_destination):
        if backup_destination.strip():
            backup_destination = shrink_bkp_destination(backup_destination)
        else:
            log_message = "No part of the backup destination path: {} exists."\
                .format(original_bkp_destination)
            return False, backup_destination, log_message

    log_message = "The backup destination to check after shrinking: " + backup_destination
    return True, backup_destination, log_message


def path_exist(path):
    """
    Check if a given path exist.

    :param path: the path to check.
    :return: true, if the path exists, false otherwise.
    """
    if os.path.exists(path):
        return True
    else:
        return False


def shrink_bkp_destination(backup_destination):
    """
    Shrink the provided backup restore destination path, in order to check the free disk space.

    :param backup_destination: the provided backup restore destination path as input from console.
    :return: backup restore destination path after shrinking.
    """
    bkp_dest_head, bkp_dest_tail = os.path.split(backup_destination)
    return bkp_dest_head


def get_offsite_backup_size(bkp_path_offsite, host):
    """
    Get the backup size from offsite, provided the path on offsite.

    This method can only be executed on offsite VM with a linux OS, not solaris(because of -b).
    Otherwise it will fail and stop the restore process.

    :param bkp_path_offsite: the full backup path on offsite disk.
    :param host: offsite machine to connect to, OFFSITE_USERNAME@OFFISTE_IP.
    :return: tuple: true, empty message to be ignored, the valid backup size.
             or
             tuple: false, exception message, -1, in case of any failure.
    """
    command = "du -bms " + bkp_path_offsite
    stdout, stderr = popen_communicate(host, command)

    std_output_list = stdout.split('\t')
    if std_output_list is None or len(std_output_list) <= 0:
        log_message = ("Invalid output from offsite while getting backup size for the path '{}'."
                       .format(bkp_path_offsite))
        return False, log_message

    log_message = ""
    try:
        backup_size = int(std_output_list[0])
    except Exception as e:
        log_message = ("Exception while getting backup size from offsite, for the path: {}, "
                       "exception message: {}"
                       .format(bkp_path_offsite, str(e)))
        return False, log_message, -1

    return True, log_message, backup_size


def sufficient_onsite_disk_space_restore(bkp_size_offsite_mb, free_disk_space_onsite_mb):
    """
    Check whether the disk onsite has sufficient free space to download the backup from offsite.

    :param bkp_size_offsite_mb: the required disk space to download and process the backup.
    :param free_disk_space_onsite_mb: the free disk space to check against.
    :return: True if the disk has sufficient free space, False otherwise.
    """
    if free_disk_space_onsite_mb <= bkp_size_offsite_mb:
        return False
    return True


def get_local_timestamp_since_epoch():
    """
    get the local timestamp, seconds since the epoch(1st Jan 1970).

    :return: timestamp with seconds and microseconds, example: 1537999522.94.
    """
    return time.time()


def truncate_microseconds_from_timestamp(time_stamp_value):
    """
    remove the microseconds part from the timestamp value.

    :param time_stamp_value: time represented in seconds and microseconds, example: 1537999522.94.
    :return: time represented in seconds only, example: 1537999522.0.
    """
    time_stamp_value = float(int(time_stamp_value))
    return time_stamp_value


def get_human_readable_time_from_local_timestamp():
    """
    get human readable local time, based on seconds since the epoch(1st Jan 1970).

    :return: human readable date time, in the format YY-MM-DD HH:MM:SS, example 2018-09-26 23:22:26.
    """
    return format_time(truncate_microseconds_from_timestamp(get_local_timestamp_since_epoch()),
                       '%Y-%m-%d %H:%M:%S')


def format_time(elapsed_time, time_format="%H:%M:%S"):
    """
    Display a float time according to the format string.
    :param elapsed_time: float time representation.
    :param time_format: format string.

    :return: formatted time.
    """
    return time.strftime(time_format, time.gmtime(elapsed_time))


def log_cli_arguments(logger):
    """
    Log passed BUR arguments through CLI.

    :param logger: logger object.
    """
    sys.argv.pop(0)  # remove the script's name from the argument list.
    provided_args = str(sys.argv)

    logger.log_info("Running BUR with the following arguments: {}".format(provided_args))


def is_dir(root_path, logger):
    """
    Check whether the informed path is a directory or not.

    :param root_path: string path.
    :param logger:    logger object.

    :return: true, if path exists and is a directory;
             false otherwise.
    """
    if not os.path.exists(root_path):
        logger.error("Path '{}' does not exist.".format(root_path))
        return False

    if not os.path.isdir(root_path):
        logger.error("Path '{}' is not a folder.".format(root_path))
        return False

    return True


def validate_volume_level_metadata(backup_path, logger):
    """
    Go through the volume list and validate its content against metadata file.

    :param backup_path: backup path.
    :param logger:      logger object.

    :return: true, if the backup was correctly validated,
             false, otherwise.
    """
    logger.info("Validating backup '{}' against its volumes' metadata.".format(backup_path))

    for volume_folder in os.listdir(backup_path):
        volume_path = os.path.join(backup_path, volume_folder)

        if not os.path.isdir(volume_path):
            continue

        metadata_file = glob.glob(os.path.join(volume_path, str('*' + METADATA_FILE_SUFFIX)))
        if len(metadata_file) != 1 or not is_dir(volume_path, logger) or not \
                validate_metadata(volume_path, metadata_file[0], logger):
            logger.error("Backup '{}' could not be validated. Checking the next one."
                         .format(backup_path))
            return False

    return True


def validate_metadata(root_path, metadata_file_name, logger):
    """
    Validate the metadata file from a specific volume against the system.

    :param root_path:          volume root path for a specific deployment.
    :param metadata_file_name: metadata file name.
    :param logger:             logger object.

    :return: true, if all files specified in the metadata are found and have the same md5 code;
             false otherwise.
    """
    logger.info("Validating metadata file {}.".format(metadata_file_name))

    if not os.path.exists(metadata_file_name):
        logger.error("Metadata error: File '{}' does not exist.".format(metadata_file_name))
        return False

    try:
        with open(metadata_file_name) as metadata_file:
            metadata_json = json.load(metadata_file)
    except Exception as e:
        logger.error(e)
        logger.error("Metadata error: Could not parse metadata file '{}'."
                     .format(metadata_file_name))
        return False

    file_list = metadata_json[MetadataKeys.objects.name]

    file_list_size = len(file_list)
    file_list_system = len(os.listdir(root_path))

    # Ignore _metadata and _sha256file files.
    if file_list_size != file_list_system - 2:
        logger.error("Metatada error: Invalid number of files (informed {}, found {})."
                     .format(file_list_size, file_list_system))
        return False

    for file_dic in file_list:

        if len(file_dic.keys()) != 1:
            logger.error("Metatada error: File entry is malformed.")
            return False

        metadata_file_path = file_dic.keys()[0]
        system_file_path = os.path.join(root_path, metadata_file_path)

        if not os.path.exists(system_file_path):
            logger.error("Metatada error: File '{}' does not exist in the system."
                         .format(system_file_path))
            return False

        if MetadataKeys.md5.name not in file_dic[metadata_file_path].keys():
            logger.error("Metatada error: Missing key {} for file {}."
                         .format(MetadataKeys.md5.name, metadata_file_path))
            return False

    return True
