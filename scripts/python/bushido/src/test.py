#!/usr/bin/env python
import sys

import requests

INSTALL = 'ENM Initial Install'
UPGRADE = 'ENM Upgrade'
BACKUP = 'Backup Deployment'
# RESTORE = '?'

NAME = 'definitionName'
START = 'startTime'
END = 'endTime'


def get_http_request(url):
    print('GET request: %s', url)
    try:
        result = requests.get(url)
    except ValueError:
        print('Invalid request information')
    result.raise_for_status()
    try:
        return result.json()
    except ValueError:
        return {}


def print_wf(wf):
    print("Workflow: %s (%s)" % (wf[NAME], wf['instanceId']))
    print("Start:    %s  End: %s" % (wf[START], wf[END]))
    print("Active:   %s (Aborted: %s, Incident: %s)" % (wf['active'],
                                                        wf['incidentActive'], wf['incidentActive']))

    # print "Aborted:  %s" %  wf['aborted']
    # print "Incident: %s" % wf['incidentActive']
    # , u'incidentTime': None


def main():
    sys.exit(0)
    laf_host = 'vnflaf-services'

    if len(sys.argv) == 2:
        laf_host = sys.argv[1]
        if sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print("Usage: %s [LAF_HOSTNAME]" % sys.argv[0])
            print("       LAF_ HOSTNAME is not needed if running from the LAF")
            sys.exit(0)

    url = 'http://{0}/wfs/rest/progresssummaries'.format(laf_host)
    wfs = get_http_request(url)

    for wf in wfs:
        if wf[NAME] == UPGRADE or wf[NAME] == INSTALL or wf[NAME] == BACKUP:
            print_wf(wf)
            print

    sys.exit(0)


if __name__ == '__main__':  # pragma: no cover
    main()
