##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from enum import Enum
import os
import subprocess

RSYNC_CMD = "rsync"
RSYNC_ARG = "-azhe ssh"

RsyncOutputSummaryItem = Enum('RsyncOutputSummaryItem',
                              'total_files, created, deleted, transferred, rate, speedup')


class RsyncManager:
    """
    Class used to encapsulate rsync commands to transfer files over the network.

    It basically sends/receives data from one location to another.
    When sending files from local to remote, it keeps track of whether the file(s) was
    successfully sent or not after a given number of tries.
    """

    def __init__(self, source_path, destination_path, retry=3):
        """
        Initialize Rsync Manager class.

        :param source_path: path of the source file to be transferred.
        :param destination_path: destination location to send the file.
        :param retry: number of tries in case of failure.
        """
        self.source_path = source_path
        self.destination_path = destination_path
        self.retry = retry

    class RsyncOutput:
        """Class used to store relevant output information of rsync commands."""

        def __init__(self, summary_dic):
            """
            Initialize Rsync Output class.

            :param summary_dic: dictionary with data parsed from the rsync output.
            """
            self.n_files = summary_dic[RsyncOutputSummaryItem.total_files.name]
            self.n_created_files = summary_dic[RsyncOutputSummaryItem.created.name]
            self.n_deleted_files = summary_dic[RsyncOutputSummaryItem.deleted.name]
            self.n_transferred_files = summary_dic[RsyncOutputSummaryItem.transferred.name]
            self.speedup = summary_dic[RsyncOutputSummaryItem.speedup.name]
            self.rate = summary_dic[RsyncOutputSummaryItem.rate.name]

        def __str__(self):
            """Representation of stored data in object."""
            return "RsyncOutput:\n" \
                   "Number of files: {}\n" \
                   "Number of created files: {}\n" \
                   "Number of deleted files: {}\n" \
                   "Number of transferred files: {}\n" \
                   "Speedup: {}\n" \
                   "Transfer rate: {}\n".format(self.n_files, self.n_created_files,
                                                self.n_deleted_files, self.n_transferred_files,
                                                self.speedup, self.rate)

    def get_number_of_files_to_send(self):
        """
        Calculate the number of files to be sent in the informed source_path.

        It considers that the path can be either a single file or a folder with other
        files or folders inside.

        If source_path refers to a single file, returns 1, otherwise go through the folder's
        content and count the number of files.

        :return: number of files to be transferred.
        """
        if not os.path.exists(self.source_path):
            raise Exception("Specified path '{}' does not exist".format(self.source_path))

        n_files = 0
        if os.path.isdir(self.source_path):
            for file_name in os.listdir(self.source_path):
                if not os.path.isdir(os.path.join(self.source_path, file_name)):
                    n_files += 1
        else:
            n_files = 1

        if n_files == 0:
            raise Exception("There is no file in '{}' to be copied to the remote location."
                            .format(self.source_path))

        return n_files

    @staticmethod
    def parse_number_of_file_key_value(rsync_output_line):
        """
        Given a line from the rsync output, this function gets the number of file measurement as
        well as the text field it is being referred.

        Raise an exception is something gets wrong.

        :param rsync_output_line: rsync output line with the 'number of' measurement.

        :return: key, value pair (measurement string, number of files).
        """
        if "number of" not in rsync_output_line:
            raise Exception("Line '{}' does not contain a number of measurement.".format(
                rsync_output_line))

        par = rsync_output_line.find('(')
        if par != -1:
            rsync_output_line = rsync_output_line[0:par - 1]

        if rsync_output_line.find(":") == -1:
            raise Exception("Could not parse rsync output line: {}.".format(rsync_output_line))

        number_of_files = rsync_output_line.split(':')[1].strip()

        key = RsyncOutputSummaryItem.total_files.name

        if RsyncOutputSummaryItem.transferred.name in rsync_output_line:
            key = RsyncOutputSummaryItem.transferred.name
        elif RsyncOutputSummaryItem.deleted.name in rsync_output_line:
            key = RsyncOutputSummaryItem.deleted.name
        elif RsyncOutputSummaryItem.created.name in rsync_output_line:
            key = RsyncOutputSummaryItem.created.name

        return key, number_of_files

    @staticmethod
    def parse_output(output):
        """
        Parse the output of a rsync execution.

        Collect relevant information to be stored in a RsyncOutput object.

        :param output: output after a rsync execution.

        :return: false, if it was not possible to parse the output,
                 RsyncOutput object with the retrieved information.
        """
        if output is None or not str(output).strip():
            raise Exception("Empty output.")

        lines = str(output).lower().split('\n')

        summary_dic = {}
        for summary_item in RsyncOutputSummaryItem:
            summary_dic[summary_item.name] = None

        for line in lines:
            if "number of" in line:

                key, number_of_files = RsyncManager.parse_number_of_file_key_value(line)

                summary_dic[key] = number_of_files

            elif "bytes/sec" in line:
                line_split = line.split(" ")

                item_index = 0
                for item in line_split:
                    if "bytes/sec" in item.strip():
                        break
                    item_index += 1

                summary_dic[RsyncOutputSummaryItem.rate.name] = line_split[item_index - 1]

            elif RsyncOutputSummaryItem.speedup.name in line:

                speedup_value = line[line.find(RsyncOutputSummaryItem.speedup.name) + len(
                    RsyncOutputSummaryItem.speedup.name) + len(" is "):]

                summary_dic[RsyncOutputSummaryItem.speedup.name] = speedup_value

        for item in summary_dic:
            if summary_dic[item] is None:
                raise Exception("Parsing did not find valid tags in the output.")

        return RsyncManager.RsyncOutput(summary_dic)

    def receive(self):
        """
        Try to receive files from a remote location.

        Remote location is specified by the source_path.
        Destination location is specified by the destination_path.

        An exception is raised if some problem happens during the process.

        :return: RsyncOutput object with the output information of the command.
        """
        try:
            output = subprocess.check_output([RSYNC_CMD, RSYNC_ARG, '--stats', self.source_path,
                                              self.destination_path], stderr=subprocess.PIPE)

            return self.parse_output(output)

        except subprocess.CalledProcessError as cp:
            raise Exception("A process error occurred while receiving file: Error code {}"
                            .format(cp.returncode))
        except Exception as e:
            raise Exception("An error occurred while receiving file: {}".format(e.message))

    def send(self):
        """
        Try to send local file(s) referred by source_path to the destination_path location.

        It will try to send the file as many times as specified by the retry variable.

        An exception will be raised if the maximum number of tries is reached without success.

        :return: RsyncOutput object with the output information of the command.
        """
        try:
            n_files = self.get_number_of_files_to_send()

            for current_try in range(1, self.retry + 1):
                output = subprocess.check_output([RSYNC_CMD,
                                                  RSYNC_ARG,
                                                  '--stats',
                                                  self.source_path,
                                                  self.destination_path],
                                                 stderr=subprocess.PIPE)

                rsync_output = self.parse_output(output)

                if not isinstance(rsync_output, RsyncManager.RsyncOutput):
                    raise Exception("Can't parse the output from rsync command.")

                if int(rsync_output.n_transferred_files) == int(n_files):
                    return rsync_output

                if current_try == self.retry:
                    raise Exception("Can't transfer file(s) to remote server:\n"
                                    "Number of tries: {}\n"
                                    "Number of files to be transferred: {}\n"
                                    "Number of transferred files: {}\n"
                                    .format(self.retry, n_files, rsync_output.n_transferred_files))
        except subprocess.CalledProcessError as cp:
            raise Exception("An error occurred while transferring file: Error code {}."
                            .format(cp.returncode))
        except Exception as e:
            raise Exception("Error occurred while transferring file: {}".format(e.message))


'''
#Sample of usage:

try:
    RsyncManager("local_path", "user@ip:remote_path").copy_to_remote()
except Exception as e:
    print(e)
print("Finished!")
'''
