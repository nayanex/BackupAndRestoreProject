#!/usr/bin/env python

"""
This module is for classes that holds stages of a workflow (BackupStages) or
a whole workflow (BackupSequence)
"""

import datetime
import logging
import os
import time

import scripts.python.backup_scheduler.workflows as workflows
import scripts.python.backup_scheduler.backup_utils as utils

SCRIPT_NAME = os.path.basename(__file__)
LOG = logging.getLogger(SCRIPT_NAME)


class BackupStages(object):
    """ Class to encapsulate running different stages
        of the ENM BUR Backup Sequence.
    """

    def __init__(self,
                 lcm,
                 max_delay,
                 max_time,
                 bkup_script,
                 metadata_script,
                 tenancies,
                 deployment_id,
                 tag,
                 enm_key,
                 keystone,
                 nfs,
                 nfs_user,
                 nfs_key,
                 nfs_path,
                 skip_all_check,
                 log,
                 mail_fn,
                 backup_id=None):

        self.log = log
        self.max_delay = max_delay
        self.max_time = max_time
        self.bkup_script = bkup_script
        self.metadata_script = metadata_script
        self.tenancies = tenancies
        self.deployment_id = deployment_id
        self.lcm = lcm
        self.tag = tag
        self.enm_key = enm_key
        self.keystone = keystone
        self.backup_id = backup_id
        self.nfs = nfs
        self.nfs_user = nfs_user
        self.nfs_key = nfs_key
        self.nfs_path = nfs_path
        self.skip_all_check = skip_all_check
        self.mail_fn = mail_fn

    def _send_fail_mail(self, message):
        subject = "Backup failure: " + self.deployment_id

        if self.mail_fn:
            return self.mail_fn(subject, message)
        return True

    def _get_backup_wf(self):
        if not self.backup_id:
            self.log.error("No backup ID to check backup state")
            return None

        wfs = workflows.WfInstances(self.lcm, self.log)
        if not wfs.get_wfs_from_lcm():
            self.log.error("Failed to retrieve workflows from LCM")
            return None

        backup = wfs.get_wf_by_id(self.backup_id)
        if not backup:
            self.log.error("Backup not found")
            return None

        self.log.info("Backup workflow found")
        workflows.log_wf(backup)
        return backup

    def _wf_has_problem(self, workflow):
        if workflow[workflows.WfInstances.INCIDENT]:
            self.log.error("Workflow has an incident")
            return True

        if workflow[workflows.WfInstances.ABORTED]:
            self.log.error("Workflow has been aborted")
            return True

        self.log.info("Workflow has no problem")
        return False

    def _transfer_to_nfs(self, transfer_file, destination):
        opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
        scp = "scp -i %s %s %s %s@%s:%s " % (self.nfs_key,
                                             opts,
                                             transfer_file,
                                             self.nfs_user,
                                             self.nfs,
                                             destination)
        return utils.cmd(scp)

    def no_storage_wfs(self):
        """Check for running workflows that are storage intensive all tenancies
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: False if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Check for Workflows on all tenancies")
        tenancies_quiet = True

        for customer in self.tenancies:
            lcm = self.tenancies[customer]
            self.log.info("Checking %s workflows on LAF %s" % (customer, lcm))
            wfs = workflows.WfInstances(lcm, self.log)
            if wfs.get_wfs_from_lcm():
                active_wfs = wfs.active_storage_wfs()
                if active_wfs:
                    tenancies_quiet = False
                    self.log.info("There are workflows running:")

                    for workflow in active_wfs:
                        workflows.log_wf(workflow)
                else:
                    self.log.info("No active workflows")
            else:
                tenancies_quiet = None
                self.log.warning("Failed to get workflows for %s" % customer)
        return tenancies_quiet

    def no_wfs(self):
        """Check for any workflows running on 'this' tenancy
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: False if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """

        self.log.info("Stage >>> Check for any workflows on %s" % self.lcm)
        deployment_quiet = True
        wfs = workflows.WfInstances(self.lcm, self.log)
        if wfs.get_wfs_from_lcm():
            active_wfs = wfs.active_wfs()

            if active_wfs:
                deployment_quiet = False
                self.log.info("There are workflows running:")

                for workflow in active_wfs:
                    workflows.log_wf(workflow)
            else:
                self.log.info("No active workflows")
        else:
            deployment_quiet = None
            self.log.warning("Failed to retrieve workflows")
        return deployment_quiet

    def set_retention(self):
        """Sets backup retention to 2 TODO: make configurable
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Set retention")
        path = 'enm/applications/bur/services/backup/retention_value'
        consul_cmd = 'consul kv put %s 2' % path
        opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
        ssh = 'ssh -i %s %s cloud-user@%s ' % (self.enm_key, opts, self.lcm)
        result = utils.cmd(ssh + consul_cmd)

        if result[0] != 0:
            self.log.error("Failed to set retention")
            msg = "Failed to set consul retention value on " + self.lcm
            self._send_fail_mail(msg)
            return False
        return True

    def start_backup(self):
        """Check for any workflows running on 'this' tenancy
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """

        if not self.tag:
            now = datetime.datetime.now().strftime('_%Y%m%d_%H%M')
            self.tag = self.deployment_id + now

        self.log.info("Stage >>> start backup")
        backup_args = " --lcm=%s --tag=%s --stdout" % (self.lcm, self.tag)
        result, stdout, _ = utils.cmd(self.bkup_script + backup_args)

        for line in stdout.split("\n"):
            if "Backup workflow requested with" in line:
                word_list = line.split()
                # get last word in list and remove last character '.'
                self.backup_id = word_list[-1][:-1]
                break

        if not self.backup_id:
            self.log.error("Failed to get backup id, assuming no backup")
            return False, "ID: None  TAG: %s" % self.tag

        info = "ID: %s  TAG: %s" % (self.backup_id, self.tag)
        if result:
            self.log.error("Starting backup failed")
            msg = "Failed to start backup on " + self.lcm
            self._send_fail_mail(msg)
            return False, info

        msg = "Backup started with tag %s and id %s" % (self.tag, self.backup_id)
        self.log.info(msg)
        return True, info

    def is_backup_running(self):
        """Check if backup is running
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if backup is running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Is Backup Running")
        backup = self._get_backup_wf()

        if not backup:
            self.log.error("Failed to find backup")
            return None  # EDDERS

        if self._wf_has_problem(backup):
            self.log.error("Backup has a problem")
            workflows.log_wf(backup)
            return False

        if not backup[workflows.WfInstances.ACTIVE]:
            self.log.info("Backup is NOT running")
            return False

        self.log.info("Backup is running")
        return True

    def backup_completed_ok(self):
        """Retrieve the backup information from the LCM workflows

        Args: None

        Returns:
            Bool: True if backup is finished
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Checking if backup completed ok")
        backup = self._get_backup_wf()

        fail_msg = "Backup with tag %s and ID %s has failed" % (self.tag,
                                                                self.backup_id)

        if not backup:
            self.log.error("Backup could not be retrieved")
            workflows.log_wf(backup)
            self._send_fail_mail(fail_msg)
            return None

        workflows.log_wf(backup)

        if self._wf_has_problem(backup):
            self.log.error("Backup has a problem")
            workflows.log_wf(backup)
            self._send_fail_mail(fail_msg)
            return False

        if backup[workflows.WfInstances.ACTIVE]:
            self.log.info("Backup is running")
            return False

        if backup[workflows.WfInstances.END_NODE].endswith(
                workflows.WfInstances.BACKUP_SUCCESSFUL):
            self.log.info("Backup workflow completed ok")
            return True

        self.log.error("Backup has failed")
        self._send_fail_mail(fail_msg)
        return False

    def verify_backup_state(self):
        """Call verify backup workflow.

           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if backup is good
            Str: For script output

        Raises: Nothing (hopefully!)
        """

        # u'endNodeId': u'ValidateBackupsEnd'
        # u'businessKey': u'Backup Validation_1533213585',
        self.log.info("Stage >>> Verify Backup State")
        wfs = workflows.WfInstances(self.lcm, self.log)
        wf_id = wfs.start_validate_backup_wf(self.tag)

        if not wf_id:
            self.log.error("Failed to start validation workflow")
            fail_msg = "Failed to start validation workflow"
            self._send_fail_mail(fail_msg)
            return False

        wfs = workflows.WfInstances(self.lcm, self.log)
        wait = 60
        for i in xrange(10):
            self.log.info("Waiting %s seconds to check worklfow" % wait)
            time.sleep(wait)

            if not wfs.get_wfs_from_lcm():
                self.log.warning("Failed to retrieve workflows from LCM")
                continue

            val_wf = wfs.get_wf_by_id(wf_id)

            if not val_wf:
                self.log.warning("Did not get validation workflow")
                continue

            if val_wf[workflows.WfInstances.END_NODE] == workflows.WfInstances.BACKUP_VALID:
                self.log.info("Backup has been validated and is good")
                return True

            if val_wf[workflows.WfInstances.END_NODE] == workflows.WfInstances.BACKUP_INVALID:
                self.log.error("Backup has been validated and is NOT GOOD")
                fail_msg = "Backup is not good, validation failed"
                self._send_fail_mail(fail_msg)
                return False

            if self._wf_has_problem(val_wf):
                self.log.error("Backup validation has a problem")
                workflows.log_wf(val_wf)
                fail_msg = "Backup validation failed"
                self._send_fail_mail(fail_msg)
                return False

        self.log.error("Failed to run backup validation workflow")
        return None

    def backup_metadata(self):
        """Backup metadata.
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> get backup metadata")
        meta = 'backup.metadata'
        dest = "%s/%s/%s" % (self.nfs_path, self.tag, meta)

        cmd_args = ' export --filename %s --rcfile %s --tag %s' % (meta, self.keystone, self.tag)
        result, stdout, stderr = utils.cmd(self.metadata_script + cmd_args)
        stdout = ""
        stderr = ""

        if result == 0 and os.path.isfile(meta):
            self.log.info("Metadata file created ok")
        else:
            self.log.error("Failed to generated metadata file")
            self.log.error("STDOUT: " + stdout)
            self.log.error("STDERR: " + stderr)
            fail_msg = "Failed to generate backup metadata"
            self._send_fail_mail(fail_msg)
            return False

        result, stdout, stderr = self._transfer_to_nfs(meta, dest)

        if result:
            self.log.error("Failed to transfer metadata file")
            self.log.error("STDOUT: " + stdout)
            self.log.error("STDERR: " + stderr)
            fail_msg = "Failed to transfer metadata to backup server"
            self._send_fail_mail(fail_msg)
            return False

        self.log.info("Metadata file transferred to nfs ok, %s" % dest)
        return True

    def label_ok(self):
        """Create success flag in backup directory
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> create success flag")
        ok_file = "%s/%s/%s" % (self.nfs_path, self.tag, 'BACKUP_OK')
        opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        touch = 'ssh -i %s %s %s@%s touch %s' % (self.nfs_key,
                                                 opts,
                                                 self.nfs_user,
                                                 self.nfs,
                                                 ok_file)
        result, stdout, stderr = utils.cmd(touch)

        if result:
            self.log.error("Failed to create success flag")
            self.log.error("STDOUT: " + stdout)
            self.log.error("STDERR: " + stderr)
            fail_msg = "Failed to create success flag on backup server"
            self._send_fail_mail(fail_msg)
            return False

        self.log.info("Success flag created at %s" % ok_file)
        return True


