#!/usr/bin/env python

import getopt
import json
import sys


def print_help():
    help = ' -i <enm.json> -o <output file> -s <synonym file> -p <app prefix>'

    print sys.argv[0] + help


def main():
    inputfile = ''
    outputfile = ''
    prefix = ''
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hi:o:s:p:",
                                   ["ifile=", "ofile=", "synonym="])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
        elif opt in ("-s", "--synonym"):
            sfile = arg
        elif opt in ("-p"):
            prefix = arg

    with open(sfile) as shandle:
        synonym = json.loads(shandle.read())

    with open(inputfile) as handle:
        mapdump = json.loads(handle.read())

    with open(outputfile, 'w') as outhandle:
        for view in mapdump.keys():
            application = mapdump[view]
            for app in application:
                for role in app["services"]:
                    line = role["name"] + ":" + role["name"] + ":" + \
                           prefix + app["name"] + ":" + view + "\n"
                    outhandle.write(line)

                    if role["name"] in synonym:
                        for syn in synonym[role["name"]]:
                            line = syn + ":" + role["name"] + ":" + \
                                   prefix + app["name"] + ":" + view + "\n"
                            outhandle.write(line)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_help()
        sys.exit()
    main()
