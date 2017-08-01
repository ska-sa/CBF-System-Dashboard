FROM nodered/node-red-docker
MAINTAINER Mpho Mphego <mmphego@ska.ac.za>
ENV UPDATED_ON 2017-07-10

ENV DEBIAN_FRONTEND noninteractive
# User data directory, contains flows, config and nodes.
COPY flows.json /data

# Node-Red editor webapp
# Username: admin
# Password: pass
COPY settings.js /data

# Copy html template to nodered
COPY index.mst /usr/src/node-red/node_modules/node-red/editor/templates/

# Root user, such that apt can be accessible
USER root

# Copy data to node-red
COPY images/node-red-256.png /usr/src/node-red/node_modules/node-red/public/red/images/
COPY images/node-red.png /usr/src/node-red/node_modules/node-red/public/red/images/
COPY images/favicon.ico /usr/src/node-red/node_modules/node-red/public/

WORKDIR /usr/src/node-red

# Handle npm deps
# Node-RED NPM module and node dependencies
RUN npm install node-red-admin node-red-contrib-cpu node-red-contrib-jenkins node-red-node-smooth
RUN npm install node-red-contrib-bigssh node-red-contrib-os node-red-dashboard

# Handle apt dependencies
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get install -y vim lm-sensors

# Clean up APT when done.
RUN apt-get clean
ENV DEBIAN_FRONTEND teletype
