#!/usr/bin/env python

import argparse
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
from pprint import PrettyPrinter

import argcomplete
import coloredlogs
import dash
import dash_core_components as dcc
import dash_html_components as html
import flask
from dash.dependencies import Event, Input, Output
from flask import send_from_directory

import Config

pp = PrettyPrinter(indent=4)
log_level = None
log_format = "%(asctime)s - %(name)s:%(process)d - %(levelname)s - %(module)s - %(pathname)s : %(lineno)d - %(message)s"

parser = argparse.ArgumentParser(
    description="Should probably put the description here!"
)
parser.add_argument(
    "-i",
    "--interface",
    dest="interface",
    action="store",
    default="eth0",
    help="network interface [Default: eth0]",
)
parser.add_argument(
    "-p",
    "--port",
    dest="port",
    action="store_true",
    default=8888,
    help="flask port [Default: 8888]",
)
parser.add_argument(
    "--nodebug",
    dest="debug",
    action="store_false",
    default=True,
    help="flask with no debug [Default: False]",
)
parser.add_argument(
    "--nothread",
    dest="threaded",
    action="store_false",
    default=True,
    help="flask with threading [Default: False]",
)
parser.add_argument(
    "--path",
    dest="sensor_path",
    action="store",
    default=None,
    help="path to where the sensor data .json file is!",
)
parser.add_argument(
    "--loglevel",
    dest="log_level",
    action="store",
    default="INFO",
    help="log level to use, default INFO, options INFO, DEBUG, ERROR",
)

