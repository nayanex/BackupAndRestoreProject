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

import os
import logging
import datetime
import json

from distutils.version import LooseVersion

import scripts.python.backup_scheduler.backup_utils as utils

# TODO More exception handling
# TODO Log exceptions
# TODO MOre checks for backup iD, getting wf etc

SCRIPT_NAME = os.path.basename(__file__)

LOG = logging.getLogger(SCRIPT_NAME)


# TODO DELETE
# class WorkflowNotRetrieved(Exception):
#    pass
#
#
# class WorkflowNotFound(Exception):
#    pass


class WfTypes(object):
    """ Class to handle retrieving the IDs of different
        ENM workflow types. Currently on backup validation
        workflow ID retrieval is implemented.
    """

    def __init__(self, lcm, log):
        self.lcm = lcm
        self.log = log

    def get_backup_validation_workflow_id(self):
        url = 'http://{0}/wfs/rest/definitions'.format(self.lcm)

        self.log.info('Getting workflow ID from workflow URL: %s', url)
        workflows = utils.get_http_request(url, self.log)

        if not workflows:
            self.log.error("Failed to get workflows")
            return None

        validation_backup_workflows = {}
        for workflow in workflows:
            _, version, name = workflow['definitionId'].split('.--.')
            if name == 'BackupValidation__top':
                validation_backup_workflows[version] = workflow['definitionId']

        if not validation_backup_workflows:
            self.log.error("Failed to find backup validation workflow")
            return None
        latest = sorted(validation_backup_workflows, key=LooseVersion)[-1]
        return validation_backup_workflows[latest]


class WfInstances(object):
    """ Class to handle workflows, retrieve them from LCM
        and filter workflows according to various criteria
    """
    ID = 'instanceId'
    END = 'endTime'
    NAME = 'definitionName'
    START = 'startTime'
    ACTIVE = 'active'
    ABORTED = 'aborted'
    BUS_KEY = 'businessKey'
    END_NODE = 'endNodeId'
    INCIDENT = 'incidentActive'

    BACKUP_SUCCESSFUL = '__prg__p100'
    BACKUP_VALID = 'ValidateBackupsEnd'
    BACKUP_INVALID = 'BackupValidationFailed'

    HA = 'High Availability Workflow'
    BACKUP = 'Backup Deployment'
    INSTALL = 'ENM Initial Install'
    UPGRADE = 'ENM Upgrade'
    RESTORE = 'Restore Deployment'
    ROLLBACK = 'Rollback Deployment'
    SNAP_VOL = 'SnapVolume'
    NEO4J_CC = 'Neo4j Consistency Check'
    TEMPLATES = 'Install ENM Cloud Templates'
    ADD_FEATURE = 'Add New Feature'
    PRE_UPGRADE = 'Prepare For Upgrade'
    CLEAN_BACKUPS = 'Cleanup Backups'
    VALIDATE_BACKUPS = 'Backup Validation'

    def __init__(self, lcm, log):
        self.lcm = lcm
        self.wfs = []
        self.log = log

    def get_wfs_from_lcm(self):
        """ Return workflows JSON object from HTTP request
        """
        url = 'http://{0}/wfs/rest/progresssummaries'.format(self.lcm)
        self.wfs = utils.get_http_request(url, self.log)

        if not self.wfs:
            self.log.error("Failed to get workflows from %s" % self.lcm)
            return False

        self.log.info("Retrieved workflows")
        return True

    def start_validate_backup_wf(self, tag):
        url = 'http://{0}/wfs/rest/instances'.format(self.lcm)
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        business_key = 'Backup Validation_{0}'.format(now)
        wfs = WfTypes(self.lcm, self.log)
        workflow_id = wfs.get_backup_validation_workflow_id()

        if not workflow_id:
            self.log.error("Failed to get workflow id")
            return None

        definition = {
            'definitionId': workflow_id,
            'businessKey': business_key,
            'variables': {
                'tag': {'type': 'String',
                        'value': tag}
            }
        }

        json_data = json.dumps(definition)
        result = utils.post_http(url, json_data, self.log)

        if not result:
            self.log.error("Failed to start backup validation workflow")
            return None

        instance_id = result['instanceId']
        self.log.info('Backup validation started with instance ID %s.', instance_id)
        return instance_id

    def active_wfs(self):
        """
        Check if there is an Active Workflow Instance
        :return: the active workflow
        """
        return [wf for wf in self.wfs if wf[WfInstances.ACTIVE]]

    def active_storage_wfs(self):
        candidates = (WfInstances.BACKUP,
                      WfInstances.INSTALL,
                      WfInstances.RESTORE,
                      WfInstances.ROLLBACK)  # TODO MAYBE MOVE TO INI FILE

        active = self.active_wfs()
        return [wf for wf in active if wf[WfInstances.NAME] in candidates]

    def active_backup_wfs(self):
        active = self.active_wfs()
        return [wf for wf in active
                if wf[WfInstances.NAME] == WfInstances.BACKUP]

    def get_wf_by_id(self, workflow_id):
        workflow = [wf for wf in self.wfs if wf[WfInstances.ID] == workflow_id]
        if len(workflow) == 1:
            return workflow[0]
        return None


def log_wf(workflow):
    """Log a workflow, logging a subset of its data

    Args:
       workflow: A dictionary holding information of a workflow

    Returns: None
        int: Seconds represented by the duration

    Raises: Nothing
    """
    LOG.info("Workflow: %s (%s)" % (workflow[WfInstances.NAME], workflow[WfInstances.ID]))
    LOG.info("Start:    %s  End: %s" % (workflow[WfInstances.START], workflow[WfInstances.END]))
    LOG.info("Active:   %s (Aborted: %s, Incident: %s)" % (workflow[WfInstances.ACTIVE],
                                                           workflow[WfInstances.ABORTED],
                                                           workflow[WfInstances.INCIDENT]))
