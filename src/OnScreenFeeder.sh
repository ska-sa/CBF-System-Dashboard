#!/bin/bash
if [ $# -eq 0 ]
  then
    printf "No argument provided, See example below.\n"
    echo "$0 localhost:7147"
    exit
fi

host=$1

screen -dmS sensor-poll
# Where the return character, ^M, you need to enter using vim as i CTRL-V ENTER ESCAPE
screen -r sensor-poll -p 0 -X stuff $"while true; do sleep 1;  echo 'newhost:' ${host}; ./sensor_poll.py --poll-sensors 15 --json --katcp ${host} && break; done ^M"
sleep 1
screen -S cbf-dash -dm python cbf_sensors_dash.py
