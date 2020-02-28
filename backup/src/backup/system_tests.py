#!/usr/bin/env python

import os
import sys
import time
import datetime
import argparse
import subprocess
from subprocess import Popen, PIPE
from logger import CustomLogger
from thread_pool import SingleThread
from utils import create_path, get_home_dir, remove_path

OPERATION_UPLOAD = "1"
OPERATION_DOWNLOAD = "2"

TIMEOUT = 1

VMSTAT = "vmstat"

"""
# for a local linux VM
VMSTAT_HEADER = "r, b, swpd, free, buff, cache, si, so, bi, bo, in, cs, us, sy, id, wa, st, " \
                "date, time"
"""
# for nfs(solaris)
VMSTAT_HEADER = "r, b, w, swap, free, re, mf, pi, po, fr, de, sr, s0, s1, s2, s3, in, sy, cs, " \
                "us, sy, id"

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

OUTPUT_ROOT_PATH = os.path.join(get_home_dir(), "backup")
VMSTAT_ROOT_PATH = os.path.join(OUTPUT_ROOT_PATH, "vmstat_collect")

DEFAULT_RESTORE_PATH = "/data1/rpcbackups/staging04/bur-test/restore_test"
DEFAULT_LOGS_PATH = "/data1/rpcbackups/staging04/bur-test/bur-logs"

global restore_folder
restore_folder = ""

global log_folder
log_folder = ""

global logger
logger = CustomLogger(SCRIPT_FILE, "")


def write_vmstat_to_file(vmstat_file_path, vmstat_output):
    vmstat_output_split = vmstat_output.split('\n')

    content_to_write = ""
    for vmstat_line_index in range(0, len(vmstat_output_split) - 1):
        if vmstat_line_index <= 1:
            if not os.path.exists(vmstat_file_path):
                content_to_write += vmstat_output_split[vmstat_line_index] + "\n"

        elif vmstat_line_index == 2:
            timestamp = str(datetime.datetime.now()).split('.')[0]

            data_line = vmstat_output_split[vmstat_line_index] + " " + timestamp

            content_to_write += data_line + "\n"

    with open(vmstat_file_path, "a") as f:
        f.write(content_to_write)


def write_vmstat_to_csv(csv_file_path, line):

    if not os.path.exists(csv_file_path):
        with open(csv_file_path, "a") as csv_file:
            csv_file.write(VMSTAT_HEADER + "\n")

    line_split = line.split(' ')
    counter_data = 0
    number_data = len(line_split)

    csv_line = ""
    for data in line_split:
        if not data.strip():
            counter_data += 1
            continue

        csv_line += data
        if counter_data < number_data - 1:
            csv_line += ","

        counter_data += 1

    with open(csv_file_path, "a") as csv_file:
        csv_file.write(csv_line + "\n")


def vmstat(method):
    def get_vmstat(*args, **kw):
        operation_name = method.__name__

        if not create_path(VMSTAT_ROOT_PATH):
            logger.error("Error to create root path for vmstat: '{}'.".format(VMSTAT_ROOT_PATH))
            return False

        if 'vmstat_file_name' in kw:
            vmstat_file_name = kw['vmstat_file_name']
            del kw['vmstat_file_name']
        else:
            vmstat_file_name = operation_name

        vmstat_file_path = os.path.join(VMSTAT_ROOT_PATH, "{}_{}.txt".format(VMSTAT,
                                                                             vmstat_file_name))

        th = SingleThread(operation_name, None, method, *args, **kw)

        th.start()

        while th.isAlive():
            try:
                vmstat_proc = Popen(VMSTAT, stdout=PIPE, shell=True)
                vmstat_output, err = vmstat_proc.communicate()

                if err is not None:
                    raise Exception("Popen error: {}.".format(err))

                write_vmstat_to_file(vmstat_file_path, vmstat_output)

            except Exception as e:
                logger.log_error_exit("Could not execute vmstat command due to {}.".format(
                    e.message), -1)

            time.sleep(TIMEOUT)

        return True

    return get_vmstat


