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

"""
This module is for unit testing of the no_storage_wfs method from
scripts.python.backup_scheduler.backup_handlers.BackupStages class
"""

import os
import unittest
import mock
import scripts.python.backup_scheduler.backup_handlers as handlers
import scripts.python.backup_scheduler.backup_utils as utils

MOCK_PACKAGE = 'scripts.python.backup_scheduler.backup_handlers.'
MOCK_BACKUP_STAGES = MOCK_PACKAGE + 'BackupStages'
MOCK_LOG = MOCK_PACKAGE + 'logging.getLogger'
MOCK_MAILER = 'scripts.python.backup_scheduler.run_backup_stages.mailer'

DIR = os.path.dirname(os.path.realpath(__file__))

CONFIG_FILE = DIR + '/backup_stages_create_test.ini'


class BackupStagesCreationTestCase(unittest.TestCase):
    """
    This is a scenario for creating a BackupStages object
    """

    def setUp(self):
        self.customer = 'dummy'
        self.backup_tag = 'fake_tag'
        self.backup_id = 'fake_id'

        self.cfg = utils.Cfg()
        self.cfg.read_config(CONFIG_FILE)

        self.bkup_script = self.cfg.get("general.backup_script")
        self.metadata_script = self.cfg.get("general.metadata_script")
        self.skip_all_check = self.cfg.get_bool("general.skip_check_all")

        self.max_delay = utils.to_seconds(self.cfg.get("timers.max_start_delay"))
        self.max_time = utils.to_seconds(self.cfg.get("timers.max_duration"))

        self.nfs = self.cfg.get("nfs.ip")
        self.nfs_user = self.cfg.get("nfs.user")
        self.nfs_key = self.cfg.get("nfs.key")
        self.nfs_path = self.cfg.get("nfs.path")

        self.lcm = self.cfg.get(self.customer + ".lcm")
        self.enm_key = self.cfg.get(self.customer + ".enm_key")
        self.keystone = self.cfg.get(self.customer + ".keystone_rc")
        self.cust_dir = self.cfg.get(self.customer + ".deployment_id")

        self.nfs_path = self.nfs_path + '/' + self.cust_dir

        self.mail_url = self.cfg.get("mail.url")
        self.mail_dest = self.cfg.get("mail.dest")

        self.tenancies = {self.customer: self.cfg.get(self.customer + ".lcm")}

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_MAILER)
    def test_create_stage(self, mock_mailer, mock_log):
        mock_mailer.call_args = {'subject': 'subject', 'message': 'message'}
        mock_mailer.return_value = utils.send_mail(self.mail_url, self.customer, self.mail_dest,
                                                   'subject', 'message')
        backup_stage = handlers.BackupStages(self.lcm,
                                             self.max_delay,
                                             self.max_time,
                                             self.bkup_script,
                                             self.metadata_script,
                                             self.tenancies,
                                             self.customer,
                                             self.backup_tag,
                                             self.enm_key,
                                             self.keystone,
                                             self.nfs,
                                             self.nfs_user,
                                             self.nfs_key,
                                             self.nfs_path,
                                             self.skip_all_check,
                                             mock_log,
                                             mock_mailer,
                                             self.backup_id)

        result = backup_stage.is_backup_running()
        self.assertFalse(result)