argcomplete.autocomplete(parser)
args = vars(parser.parse_args())


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
        if state == "nominal":
            style = {
                "backgroundColor": Config.COLORS[0]["background"],
                "color": Config.COLORS[0]["color"],
                "display": "inline-block",
            }
        elif state == "warn":
            style = {
                "backgroundColor": Config.COLORS[1]["background"],
                "color": Config.COLORS[1]["color"],
                "display": "inline-block",
            }
        elif state == "error":
            style = {
                "backgroundColor": Config.COLORS[2]["background"],
                "color": Config.COLORS[2]["color"],
                "display": "inline-block",
            }
        elif state == "failure":
            style = {
                "backgroundColor": Config.COLORS[3]["background"],
                "color": Config.COLORS[3]["color"],
                "font-weight": "bold",
                "font-style": "italic",
                "display": "inline-block",
            }
        else:
            style = {
                "backgroundColor": Config.COLORS[4]["background"],
                "color": Config.COLORS[4]["color"],
                "display": "inline-block",
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
    _button = [
        html.Button(
            children=child,
            style=set_style(_status),
            type="button",
            className="btn-xl",
            id=_id,
            n_clicks=0,
        )
    ]
    # if '-020' in child:
    #     return html.A(_button, id='button', href='/page-2')
    # else:
    _button.append(html.Hr(className="horizontal"))
    return html.A(_button, id="button", href="/page-2")


def generate_line(host):
    """
    Params
    ======

    Return
    ======

    """
    return [
        add_buttons(i[0], "id_%s_%s" % (host, _c), i[-1])
        for _c, i in enumerate(sensor_format.get(host))
    ]


def generate_table():
    """
    Params
    ======

    Return
    ======

    """
    return [
        html.Div(
            [
                html.Span(children=i, style={"display": "inline-block"})
                for i in generate_line(x)
            ]
        )
        for x in sorted(sensor_format.keys())
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
    return socket.inet_ntoa(
        fcntl.ioctl(
            s.fileno(), 0x8915, struct.pack("256s", ifname[:15])  # SIOCGIFADDR
        )[20:24]
    )


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
    request.get_method = lambda: "HEAD"
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
    logger.info("Reading latest sensor values from %s" % json_file)
    with open(json_file) as json_data:
        data = json.load(json_data)
        return data


if args.get("log_level", "INFO"):
    log_level = args.get("log_level", "INFO").upper()
    try:
        logging.basicConfig(level=getattr(logging, log_level), format=log_format)
        logger = logging.getLogger(os.path.basename(sys.argv[0]))
    except AttributeError:
        raise RuntimeError("No such log level: %s" % log_level)
    else:
        if log_level == "DEBUG":
            coloredlogs.install(level=log_level, fmt=log_format)
        else:
            coloredlogs.install(level=log_level)

if not args.get("sensor_path"):
    try:
        cur_path = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
    except NameError:
        cur_path = os.path.split(os.path.dirname(os.path.abspath(__name__)))[0]

    try:
        json_dumps_dir = os.path.join(cur_path + "/json_dumps")
        assert os.path.exists(json_dumps_dir)
        sensor_values_json = max(
            glob.iglob(json_dumps_dir + "/sensor_values.json"), key=os.path.getctime
        )
    except AssertionError:
        logger.error("No json dump file. Exiting!!!")
        sys.exit(1)
else:
    sensor_values_json = args.get("sensor_path")

try:
    ordered_sensor_dict = get_sensors(json_dumps_dir + "/ordered_sensor_values.json")
except:
    ordered_sensor_dict = {}

sensor_format = get_sensors(sensor_values_json)
host = get_ip_address(args.get("interface"))

title = Config.title
refresh_time = int(Config.refresh_time)

app = dash.Dash(name=title)
try:
    css_link = Config.css_link
    logger.info("Loading css/js from URL: %s" % css_link)
    assert file_exists(css_link)
    app.css.config.serve_locally = False
    app.scripts.config.serve_locally = False
except AssertionError:
    logger.info("Loading local css/js files")
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
else:
    app.css.append_css({"external_url": css_link})

# Monkey patching
app.title = types.StringType(title)
# metadata = Config.metadata
# app.meta = types.StringType(metadata)

# HTML Layout
html_layout = html.Div(
    [
        html.H3(
            "Last Updated: %s" % time.ctime(), style={"margin": 0, "color": "green"}
        ),
        html.Div(generate_table()),
    ]
)

app.layout = html.Div(
    [
        html.Link(rel="stylesheet", href="/static/stylesheet.css"),
        html.Div(
            [
                # Each "page" will modify this element
                html.Div(id="content-container"),
                # This Location component represents the URL bar
                dcc.Location(id="url", refresh=False),
            ]
        ),
        html.Div(
            [dcc.Interval(id="refresh", interval=refresh_time), html.Div(id="content")]
        ),
    ]
)

# Update the `content` div with the `layout` object.
# When you save this file, `debug=True` will re-run this script, serving the new layout
@app.callback(Output("content", "children"), events=[Event("refresh", "interval")])
def display_layout():
    return html_layout


@app.server.route("/static/<path:path>")
def static_file(path):
    static_folder = os.path.join(os.getcwd(), "static")
    logger.info("Loaded css/js from %s" % static_folder)
    return send_from_directory(static_folder, path)


@app.callback(Output("content-container", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/":
        # return html_layout
        pass
    elif pathname == "/page-2":
        try:
            _sensors = json.dumps(
                OrderedDict(ordered_sensor_dict),
                indent=4,
                sort_keys=True,
                separators=(",", ": "),
            )
        except:
            _sensors = json.dumps(
                OrderedDict(sensor_format),
                indent=4,
                sort_keys=True,
                separators=(",", ": "),
            )

        return html.Div([dcc.Link(html.Pre(_sensors), href="/"), html.Br()])
    else:
        return html.Div(
            [
                html.A(
                    "I guess this is like a 404 - no content available. Click to Go Home",
                    href="/",
                )
            ]
        )


if __name__ == "__main__":
    app.run_server(
        host=host,
        port=args.get("port"),
        debug=args.get("debug"),
        extra_files=[sensor_values_json],
        threaded=args.get("threaded"),
    )
