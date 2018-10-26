.PHONY: bootstrap help build run bootstrap start stop clean logs shell

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  bootstrap			One-liner to make everything work!!!"
	@echo "  build				to build a docker container, configure CBF-Sensor-Dash"
	@echo "  run 				to run pre-built CBF-Sensor-Dash container"
	@echo "  start  			to start an existing CBF-Sensor-Dash container"
	@echo "  stop   			to stop an existing CBF-Sensor-Dash container"
	@echo "  log      			to see the logs of a running container"
	@echo "  shell      			to execute a shell on CBF-Sensor-Dash container"
	@echo "  clean      			to stop and delete CBF-Sensor-Dash container"

build:
	@docker build -t cbf-sensor-dash .

run:
	@docker run -d -p 8888:8888 -v ${PWD}/json_dumps/:/usr/src/json_dumps --name cbf-sensor-dash cbf-sensor-dash

bootstrap: build run

start:
	@docker start cbf-sensor-dash || true

stop:
	@docker stop cbf-sensor-dash || true

clean: stop
	@docker rm -v cbf-sensor-dash || true
	@docker rmi cbf-sensor-dash || true

logs:
	@docker logs -f cbf-sensor-dash

shell:
	@docker exec -it cbf-sensor-dash /bin/bash
