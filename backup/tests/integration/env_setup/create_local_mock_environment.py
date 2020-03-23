import argparse
import datetime
import hashlib
import json
import os
import threading

from backup.utils import get_path_to_docs, remove_path

CUSTOMER_NAME = "customer_deployment_"
VOLUME_NAME = "volume"
FILE_NAME = "volume_file"

DEFAULT_RPC_DIR = os.path.join(get_path_to_docs(), 'rpc_bkps')
DEFAULT_FILE_SIZE = 100 * 1024
DEFAULT_NUM_FILES = 3
DEFAULT_NUM_VOLUMES = 3
DEFAULT_NUM_BKPS = 2
DEFAULT_NUM_CUSTOMERS = 2


class MyThread(threading.Thread):
    """Thread class to create the mock environment in parallel."""

    def __init__(self, root_path, customer_name, num_bkps, num_volumes, num_files, reset=False):
        """
        Initialize custom thread that override Thread.

        :param root_path:     root path where the files will be stored.
        :param customer_name: customer name.
        :param num_bkps:      number of backups.
        :param num_volumes:   number of volumes.
        :param num_files:     number of files.
        :param reset:         whether to delete the previous environment or not.
        """
        threading.Thread.__init__(self)

        self.root_path = root_path
        self.customer_name = customer_name
        self.num_bkps = num_bkps
        self.num_volumes = num_volumes
        self.num_files = num_files
        self.reset = reset

    def run(self):
        """Execute this thread."""
        generate_customer_data(self.root_path,
                               self.customer_name,
                               self.num_bkps,
                               self.num_volumes,
                               self.num_files,
                               self.reset)


def get_bkp_dir_date(current_date):
    """
    Get the current date to create the backup folders name.

    :param current_date: current date.

    :return: backup folder name based on the date.
    """
    month = str(current_date.month)
    if len(month) == 1:
        month = "0{}".format(month)

    day = str(current_date.day)
    if len(day) == 1:
        day = "0{}".format(day)

    return "{}-{}-{}".format(current_date.year, month, day)


def create_mock_file(rpc_path, size):
    """
    Create mock file to be stored in the volumes folders.

    :param rpc_path: path where the mock environment will be stored.
    :param size:     size of the file.

    :return:     path of the created file.
    """
    aux_file_path = os.path.join(rpc_path, FILE_NAME)

    if not os.path.exists(aux_file_path):
        with open(aux_file_path, 'wb') as f:
            f.write(os.urandom(size))

    return aux_file_path


def generate_customer_data(root_path, customer_name, num_bkps, num_volumes, num_files, reset=False):
    """
    Generate the backup folder structure for each customer according to the informed parameters.

    :param root_path:     path in with the files will be created.
    :param customer_name: name of the customer.
    :param num_bkps:      number of backups to be created.
    :param num_volumes:   number of volumes to be created.
    :param num_files:     number of files to be created.
    :param reset:         whether delete or not the previous mock environment.
    """
    customer_deployment_path = os.path.join(root_path, customer_name)

    if os.path.exists(customer_deployment_path):
        if reset:
            remove_path(customer_deployment_path)
            os.makedirs(customer_deployment_path)
    else:
        os.makedirs(customer_deployment_path)

    current_date = datetime.datetime.today()

    idx = 0

    if num_files > 0:
        mock_file_size = os.path.getsize(mock_file_path)

    for d in range(num_bkps, 0, -1):
        day_diff = datetime.timedelta(days=d)
        customer_bkp_path = os.path.join(customer_deployment_path,
                                         get_bkp_dir_date(current_date - day_diff))

        if not os.path.exists(customer_bkp_path):
            os.makedirs(customer_bkp_path)
        else:
            continue

        metadata = {"backup_description": "mock_backup", "backup_id": idx,
                    "backup_name": "{}_Backup_{}".format(customer_name, idx),
                    "created_at": str(current_date), "parent_id": "null", "version": "1.0.0",
                    "volume_meta": ""}

        idx += 1

        for k in range(0, num_volumes):
            metadata["volume_id"] = k

            customer_volume_path = os.path.join(customer_bkp_path, VOLUME_NAME + str(k))
            if not os.path.exists(customer_volume_path):
                os.makedirs(customer_volume_path)
            else:
                continue

            metadata["objects"] = []

            for j in range(0, num_files):
                file_name = "{}{}.dat".format(FILE_NAME, str(j))
                object_info = {}
                metadata["objects"].append(object_info)
                volume_data_path = os.path.join(customer_volume_path, file_name)
                os.system("cp {} {}".format(mock_file_path, volume_data_path))
                object_info[file_name] = {"compression": "none",
                                          "length": mock_file_size,
                                          "md5": md5(volume_data_path),
                                          "offset": 0}

            create_metadata_file(customer_volume_path, "{}_backup_metadata".format(k), metadata)
            open(os.path.join(customer_volume_path, "{}_backup_sha256file".format(k)), 'w').close()

        open(os.path.join(customer_bkp_path, "BACKUP_OK"), 'w').close()


