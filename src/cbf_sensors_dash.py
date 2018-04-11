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
import json
import logging
import os
import socket
import struct
import types

from pprint import PrettyPrinter

title = 'CBF Sensors Dashboard'
metadata = 'charset=\"UTF-8\" http-equiv=\"refresh\" content=\"60\"'
css_link = "https://codepen.io/mmphego/pen/KoJoZq.css"
sensor_values_dict = '/home/mmphego/.sensor_dumps/sensor_values_dict.json'

with open(sensor_values_dict) as json_data:
   data = json.load(json_data)

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


fhosts = []
xhosts = []
for host, sensor_status in data.iteritems():
    host_ =  host.split('.')
    if 'device-status' in host_ and len(host_) > 2:
        host_.append(sensor_status.get('status'))
        if host_[0].startswith('fhost'):
            fhosts.append(host_)
        if host_[0].startswith('xhost'):
            xhosts.append(host_)
fhosts = sorted(fhosts)
xhosts = sorted(xhosts)


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

def set_style(value):
    style = {}
    value = value.lower()
    if value:
        if value == 'nominal':
            style = {
                'backgroundColor': COLORS[0]['background'],
                'color': COLORS[0]['color'],
                'display': 'inline-block'
                }
        elif value == 'warn':
            style = {
                'backgroundColor': COLORS[1]['background'],
                'color': COLORS[1]['color'],
                'display': 'inline-block'
                }
        elif value == 'error':
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
    # print child, _id, _status
    return [
        # Button click redirection -- https://github.com/plotly/dash-html-components/issues/16
        html.A(
            html.Button(children=child, id=_id, style=set_style(_status),
                type='button', className="btn-xl"),
            href='http://www.dontclick.it/'),
        html.Hr(className='horizontal')]


def generate_line(host):
    # print  [      (i[0], 'id_%s' % i[0], i[-1]) for i in sensor_format.get(host)]
    return [add_buttons(i[0], 'id_%s' % i[0], i[-1]) for i in sensor_format.get(host)]


def generate_table():
    return [
        html.Div([
            html.Span(children=i, style={'display': 'inline-block'}) for i in generate_line(x)
            ]) for x in sorted(sensor_format.keys())
        ]


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                            struct.pack('256s', ifname[:15]))[20:24])

app = dash.Dash(name=title)
# Monkey patching the code
app.title = types.StringType(title)
app.meta = types.StringType(metadata)
app.layout = html.Div(generate_table())
app.css.append_css({"external_url": css_link})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--interface', dest='interface', action='store', default='eth0',
                        help='network interface [Default: eth0]')
    parser.add_argument('-p', '--port', dest='port', action='store_true', default=8888,
                        help='webserver port [Default: 8888]')
    parser.add_argument('--debug', dest='debug', action='store_true', default=False,
                        help='run flask with debug [Default: False]')
    parser.add_argument('--loglevel', dest='log_level', action='store', default='INFO',
                        help='log level to use, default INFO, options INFO, DEBUG, ERROR')

    argcomplete.autocomplete(parser)
    args = vars(parser.parse_args())

    pp = PrettyPrinter(indent=4)
    log_level = None
    if args.get("log_level", 'INFO'):
        log_level = args.get("log_level", 'INFO').upper()
        try:
            logging.basicConfig(level=getattr(logging, log_level),
                                format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : '
                                '%(lineno)d - %(message)s')
        except AttributeError:
            raise RuntimeError('No such log level: %s' % log_level)
        else:
            coloredlogs.install(level=log_level)

    host = get_ip_address(args.get('interface'))
    app.run_server(host=host, port=args.get('port'), debug=args.get('debug'),
        extra_files=[sensor_values_dict])


