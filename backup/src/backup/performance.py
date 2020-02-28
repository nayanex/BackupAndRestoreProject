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
from enum import Enum

from utils import format_time, VolumeOutputKeys

SCRIPT_PATH = os.path.dirname(__file__)

PERFORMANCE_PER_BACKUP_FILE_NAME = "performance_per_backup.csv"
PERFORMANCE_PER_VOLUME_SUFFIX_FILE_NAME = "_performance_per_volume.csv"

PerformanceTimeIndex = Enum('PerformanceTimeIndex', 'COMPRESS_TIME, ENCRYPT_TIME')


def collect_performance_data(method):
    """
    Decorator function.

    Collect performance data after executing a backup operation.

    :param method: decorated method.
    :return: tuple (bur_id, backup_output, total_time time).
    """
    def get_performance(*args, **kw):
        bur_id, backup_output_dic, total_time = method(*args, **kw)

        BURPerformance(bur_id, backup_output_dic, total_time).update_csv_reports()

        return bur_id, backup_output_dic, total_time

    return get_performance


class BURPerformance:
    """
    Handle data about the performance of the backup process.

    It also provides functions to calculate and generate a csv report.
    """

    def __init__(self, bur_id, backup_output_dic, total_time):
        """
        Initialize Backup Performance class.

        :param bur_id: id of the backup according to the operation: upload (customer id)/download
        (backup tag)
        :param backup_output_dic: dictionary with the output of the backup operation process.
        :param total_time: total time to process whole backup..
        """
        self.bur_id = bur_id
        self.backup_output_dic = backup_output_dic
        self.total_time = total_time

    def __str__(self):
        """
        To string method.

        :return: string with the string representation of the class.
        """
        total_time = format_time(self.total_time)

        return "{}, {}\n".format(self.bur_id, total_time)

    def update_csv_reports(self):
        """
        Store collected performance data from the backup process into csv files.

        Two csv files will be updated: Consolidated data per backup, Time data per volume.

        The report contains the following consolidated data:
        """
        performance_file_root_path = os.path.join(os.path.expanduser("~"), "backup")
        if not os.access(performance_file_root_path, os.R_OK):
            performance_file_root_path = os.path.join(SCRIPT_PATH)

        self.update_per_backup_report(performance_file_root_path)
        self.update_per_volume_report(performance_file_root_path)

    def update_per_backup_report(self, performance_file_path):
        """
        Update the file related to the consolidated report per backup.

        :param performance_file_path: path to store the report file.
        """
        report_file_path = os.path.join(performance_file_path, PERFORMANCE_PER_BACKUP_FILE_NAME)

        if not os.path.exists(report_file_path):
            f = open(report_file_path, 'a')
            f.write(str(BURPerformance.get_per_backup_header()))
            f.close()

        with open(report_file_path, 'a') as report_file:
            report_file.write(self.__str__())

    def update_per_volume_report(self, performance_file_path):
        """
        Update the file related to the report per volume.

        :param performance_file_path: path to store the report file.
        """
        report_file_path = os.path.join(performance_file_path, "{}{}".
                                        format(self.bur_id,
                                               PERFORMANCE_PER_VOLUME_SUFFIX_FILE_NAME))

        if not os.path.exists(report_file_path):
            f = open(report_file_path, 'a')
            f.write(str(BURPerformance.get_per_volume_header()))
            f.close()

        for volume_name in self.backup_output_dic.keys():
            proc_time = self.backup_output_dic[volume_name][VolumeOutputKeys.processing_time.name]
            tar_time = self.backup_output_dic[volume_name][VolumeOutputKeys.tar_time.name]
            transfer_time = self.backup_output_dic[volume_name][VolumeOutputKeys.transfer_time.name]

            total_proc_time = float(proc_time) + float(tar_time)
            total_time = total_proc_time + float(transfer_time)

            rsync_output = self.backup_output_dic[volume_name][VolumeOutputKeys.rsync_output.name]

            with open(report_file_path, 'a') as report_file:
                report_file.write("{}, {}, {}, {}, {}, {}, {}, {}\n".format(volume_name,
                                                                            format_time(proc_time),
                                                                            format_time(tar_time),
                                                                            format_time(
                                                                                total_proc_time),
                                                                            format_time(
                                                                                transfer_time),
                                                                            format_time(total_time),
                                                                            rsync_output.speedup,
                                                                            rsync_output.rate))

    @staticmethod
    def get_per_backup_header():
        """
        Return the header of the performance report per backup.

        :return: header.
        """
        return "BUR_ID, TOTAL_TIME\n"

    @staticmethod
    def get_per_volume_header():
        """
        Return the header of the performance report per volume.

        :return: header.
        """
        return "VOLUME_NAME, COMPRESSION_ENCRYPTION_TIME, TAR_TIME, TOTAL_PROCESSING_TIME, " \
               "TRANSFER_TIME, TOTAL_TIME, SPEEDUP, RATE\n"
