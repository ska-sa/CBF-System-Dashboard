#!/usr/bin/env python

# ====================================
# TODO
# Multi-Page Apps and URL Support
# https://dash.plot.ly/urls

import argcomplete
import argparse
import coloredlogs
import dash
import dash_core_components as dcc
import dash_html_components as html
import fcntl
import glob
import json
import logging
import os
import socket
import struct
import sys
import types
import urllib2

from pprint import PrettyPrinter


def get_sensors(json_file):
    """
    Read sensor values stored in a json file

    Params
    ======
    json_file: str
        json path

    Return
    ======
    data: dict
        json dump in a dict format
    """
    logger.info('Reading latest sensor values from %s' % json_file)
    with open(json_file) as json_data:
        data = json.load(json_data)
        return data

# Sensors should be formatted like this
sensor_format = {
                    'fhost00': [    # sensor, status
                                    ['SKA-020709','host'],
                                    ['fhost00', 'skarab020709-01'],
                                    ['ant0_x', 'inputlabel'],
                                    ['network', 'nominal'],
                                    ['spead-rx', 'nominal'],
                                    # ['network-reorder', 'nominal'],
                                    ['network-Re', 'nominal'],
                                    ['cd', 'warn'],
                                    ['pfb', 'nominal'],
                                    ['requant', 'warn'],
                                    ['ct', 'nominal'],
                                    ['spead-tx','nominal'],
                                    ['network', 'error'],
                                    ['->XEngine', 'xhost']
                             ],
                    'fhost01': [    # sensor, status
                                    ['SKA-020710','host'],
                                    ['fhost01', 'skarab020710-01'],
                                    ['ant1_x', 'inputlabel'],
                                    ['network', 'nominal'],
                                    ['spead-rx', 'nominal'],
                                    # ['network-reorder', 'nominal'],
                                    ['network-Re', 'warn'],
                                    ['cd', 'nominal'],
                                    ['pfb', 'nominal'],
                                    ['requant', 'nominal'],
                                    ['ct', 'nominal'],
                                    ['spead-tx','nominal'],
                                    ['network', 'nominal'],
                                    ['->XEngine', 'xhost']
                             ],
                    'fhost02': [    # sensor, status
                                    ['SKA-020711','host'],
                                    ['fhost02', 'skarab020711-01'],
                                    ['ant1_x', 'inputlabel'],
                                    ['network', 'nominal'],
                                    ['spead-rx', 'nominal'],
                                    # ['network-reorder', 'nominal'],
                                    ['network-Re', 'nominal'],
                                    ['cd', 'warn'],
                                    ['pfb', 'nominal'],
                                    ['requant', 'error'],
                                    ['ct', 'nominal'],
                                    ['spead-tx','warn'],
                                    ['network', 'nominal'],
                                    ['->XEngine', 'xhost']
                             ],
                    'fhost03': [    # sensor, status
                                    ['SKA-020711','host'],
                                    ['fhost03', 'skarab020711-01'],
                                    ['ant2_x', 'inputlabel'],
                                    ['network', 'warn'],
                                    ['spead-rx', 'nominal'],
                                    # ['network-reorder', 'nominal'],
                                    ['network-Re', 'error'],
                                    ['cd', 'nominal'],
                                    ['pfb', 'nominal'],
                                    ['requant', 'nominal'],
                                    ['ct', 'nominal'],
                                    ['spead-tx','nominal'],
                                    ['network', 'nominal'],
                                    ['->XEngine', 'xhost']
                             ],
                    }

# def format_sensors(sensor_data):
#     fhosts = []
#     xhosts = []
#     for host, sensor_status in sensor_data.iteritems():
#         host_ =  host.split('.')
#         if 'device-status' in host_ and len(host_) > 2:
#             host_.append(sensor_status.get('status'))
#             if host_[0].startswith('fhost'):
#                 fhosts.append(host_)
#             if host_[0].startswith('xhost'):
#                 xhosts.append(host_)
#     return [sorted(fhosts), sorted(xhosts)]


COLORS = [
            {   # NOMINAL
                'background': 'green',
                'color': 'white',
            },
            {
                # WARN
                'background': 'orange',
                'color': 'white',
            },
            {
                # ERROR
                'background': 'red',
                'color': 'white',
            },
            {
                # Other
                'background': 'blue',
                'color': 'white',
            },
        ]

