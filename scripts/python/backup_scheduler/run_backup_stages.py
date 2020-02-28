#!/usr/bin/env python
##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import ConfigParser
import datetime
import getopt
import json
import logging
import os
import subprocess
import sys
import requests
import time

from backup_handlers import *
from backup_utils import *
from workflows import *

from distutils.version import LooseVersion
from requests.exceptions import RequestException

CUSTOMER = None
BACKUP_TAG = None
BACKUP_ID = None
STAGE = None

SEND_MAIL = True
MAIL_TO = None
MAIL_URL = None

SCRIPT_NAME = os.path.basename(__file__)
DIR = os.path.dirname(os.path.realpath(__file__))
CONF_FILE = DIR + '/' + SCRIPT_NAME.split('.')[0] + '.ini'

LOG = logging.getLogger(SCRIPT_NAME)

USAGE = """
Usage: {script} --customer=CUSTOMER --stage=STAGE [--tag=TAG] [--id=ID] [--mail=MAIL_BOOL ]

Run a stage in the backup sequence for a customer.

Where:
CUSTOMER is the name of the customer (tenancy/deployment_id)

STAGE     is one of:
          STORAGE_WF - Check for storage workflows on all tenancies
          ALL_WF     - Check for any workflow on 'this' tenancy
          RETENTION  - Set the retention policy for backups
          BACKUP     - Trigger Backup
          RUNNING    - Check if Backup is running (requires ID)
          CHECK      - Check state of finished backup (requires ID)
          VALIDATE   - Trigger Backup validation workflow
          METADATA   - Backup Metadata (requires ID)
          FLAG       - Create success flag in backup directory
          ALL        - To Run all the above stages in sequence

TAG       is a label for the backup, needed for every stage after BACKUP.
          If TAG is not supplied for ALL and BACKUP then one will be generated.
ID        is the backup id, required for some stages
MAIL_BOOL is true/false to control email notification (defaut is true)
"""

def usage(err=1):
    """Display usage and exit.

    Args:
       exit_val: numerical exit code

    Returns: Exits script with exit_val

    Raises: Nothing
    """
    conf_file = os.path.basename(CONF_FILE)
    err_exit(USAGE.format(script=SCRIPT_NAME, cfg=conf_file), err)


def mailer(subject, message):
    if not SEND_MAIL:
        return

    sender = CUSTOMER + "@ericsson.com"
    if not send_mail(MAIL_URL, sender, MAIL_TO, subject, message):
        LOG.warning("Failed to send mail to %s, %s" %(MAIL_TO, message))


def parse_args(argv):
    """Handle command line arguments.  Sets global vars for
       backup tag, LCM IP/host, stage, and backup id.

    Args:
       argv: list of system arguments

    Returns: Nothing

    Raises: Nothing
    """
    # pylint: disable=global-statement
    global BACKUP_TAG
    global BACKUP_ID
    global CONF_FILE
    global STAGE
    global CUSTOMER
    global SEND_MAIL

    long_opts = ["customer=", "cfg=", "tag=", "stage=", "id=", "nomail", "help"]

    try:
        opts, _ = getopt.getopt(argv, "h", long_opts)
    except getopt.GetoptError:
        usage()

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '--customer':
            CUSTOMER = arg
        elif opt == '--cfg':
            CONF_FILE = arg
        elif opt == '--tag':
            BACKUP_TAG = arg
        elif opt == '--stage':
            STAGE = arg
        elif opt == '--id':
            BACKUP_ID = arg
        elif opt == '--nomail':
            SEND_MAIL = False
        else:
            print "Unknown option %s" % opt
            usage()

    if not STAGE:
        print "--stage required"
        usage()

    if not CUSTOMER:
        print "--customer required"
        usage()

    # BACKUP_ID is required for these stages:
    if STAGE in ('RUNNING', 'CHECK', 'METADATA'):
        if not BACKUP_ID:
            print "--id required for stage %s" % STAGE
            usage()

    # BACKUP_TAG is not needed in stages before BACKUP and can be
    # generated in ALL or BACKUP stages so is not mandatory for them
    if STAGE not in ('STORAGE_WF', 'ALL_WF', 'RETENTION', 'ALL', 'BACKUP'):
        if not BACKUP_TAG:
            print "--tag required for stage %s" % STAGE
            usage()


