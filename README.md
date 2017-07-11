# CBF-System-Dashboard

This project entails how Node-RED Dashboard is ran under Docker which shows the systems status and any arrays running.

![CBF Dashboard](https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/images/dash.png)

This project uses a modified version of Node-RED `nodered/node-red-docker`
container on [DockerHub](https://hub.docker.com/r/nodered/node-red-docker/).


## Building Image

Build the docker image with the following command, which will also install all dependencies...

        $ docker build -t cbf-dashboard:cbf-system-dashboard .

![CBF Dashboard](https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/images/build_log.png)

## Startup container
To run the newly build docker container, execute the following command...

        docker run -h "${HOSTNAME}" --name=cbf-sys-dash --restart=on-failure:10 -p 1880:1880 cbf-dashboard/cbf-system-dashboard

Let's dissect that command...

        docker run      - run this container... and build locally if necessary first.
        -h "${HOSTNAME}" - run container with system hostname
        -p 1880:1880    - connect local port 1880 to the exposed internal port 1880
        --name cbf-sys-dash - give this machine a friendly local name
        --restart on-failure:10 -  the container will be restarted only if it stops
                                   with an exit code other than 0. (0 is for normal
                                   shutdown.)
        cbf-dashboard/cbf-system-dashboard - the image to base it on


Running that command should give a terminal window with a running instance of Node-RED

![Docker logs](https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/images/startup_log.png)

You can then browse to `http://{host-ip}:1880` to access the Node-RED editor(Requires authentication)

![Dashboard auth](https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/images/login.png)

and  `http://{host-ip}:1880/ui` to access the Node-Red CBF Dashboard with additional links to select from...

![Dashboard menu](https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/images/menu.png)

### Container Shell

        $ docker exec -it <containerID> /bin/bash

Will give a command line inside the container - where you can then run the npm install
command you wish - e.g.

        $ cd /data
        $ npm install node-red-node-smooth
        node-red-node-smooth@0.0.3 node_modules/node-red-node-smooth
        $ exit
        $ docker stop <containerID>
        $ docker start <containerID>

Refreshing the browser page should now reveal the newly added node in the palette.

## Running headless

The barest minimum we need to just run Node-RED is

    $ docker run -d -h "${HOSTNAME}" --name=cbf-sys-dash --restart=on-failure:10 -p 1880:1880 cbf-dashboard/cbf-system-dashboard

This will create a local running instance of a machine - that will have some
docker id number and be running on a random port... to find out run

![Docker ps](https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/images/images.png)


You can now point a browser to the host machine on the tcp port reported back, so in the example
above browse to  `http://{host ip}:1880`



### User Permission Errors

If you are seeing *permission denied* errors opening files or accessing host devices, try running the container as the root user.

```
docker run -it -p 1880:1880 --name mynodered --user=root nodered/node-red-docker
```