def set_style(state):
    """
    Set html/css style according to sensor state
    Params
    ======
    state: str
        sensor state, eg: nominal, warn, error and other

    Return
    ======
    style: dict
        dictionary containing html/css style
    """

    style = {}
    state = state.lower()
    if state:
        if state == 'nominal':
            style = {
                'backgroundColor': COLORS[0]['background'],
                'color': COLORS[0]['color'],
                'display': 'inline-block'
                }
        elif state == 'warn':
            style = {
                'backgroundColor': COLORS[1]['background'],
                'color': COLORS[1]['color'],
                'display': 'inline-block'
                }
        elif state == 'error':
            style = {
                'backgroundColor': COLORS[2]['background'],
                'color': COLORS[2]['color'],
                'display': 'inline-block'
                }
        else:
            style = {
                'backgroundColor': COLORS[3]['background'],
                'color': COLORS[3]['color'],
                'display': 'inline-block'
                }
    return style


def add_buttons(child, _id, _status):
    """
    Params
    ======

    Return
    ======

    """
    return [
        # Button click redirection -- https://github.com/plotly/dash-html-components/issues/16
        html.A(
            html.Button(children=child, id=_id, style=set_style(_status),
                type='button', className="btn-xl"),
            href='http://www.dontclick.it/'),
        html.Hr(className='horizontal')]


def generate_line(host):
    """
    Params
    ======

    Return
    ======

    """
    # print  [      (i[0], 'id_%s' % i[0], i[-1]) for i in sensor_format.get(host)]
    return [add_buttons(i[0], 'id_%s' % i[0], i[-1]) for i in sensor_format.get(host)]


def generate_table():
    """
    Params
    ======

    Return
    ======

    """
    return [
        html.Div([
            html.Span(children=i, style={'display': 'inline-block'}) for i in generate_line(x)
            ]) for x in sorted(sensor_format.keys())
        ]


def get_ip_address(ifname):
    """
    Get current IP address of a network interface card

    Params
    ======
    ifname: str
        Interface name eg: eth0
    Return
    ======
    IP: str
        Current IP of the interface
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                            struct.pack('256s', ifname[:15]))[20:24])


def file_exists(url):
    """
    Check if file in url exists

    Params
    ======
    url: str
        http(s):// link
    Return
    ======
    Boolean
    """
    request = urllib2.Request(url)
    request.get_method = lambda : 'HEAD'
    try:
        response = urllib2.urlopen(request)
        return True
    except:
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Should probably put the description here!')
    parser.add_argument('-i', '--interface', dest='interface', action='store', default='eth0',
                        help='network interface [Default: eth0]')
    parser.add_argument('-p', '--port', dest='port', action='store_true', default=8888,
                        help='flask port [Default: 8888]')
    parser.add_argument('--debug', dest='debug', action='store_false', default=True,
                        help='flask with debug [Default: False]')
    parser.add_argument('--path', dest='sensor_path', action='store', default=None,
                        help='path to where the sensor data .json file is!')
    parser.add_argument('--loglevel', dest='log_level', action='store', default='INFO',
                        help='log level to use, default INFO, options INFO, DEBUG, ERROR')

    argcomplete.autocomplete(parser)
    args = vars(parser.parse_args())

    pp = PrettyPrinter(indent=4)
    log_level = None
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : %(lineno)d - %(message)s'
    if args.get("log_level", 'INFO'):
        log_level = args.get("log_level", 'INFO').upper()
        try:
            logging.basicConfig(level=getattr(logging, log_level), format=log_format)
            logger = logging.getLogger(os.path.basename(sys.argv[0]))
        except AttributeError:
            raise RuntimeError('No such log level: %s' % log_level)
        else:
            if log_level == 'DEBUG':
                coloredlogs.install(level=log_level, fmt=log_format)
            else:
                coloredlogs.install(level=log_level)

    if not args.get('sensor_path'):
        try:
            cur_path = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
        except NameError:
            cur_path = os.path.split(os.path.dirname(os.path.abspath(__name__)))[0]

        try:
            json_dumps_dir = os.path.join(cur_path + '/json_dumps')
            assert os.path.exists(json_dumps_dir)
            sensor_values_json = max(glob.iglob(json_dumps_dir + '/*.json'), key=os.path.getctime)
        except AssertionError:
            logger.error('No json dump file. Exiting!!!')
            sys.exit(1)
    else:
        sensor_values_json = args.get('sensor_path')

    sensor_data = get_sensors(sensor_values_json)
    host = get_ip_address(args.get('interface'))

    # Should I really argparse this???
    title = 'CBF Sensors Dashboard'
    metadata = 'charset=\"UTF-8\" http-equiv=\"refresh\" content=\"60\"'
    try:
        css_link = "https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/src/css/KoJoZq.css"
        assert file_exists(css_link)
    except AssertionError:
        css_link = "https://codepen.io/mmphego/pen/KoJoZq.css"

    app = dash.Dash(name=title)
    # Monkey patching
    app.title = types.StringType(title)
    app.meta = types.StringType(metadata)
    app.layout = html.Div(generate_table())
    app.css.append_css({"external_url": css_link})
    app.run_server(host=host, port=args.get('port'), debug=args.get('debug'),
        extra_files=[sensor_values_json])