def main():
    """Check for any workflows running on 'this' tenancy

    Args: None

    Returns:
        Bool: True if workflows are running

    Raises: Nothing (hopefully!)
    """
    global MAIL_URL
    global MAIL_TO

    # Parse arguments
    parse_args(sys.argv[1:])

    # Read configuration file
    cfg = Cfg()
    cfg.read_config(CONF_FILE)

    # Set up logging
    try:
        log = get_logger(cfg, CUSTOMER)
    except (AttributeError,
            ConfigParser.NoOptionError,
            ConfigParser.NoSectionError) as err:
        err_exit("Logging configuration invalid in " + CONF_FILE, 1)


    # Run the backup stage
    log.info(">>> %s Started, running stage %s with tag %s  " % (SCRIPT_NAME, STAGE, str(BACKUP_TAG)))

    try:
        customers = cfg.get("general.customers").split(',')
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Could not get customer list from " + CONF_FILE, 1, log)

    if CUSTOMER not in customers:
        msg = "Customer %s not in list %s, exiting" % (CUSTOMER, customers)
        err_exit(msg, 1, log)

    try:
        bkup_script = cfg.get("general.backup_script")
        metadata_script = cfg.get("general.metadata_script")
        skip_all_check = cfg.get_bool("general.skip_check_all")

        max_delay = to_seconds(cfg.get("timers.max_start_delay"))
        max_time  = to_seconds(cfg.get("timers.max_duration"))

        nfs = cfg.get("nfs.ip")
        nfs_user = cfg.get("nfs.user")
        nfs_key = cfg.get("nfs.key")
        nfs_path = cfg.get("nfs.path")

        lcm = cfg.get(CUSTOMER + ".lcm")
        enm_key = cfg.get(CUSTOMER + ".enm_key")
        keystone = cfg.get(CUSTOMER + ".keystone_rc")
        cust_dir = cfg.get(CUSTOMER + ".deployment_id")

        nfs_path = nfs_path + '/' + cust_dir

        MAIL_URL = cfg.get("mail.url")
        MAIL_TO = cfg.get("mail.dest")

    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Failed to read item from " + CONF_FILE + " " + err, 1, log)

    try:
        tenancies = {}
        for customer in customers:
            tenancies[customer] = cfg.get(customer + ".lcm")
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Failed to read customer info from " + CONF_FILE + " " + err, 1, log)


    if STAGE == 'ALL':
        BackupClass = BackupSequencer
    else:
        BackupClass = BackupStages

    backup = BackupClass(lcm,
                         max_delay,
                         max_time,
                         bkup_script,
                         metadata_script,
                         tenancies,
                         CUSTOMER,
                         BACKUP_TAG,
                         enm_key,
                         keystone,
                         nfs,
                         nfs_user,
                         nfs_key,
                         nfs_path,
                         skip_all_check,
                         log,
                         mailer,
                         BACKUP_ID)

    output = None
    try:
        if STAGE == 'STORAGE_WF':
            result = backup.no_storage_wfs()
        elif STAGE == 'ALL_WF':
            result = backup.no_wfs()
        elif STAGE == 'RETENTION':
            result = backup.set_retention()
        elif STAGE == 'BACKUP':
            result, output = backup.start_backup()
        elif STAGE == 'RUNNING':
            result = backup.is_backup_running()
        elif STAGE == 'CHECK':
            result = backup.backup_completed_ok()
        elif STAGE == 'VALIDATE':
            result = backup.verify_backup_state()
        elif STAGE == 'METADATA':
            result = backup.backup_metadata()
        elif STAGE == 'FLAG':
            result = backup.label_ok()
        elif STAGE == 'ALL':
            result = backup.run()
        else:
            log.error("Invalid stage %s " % STAGE)
            usage()

    except Exception as err:  # pylint: disable=broad-except
        # External orchestrator can retry this
        log.error("Unknown error occured: %s " % err)
        result = False
        output = "Stage Failed to Run"
        mailer("Backup failure: " + CUSTOMER,
               "Backup failed because workflows not retrieved")

    if output:
        print output

    if STAGE == 'ALL':
        if result:
            log.info("Backup Completed Successfully")
            mailer("Backup Successful for " + CUSTOMER,
                   'Backup successful')
        else:
            log.error("Backup Failed")
    else:
        if result:
            log.info("Stage %s Completed Successfully" % STAGE)
        else:
            log.error("Stage %s Failed" % STAGE)
            mailer("Backup failure: " + CUSTOMER,
                   "Backup failed at stage " + STAGE)

    if result:
        return 0
    elif result == False:
        return 1
    else:
        log.error("Stage failed to retrieve information.  It can be re-ran")
        return 2
 
if __name__ == "__main__":  # pragma: no cover
    result = main()
    sys.exit(result)