class BackupSequencer(BackupStages):
    """ Class derived from BackupStages adding functionality
        to run the full ENM BUR Backup Sequence.
    """

    def __init__(self,
                 lcm,
                 max_delay,
                 max_time,
                 bkup_script,
                 metadata_script,
                 tenancies,
                 deployment_id,
                 tag,
                 enm_key,
                 keystone,
                 nfs,
                 nfs_user,
                 nfs_key,
                 nfs_path,
                 skip_all_check,
                 log,
                 mail_fn,
                 backup_id=None):
        super(BackupSequencer, self).__init__(lcm,
                                              max_delay,
                                              max_time,
                                              bkup_script,
                                              metadata_script,
                                              tenancies,
                                              deployment_id,
                                              tag,
                                              enm_key,
                                              keystone,
                                              nfs,
                                              nfs_user,
                                              nfs_key,
                                              nfs_path,
                                              skip_all_check,
                                              log,
                                              mail_fn,
                                              backup_id)

    def check_for_wfs(self):
        """Calls the two wfs methods using a timeout mechanism.

        Args: None

        Returns:
            Bool: False if timeout expires and workflows are running, else True

        Raises: Nothing (hopefully!)
        """
        self.log.info("wait for no workflows")
        retry_wait = 300
        retry_end = time.time() + self.max_delay - retry_wait
        self.log.info("Retry end: %s " % retry_end)
        self.log.info("Max delay: %s " % self.max_delay)
        self.log.info("Time %s" % time.time())
        while time.time() < retry_end:

            if self.skip_all_check:
                self.log.info("Not checking other tenancies' workflows")
                proceed_ok = True
            else:
                state = self.no_storage_wfs()

                if state is True:
                    self.log.info("No workflows running on any tenancy")
                    proceed_ok = True
                elif state is False:
                    self.log.info("workflows are running")
                    proceed_ok = False
                else:
                    self.log.warning("Failed to check storage workflows")
                    # Assume LAF or WFs are down so we can assume nothing running
                    # if problem is for 'this' tenancy then it will be caught in
                    # next check
                    proceed_ok = True

            if proceed_ok:
                state = self.no_wfs()

                if state is True:
                    self.log.info("No workflows running on %s" % self.lcm)
                    return True
                elif state is False:
                    self.log.info("WfInstances are running on %s" % self.lcm)
                elif state is None:
                    self.log.warning("Failed to check workflows")
            self.log.info("Waiting for %s before checking again" % retry_wait)
            time.sleep(retry_wait)

        self.log.error("Timed out waiting for no workflows")
        return False

    def wait_for_backup(self):
        """Checks for backup to finish using a timeout mechanism.

        Args: None

        Returns:
            Bool: True if backup not running, False if timeout

        Raises: Nothing (hopefully!)
        """
        self.log.info("wait for backup")
        time.sleep(30)  # Wait for backup workflow to appear
        wait = 300
        retry_end = time.time() + self.max_time - wait

        while time.time() < retry_end:
            state = self.is_backup_running()
            if state:
                self.log.info("Waiting for %s s before checking again" % wait)
                time.sleep(wait)
            elif state is None:
                self.log.error("Failed to retrieve backup")
                return None
            else:
                self.log.info("Backup is not running")
                return True
        self.log.warning("Timed out waiting for backup to complete")
        return False

    def run(self):
        """Run the entire backup sequence
           This is a special 'stage' method that runs all stages in sequence,
           calling additional functions to wait and check for stage completion.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("run backup sequence")

        has_error = False
        log_error_message = ''
        mail_error_message = None

        if not self.check_for_wfs():
            has_error = True
            log_error_message = "Timed out waiting for workflows to stop, backup not started"
            mail_error_message = "Backup could not be started as workflows are running"

        elif not self.set_retention():
            has_error = True
            log_error_message = "Failed to set backup retention"

        elif not self.start_backup()[0]:
            has_error = True
            log_error_message = "Could not start backup"

        wait = self.wait_for_backup()

        if not wait:
            has_error = True
            if wait is False:
                mail_error_message = "Timed out waiting for backup (it is still running)"
            else:
                mail_error_message = "Unable to retrieve backup info"

        elif not self.backup_completed_ok():
            has_error = True
            log_error_message = "Backup did not complete okay"

        elif not self.verify_backup_state():
            has_error = True
            log_error_message = "Verification of backup failed"

        elif not self.backup_metadata():
            has_error = True
            log_error_message = "Failed to get backup metadata"

        elif not self.label_ok():
            has_error = True
            log_error_message = "Failed to create ok flag"

        if has_error:
            self.log.error(log_error_message)

            if mail_error_message.strip():
                self._send_fail_mail(mail_error_message)
            return False

        self.log.info("Backup completed successfully")
        return True
