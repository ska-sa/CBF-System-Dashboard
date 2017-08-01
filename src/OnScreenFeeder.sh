#!/bin/bash
if [ -z "$*" ];
    then printf "Usage: $0 JenkinsUsername JenkinsPassword\n";
    exit 1;
fi

screen -S nodered-dashboard -dm python /usr/local/src/CBF-System-Dashboard/src/nodered-dashboard.py --username $1 --password $2 run-feeds
