#!/bin/bash
screen -S sensor-poll -dm python sensor_poll.py --poll-sensors 15 --json
