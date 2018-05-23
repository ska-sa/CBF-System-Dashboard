#!/bin/bash
screen -S sensor-poll -dm python sensor_poll.py --poll-sensors 10 --json --katcp $1
sleep 1
screen -S cbf-dash -dm python cbf_sensors_dash.py
