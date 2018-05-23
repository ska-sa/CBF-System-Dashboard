FROM nodered/node-red-docker
LABEL Mpho Mphego <mmphego@ska.ac.za>
ENV UPDATED_ON 2018-05-23

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

# Handle npm deps, in order to install node-red packages, we need to chdir to /usr/src/node-red
WORKDIR /usr/src/node-red
# Node-RED NPM module and node dependencies
RUN npm install -g node-red-admin node-red-contrib-cpu node-red-contrib-jenkins node-red-node-smooth
RUN npm install node-red-contrib-os node-red-dashboard

# Handle apt dependencies
# https://superuser.com/questions/413463/catch-22-need-apt-utils-to-install-apt-utils#413913
RUN apt-get update -qq && apt-get install -y --no-install-recommends apt-utils
RUN dpkg --configure -a

ENV CBFDASH /usr/local/src/cbf-dashboard
RUN mkdir -p $CBFDASH
COPY src/* $CBFDASH/
WORKDIR $CBFDASH
RUN bash setup.sh

RUN bash OnScreenFeeder.sh '192.168.4.14:7147'
# Clean up APT when done.
RUN apt-get clean
ENV DEBIAN_FRONTEND teletype
# Change to working directory
WORKDIR /usr/src/node-red
