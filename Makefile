.PHONY: bootstrap help build run bootstrap start stop clean logs_dash logs_sensors shell

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  bootstrap			One-liner to make everything work!!!"
	@echo "  build				to build a docker container, configure CBF-Sensor-Dash"
	@echo "  run 				to run pre-built CBF-Sensor-Dash container"
	@echo "  start  			to start an existing CBF-Sensor-Dash container"
	@echo "  stop   			to stop an existing CBF-Sensor-Dash container"
	@echo "  logs      			to see the logs of a running container"
	@echo "  shell      			to execute a shell on CBF-Sensor-Dash container"
	@echo "  clean      			to stop and delete CBF-Sensor-Dash container"

build:
	@docker build -t cbf-sensor-dash -f Dockerfile .
	@docker build -t sensor-poll -f DockerfileSensorPoll .

run:
	@docker run -d -p 8888:8888 -v ${PWD}/json_dumps/:/usr/src/json_dumps --name cbf-sensor-dash cbf-sensor-dash
	@docker run -d -v ${PWD}/json_dumps/:/usr/src/json_dumps --name sensor-poll sensor-poll


bootstrap: build run

start:
	@docker start cbf-sensor-dash || true
	@docker start sensor-poll || true

stop:
	@docker stop cbf-sensor-dash || true
	@docker stop sensor-poll || true

clean: stop
	@docker rm -v cbf-sensor-dash || true
	@docker rmi cbf-sensor-dash || true
	@docker rm -v sensor-poll || true
	@docker rmi sensor-poll || true

logs_dash:
	@docker logs -f cbf-sensor-dash

logs_sensors:
	@docker logs -f sensor-poll

shell:
	@docker exec -it cbf-sensor-dash /bin/bash
