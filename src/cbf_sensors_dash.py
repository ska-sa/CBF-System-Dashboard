#!/usr/bin/env python

# ====================================
# TODO
# Multi-Page Apps and URL Support
# https://dash.plot.ly/urls

import argcomplete
import argparse
import coloredlogs
import Config
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
import time
import types
import urllib2

from collections import OrderedDict
from dash.dependencies import Event, Input, Output
from pprint import PrettyPrinter

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
                'backgroundColor': Config.COLORS[0]['background'],
                'color': Config.COLORS[0]['color'],
                'display': 'inline-block'
                }
        elif state == 'warn':
            style = {
                'backgroundColor': Config.COLORS[1]['background'],
                'color': Config.COLORS[1]['color'],
                'display': 'inline-block'
                }
        elif state == 'error':
            style = {
                'backgroundColor': Config.COLORS[2]['background'],
                'color': Config.COLORS[2]['color'],
                'display': 'inline-block'
                }
        elif state == 'failure':
            style = {
                'backgroundColor': Config.COLORS[3]['background'],
                'color': Config.COLORS[3]['color'],
                'font-weight': 'bold',
                'font-style': 'italic',
                'display': 'inline-block',
                }
        else:
            style = {
                'backgroundColor': Config.COLORS[4]['background'],
                'color': Config.COLORS[4]['color'],
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
    # Button click redirection -- https://github.com/plotly/dash-html-components/issues/16
    _button = [html.Button(children=child,  style=set_style(_status), type='button',
                            className="btn-xl", id='submit-button', n_clicks=0)]
    if '->XEngine' in child:
        return _button
    elif '-020' in child:
        return _button
    else:
        _button.append(html.Hr(className='horizontal'))
        return _button


def generate_line(host):
    """
    Params
    ======

    Return
    ======

    """
    # print  [      (i[0], 'id_%s' % i[0], i[-1]) for i in sensor_format.get(host)]
    # return [add_buttons(i[0], 'id_%s' % i[0], i[-1]) for i in sensor_format.get(host)]
    return [add_buttons(i[0], 'id_%s' % _c, i[-1]) for _c, i in enumerate(sensor_format.get(host))]


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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Should probably put the description here!')
    parser.add_argument('-i', '--interface', dest='interface', action='store', default='eth0',
                        help='network interface [Default: eth0]')
    parser.add_argument('-p', '--port', dest='port', action='store_true', default=8888,
                        help='flask port [Default: 8888]')
    parser.add_argument('--nodebug', dest='debug', action='store_false', default=True,
                        help='flask with no debug [Default: False]')
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

    sensor_format = get_sensors(sensor_values_json)
    host = get_ip_address(args.get('interface'))


    title = Config.title
    # metadata = Config.metadata
    codepen_link = Config.js_link['codepen']
    jquery_link = Config.js_link['jquery']
    try:
        css_link = "https://raw.githubusercontent.com/ska-sa/CBF-System-Dashboard/master/src/css/KoJoZq.css"
        assert file_exists(css_link)
    except AssertionError:
        css_link = Config.css_link

    app = dash.Dash(name=title)
    # app.config.supress_callback_exceptions = True
    # Monkey patching
    app.title = types.StringType(title)
    # app.meta = types.StringType(metadata)

    # HTML Layout
    html_layout = html.Div([
        html.H3('Last Updated: %s' % time.ctime(), style={"margin":0}),
        html.Div(generate_table()),
        # html.Div([
        #     html.Br(),
        #     html.Div(id='output-state')
        #     ])
        ])

    app.layout = html.Div([
        #html_layout])
        html.Div([
            dcc.Interval(id='refresh', interval=10000),
            html.Div(id='content', className="container")
            ]),

        # html.Br(), html.Div(id='output-state')
        ])


    # Update the `content` div with the `layout` object.
    # When you save this file, `debug=True` will re-run
    # this script, serving the new layout
    @app.callback(Output('content', 'children'), events=[Event('refresh', 'interval')])
    def display_layout():
        return html_layout

    # @app.callback(Output('output-state', 'children'), [Input('submit-button', 'n_clicks'), ])
    # def update_output(n_clicks,):
    #     if n_clicks:
    #         logger.info('Button clicked')
    #         # import IPython; globals().update(locals()); IPython.embed(header='Python Debugger')

    #         return json.dumps(OrderedDict(sensor_format), indent=4)

    app.scripts.append_script({"external_url": codepen_link})
    app.scripts.append_script({"external_url": jquery_link})
    app.css.append_css({"external_url": css_link})
    app.run_server(host=host, port=args.get('port'), debug=args.get('debug'),
        extra_files=[sensor_values_json])


