# I should proly document this!

FROM python:2
LABEL Mpho Mphego <mmphego@ska.ac.za>

ENV DEBIAN_FRONTEND noninteractive
WORKDIR /usr/src/apps
RUN python -V

# Install Debian package dependencies
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils && apt-get clean
# Install Python dependencies
RUN pip install --no-cache-dir -U argcomplete \
                   coloredlogs \
                   context.api \
                   dash-core-components \
                   dash-html-components \
                   dash-renderer \
                   dash \
                   katcp \
                   plotly

# User data directory, containing Python scripts, config and etc.
COPY src/Config.py /usr/src/apps/
COPY src/cbf_sensors_dash.py /usr/src/apps/
RUN chmod +x /usr/src/apps/cbf_sensors_dash.py
ENTRYPOINT ["/usr/src/apps/cbf_sensors_dash.py"]
