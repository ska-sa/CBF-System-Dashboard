#!/bin/bash
# Mpho Mphego <mmphego@ska.ac.za>

set -x
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

LINUX_VERSION=$(lsb_release -cs)
MOSQ_VERSION="mosquitto-${LINUX_VERSION}.list"
wget http://repo.mosquitto.org/debian/mosquitto-repo.gpg.key
apt-key add mosquitto-repo.gpg.key && rm -rf mosquitto-repo.gpg.key
wget -O /etc/apt/sources.list.d/"${MOSQ_VERSION}" http://repo.mosquitto.org/debian/"${MOSQ_VERSION}"
wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py
pip install -Ir pip-requirements.txt
apt-get update -qq && apt-get install -y $(grep -vE "^\s*#" apt-requirement.txt | tr "\n" " ")