def get_vmstat_csv_files():
    if not os.path.exists(VMSTAT_ROOT_PATH):
        return False

    if not os.path.isdir(VMSTAT_ROOT_PATH):
        return False

    for vmstat_file_name in os.listdir(VMSTAT_ROOT_PATH):
        if ".csv" in vmstat_file_name:
            continue

        output_csv_file = os.path.join(VMSTAT_ROOT_PATH, "{}.csv".format(vmstat_file_name))

        if os.path.exists(output_csv_file):
            remove_path(output_csv_file)

        with open(os.path.join(VMSTAT_ROOT_PATH, vmstat_file_name)) as vmstat_file:
            for cnt, line in enumerate(vmstat_file):
                if cnt < 2:
                    continue

                if not line.strip():
                    continue

                write_vmstat_to_csv(output_csv_file, line.strip())


def run_popen(command_list, shell=False):
    if not command_list:
        return None

    command = ""
    for cmd_item in command_list:
        command += cmd_item + " "

    logger.info("Running command: {}.".format(command))

    if not shell:
        with open(os.devnull, "w") as devnull:
            return Popen(command_list, stdout=devnull, stderr=devnull)

    return Popen(command, shell=True)


def run_bur_process(param_list=[], verbose=False):
    full_cmd = ["bur"] + param_list + ["--do_cleanup", "0"]

    return run_popen(full_cmd, verbose)


def get_bur_upload_single_instance_process(customer_name="", verbose=False):
    cmd_par = []
    if customer_name.strip():
        cmd_par = ["--script_option", OPERATION_UPLOAD, "--customer_name", customer_name,
                   "--log_root_path", os.path.join(log_folder, customer_name)]

    return run_bur_process(cmd_par, verbose)


def get_bur_download_single_instance_process(backup_tag="", verbose=False):
    if not backup_tag.strip():
        return None

    cmd_par = ["--script_option", OPERATION_DOWNLOAD, "--backup_destination", restore_folder,
               "--backup_tag", backup_tag, "--log_root_path", os.path.join(log_folder, backup_tag)]

    return run_bur_process(cmd_par, verbose)


@vmstat
def execute_bur_upload_single_instance(customer_name="", verbose=False):
    p = get_bur_upload_single_instance_process(customer_name, verbose)
    if p is not None:
        p.wait()


@vmstat
def execute_bur_download_single_instance(backup_tag="", verbose=False):
    p = get_bur_download_single_instance_process(backup_tag, verbose)
    if p is not None:
        p.wait()


@vmstat
def execute_bur_multiple_instances(operation="", input_list=[], verbose=False):
    if not operation.strip():
        logger.error("Empty operation.")
        return

    if operation == OPERATION_DOWNLOAD:
        execute_bur_function = get_bur_download_single_instance_process
    elif operation == OPERATION_UPLOAD:
        execute_bur_function = get_bur_upload_single_instance_process
    else:
        logger.error("Invalid operation: {}.".format(operation))
        return

    instance_dic = {}
    for input_value in input_list:
        input_value = input_value.strip()
        if input_value in instance_dic.keys():
            logger.warning("Ignoring repeated value: {}.".format(input_value))
            continue

        instance_dic[input_value] = execute_bur_function(input_value, verbose)

    if len(instance_dic.keys()) > 0:
        check_alive_process(instance_dic)