def md5(filename):
    """
    Calculate md5 from the informed file.

    :param filename: file path.

    :return:         md5 code.
    """
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def create_metadata_file(path, filename, content):
    """
    Create metadata file for the specified volume.

    :param path:     volume path.
    :param filename: name of the metadata file.
    :param content:  json structure with the content to be stored in the metadata file.
    """
    metadata_file = os.path.join(path, filename)
    with open(metadata_file, 'w') as outfile:
        json.dump(content, outfile)


def create_mock_env(rpc_path, num_customers, num_bkps, num_volumes=DEFAULT_NUM_VOLUMES,
                    num_files=DEFAULT_NUM_FILES, file_size=DEFAULT_FILE_SIZE, reset=False):
    """
    Create the whole test environment based on the input parameters.

    :param rpc_path:      root path where the files will be stored.
    :param num_customers: number of customers.
    :param num_bkps:      number of backups.
    :param num_volumes:   number of volumes.
    :param num_files:     number of files.
    :param reset:         whether to delete the previous environment or not.
    """
    if not os.path.exists(rpc_path):
        os.makedirs(rpc_path)

    global mock_file_path
    mock_file_path = ""

    if num_files > 0:
        mock_file_path = create_mock_file(rpc_path, file_size)

    if mock_file_path == "" and num_files > 0:
        print("Mock file could not be created.")
        return

    ths = []
    for i in range(0, num_customers):
        try:
            th = MyThread(rpc_path, CUSTOMER_NAME + str(i), num_bkps, num_volumes, num_files, reset)
            th.start()
            ths.append(th)
        except Exception as e:
            print(e)

    for t in ths:
        t.join()

    if num_files > 0:
        remove_path(mock_file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc_path", nargs='?', default=DEFAULT_RPC_DIR,
                        help="Provide the path in which the mock will be placed.")
    parser.add_argument("--num_customers", nargs='?', default=DEFAULT_NUM_CUSTOMERS,
                        help="Provide the number of customers.")
    parser.add_argument("--num_bkps", nargs='?', default=DEFAULT_NUM_BKPS,
                        help="Provide the number of backups.")
    parser.add_argument("--num_volumes", nargs='?', default=DEFAULT_NUM_VOLUMES,
                        help="Provide the number of volumes per customer.")
    parser.add_argument("--num_files", nargs='?', default=DEFAULT_NUM_FILES,
                        help="Provide the number of files per volume.")
    parser.add_argument("--file_size", nargs='?', default=DEFAULT_FILE_SIZE,
                        help="Provide the file size.")
    parser.add_argument("--reset", nargs='?', default="True",
                        help="Weather reset or not the previous mock environment.")

    args = parser.parse_args()

    create_mock_env(args.rpc_path,
                    int(args.num_customers),
                    int(args.num_bkps),
                    int(args.num_volumes),
                    int(args.num_files),
                    int(args.file_size),
                    bool(args.reset))
