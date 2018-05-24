#!/usr/bin/env python

import argparse
import fileinput
import sys
import socket
import struct
import fcntl
import os
import time
import subprocess

parser = argparse.ArgumentParser(description='Should probably put the description here!')
parser.add_argument('-i', '--interface', dest='interface', action='store', default='eth0',
                    help='network interface [Default: eth0]')
parser.add_argument('-f', '--flowsFile', dest='FLOWS', action='store', default='flows.json',
                    help='Node-Red flows [Default: flows.json]')

args = vars(parser.parse_args())

try:
    dir_path = os.path.dirname(os.path.realpath(__file__))
except:
    dir_path = os.path.dirname(os.path.realpath(__name__))

def replaceAll(file,searchExp,replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)

def get_ip_address(ifname):
    """
    Get current IP address of a network interface card

    Params
    ======
    ifname: str
        Interface name eg: eth0
    Return
    ======
    IP: str
        Current IP of the interface
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                                        struct.pack('256s', ifname[:15]))[20:24])

if __name__ == '__main__':
    host = get_ip_address(args.get('interface'))
    hostname = os.uname()[1]
    flows_file = args.get('FLOWS')
    replaceAll(flows_file, 'localhost', host)
    os.chdir('/'.join([dir_path, 'src']))
    msg = ("Starting flask server and sensor polling scripts in the background\n"
     "To list detached screens, Run: screen -list\n"
     "else, to killall screen session, \n"
     "Run: screen -ls | grep Detached | cut -d. -f1 | awk '{print $1}' | xargs kill\n\n")
    print msg
    subprocess.call(['/bin/bash', 'OnScreenFeeder.sh', '%s:7147' % host])
    os.chdir(dir_path)
    subprocess.call(["docker", "build", "-t", "cbf-dashboard/cbf-system-dashboard", "."])
    time.sleep(1)
    subprocess.call(["docker", "run", "-d", "-h", "%s" % hostname, "--name=cbf-dash",
        "--restart=on-failure:10", "-p", "1880:1880", "cbf-dashboard/cbf-system-dashboard"])

    print "Reminder:\n%s" % msg