def check_alive_process(process_dic):
    while True:
        alive_process_dic = {}
        for key in process_dic.keys():
            if process_dic[key] is None:
                continue

            if process_dic[key].poll() is None:
                alive_process_dic[key] = process_dic[key]
            else:
                logger.info("Process has finished: {}.".format(key))

        if len(alive_process_dic.keys()) == 0:
            break

        process_dic = alive_process_dic


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--test_option", default=1,
                        help="Execute single (1) or multiple instance (2) test.")
    parser.add_argument("--customer_list",
                        help="List of customer names to execute the test (e.g. c1, c2, c3).")
    parser.add_argument("--backup_tag_list",
                        help="List of backup tags to execute the test (e.g. c1, c2, c3).")
    parser.add_argument("--restore_destination", nargs='?', default=DEFAULT_RESTORE_PATH)
    parser.add_argument("--log_root_path", default=DEFAULT_LOGS_PATH,
                        help="Specify a valid path to store the logs.")
    parser.add_argument("--verbose", default=False, help="Shows BUR logs.")
    parser.add_argument("--usage", action="store_true", help="Display detailed help.")

    args = parser.parse_args()

    if args.usage:
        logger.log_info("Example of usage:\n\n"
                        "(1) Running sequential upload for CUSTOMER_0 and CUSTOMER_1, "
                        "followed by a sequential download of backup tags 2018 and 2019:\n\n"
                        "    python system_tests.py --customer_list \"CUSTOMER_0, CUSTOMER_1\" "
                        "--backup_tag_list \"2018, 2019\" --test_option 1 --log_root_path "
                        "\"path_to_logs\" --restore_destination \"path_to_restore\" ""\n\n"
                        "(2) To run parallel upload followed by parallel download, "
                        "just use --test_option 2.\n\n"
                        "(3) To see the stdout from BUR use --verbose True.\n")
        sys.exit(1)

    try:
        test_option = int(args.test_option)

        if not args.log_root_path.strip():
            raise Exception("--log_root_path should not be empty.")

        if not create_path(args.log_root_path):
            raise Exception("--log_root_path '{}' could not be created.".format(
                args.log_root_path))

        log_folder = args.log_root_path

        if args.customer_list is None:
            raise Exception("--customer_list should not be empty.")

        customer_list = str(args.customer_list).split(",")

        if args.backup_tag_list is None:
            raise Exception("--backup_tag_list should not be empty.")

        backup_tag_list = str(args.backup_tag_list).split(",")

        if args.restore_destination is not None:
            restore_folder = str(args.restore_destination)
            if not restore_folder.strip():
                raise Exception("--restore_destination, can't be empty ")
        else:
            raise Exception("--restore_destination is null.")

        starts_with_dot = str(restore_folder)[0] == '.'
        absolute_path = os.path.isabs(restore_folder)
        if not starts_with_dot and not absolute_path:
            raise Exception("--restore_destination, is a path, it should start with '.' '/'")

        verbose = False
        if str(args.verbose).lower() in ("yes", "true", "t", "1"):
            verbose = True

    except Exception as e:
        logger.log_error_exit("Invalid input value due to: {}".format(e), -1)

    logger.log_info("Performing system tests with the following data: Customer list: {}, "
                    "Backup tag list: {}.".format(customer_list, backup_tag_list))

    if int(args.test_option) == 1:
        logger.log_info("Run backup upload single instance.")

        for customer in customer_list:
            customer = customer.strip()
            logger.log_info("Running backup upload for customer {}.".format(customer))
            execute_bur_upload_single_instance(customer, verbose,
                                               vmstat_file_name="upload_{}".format(customer))

        logger.log_info("The whole upload procedure finished.")

        logger.log_info("Run backup download single instance.")
        for backup_tag in backup_tag_list:
            backup_tag = backup_tag.strip()
            logger.log_info("Running backup download for tag {}.".format(backup_tag))
            execute_bur_download_single_instance(backup_tag, verbose,
                                                 vmstat_file_name="download_{}".format(backup_tag))

    elif int(args.test_option) == 2:
        logger.log_info("Run backup upload parallel.")
        execute_bur_multiple_instances(OPERATION_UPLOAD, customer_list, verbose,
                                       vmstat_file_name="upload_parallel")

        logger.log_info("The whole upload procedure finished.")

        logger.info("Run backup download parallel.")
        execute_bur_multiple_instances(OPERATION_DOWNLOAD, backup_tag_list, verbose,
                                       vmstat_file_name="download_parallel")

    logger.log_info("Getting vmstat csv files. Storing into path '{}'.".format(VMSTAT_ROOT_PATH))
    get_vmstat_csv_files()

    logger.info("System test finished!!!")
