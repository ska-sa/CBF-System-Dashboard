from src import cbf_sensors_dash
import fileinput
import sys

def replaceAll(file,searchExp,replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)

host = cbf_sensors_dash.host
replaceAll('flows.json', 'localhost:8888', host + ':8888')
