# Usage
# docker run -d -p 8888:8888 -v ${PWD}/json_dumps/:/usr/src/json_dumps --name cbf-sensor-dash cbf-sensor-dash

FROM python:2
LABEL maintainer="Mpho Mphego <mmphego@ska.ac.za>"

ENV DEBIAN_FRONTEND noninteractive
WORKDIR /usr/src/apps
# Install Python dependencies
RUN pip install --no-cache-dir -U \
                argcomplete \
                coloredlogs \
                context.api \
                dash==0.21.0 \
                dash-core-components==0.22.1 \
                dash-html-components==0.10.0  \
                dash-renderer==0.12.1

# User data directory, containing Python scripts, config and etc.
COPY src/Config.py /usr/src/apps/
COPY src/cbf_sensors_dash.py /usr/src/apps/
RUN chmod +x /usr/src/apps/cbf_sensors_dash.py
ENTRYPOINT ["/usr/src/apps/cbf_sensors_dash.py"]
