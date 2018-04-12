#!/usr/bin/env python

import os
import argparse
import argcomplete
import atexit
import coloredlogs
import katcp
import logging
import sys
import time
import traceback
import random
import json
import gc

# from addict import Dict
from collections import OrderedDict
from itertools import izip_longest
from pprint import PrettyPrinter


# This class could be imported from a utility module
class LoggingClass(object):
    @property
    def logger(self):
        name = '.'.join([__name__, self.__class__.__name__])
        return logging.getLogger(name)

class SensorPoll(LoggingClass):

    def __init__(self, katcp_ip='127.0.0.1', katcp_port=7147):
        """
        Parameters
        =========
        katcp_ip: str
            IP to connect to! [Defaults: 127.0.0.1]
        katcp_port: int
            Port to connect to! [Defaults: 7147]
        """
        self.katcp_ip = katcp_ip
        self.katcp_port = katcp_port
        atexit.register(self.cleanup)
        try:
            reply, informs = self.katcp_request()
            assert reply.reply_ok()
            katcp_array_list = informs[0].arguments
        except IndexError:
            self.logger.exception('Seems like there is no running array!!!!')
            sys.exit(1)
        except Exception as e:
            self.logger.exception(e.message)
            sys.exit(1)
        else:
            self.katcp_array_name = katcp_array_list[0]
            self.katcp_array_port, self.katcp_sensor_port = katcp_array_list[1].split(',')
            self.logger.info("Katcp connection established: IP %s, Array Port: %s, Sensor Port %s" %
                        (self.katcp_ip, self.katcp_array_port, self.katcp_sensor_port))

    def cleanup(self):
        if self._started:
            self.logger.info('Some Cleaning Up!!!')
            self.client.stop()
            time.sleep(0.1)
            if self.client.is_connected():
                self.logger.error('Did not clean up client properly')
            self.client = None
            gc.collect

    def katcp_request(self, which_port=7147, katcprequest='array-list', katcprequestArg=None, timeout=10):
        """
        Katcp requests

        Parameters
        =========
        which_port: str
            Katcp port to connect to!
        katcprequest: str
            Katcp requests messages [Defaults: 'array-list']
        katcprequestArg: str
            katcp requests messages arguments eg. array-list array0 [Defaults: None]
        timeout: int
            katcp timeout [Defaults :10]

        Return
        ======
        reply, informs : tuple
            katcp request messages
        """
        self._started = False
        if not self._started:
            self.client = katcp.BlockingClient(self.katcp_ip, which_port)
            self.client.setDaemon(True)
            self.client.start()
            self._started = True
        is_connected = self.client.wait_running(timeout)
        if not is_connected:
            self.client.stop()
            self.logger.error('Could not connect to katcp, timed out.')
            return
        try:
            time.sleep(0.3)
            if katcprequestArg:
                reply, informs = self.client.blocking_request(katcp.Message.request(katcprequest, katcprequestArg),
                                                         timeout=timeout)
            else:
                reply, informs = self.client.blocking_request(katcp.Message.request(katcprequest),
                                                         timeout=timeout)

            assert reply.reply_ok()
        except Exception:
            self.logger.exception('Failed to execute katcp command')
            return None
        else:
            return reply, informs

    @property
    def get_sensor_values(self, i=1):
        self.logger.info('Connecting to running sensors servlet and getting sensors')
        try:
            assert self.katcp_sensor_port
            for i in xrange(i):
                reply, informs = self.katcp_request(which_port=self.katcp_sensor_port,
                    katcprequest='sensor-value')
            self.logger.info('Retrieved sensors successfully')
            assert int(reply.arguments[-1])
            yield [inform.arguments for inform in informs]
        except AssertionError:
            self.logger.exception("No Sensors!!! Exiting!!!")
            sys.exit(1)

    @property
    def get_sensor_dict(self):
        sensor_value_informs = next(self.get_sensor_values)
        self.logger.info('Converting sensor list to dict!!!')
        # return dict((x[0], x[1:]) for x in [i[2:] for i in sensor_value_informs])
        # return dict((x[0], dict([['status',x[1:]]])) for x in [i[2:] for i in sensor_value_informs])
        # Return with sensor full name and state
        return dict((x[0], dict([['status',x[1]]])) for x in [i[2:] for i in sensor_value_informs])

    @property
    def get_ordered_sensor_values(self):
        self.logger.info('Converting sensor dict to ordered!!!')
        _sensor_values = self.get_sensor_dict
        return OrderedDict(sorted(_sensor_values.items()))

    @property
    def get_sorted_sensors_by_host(self):
        """
        Will look like!!!
        ==================
        {
            "FHOSTS": [
                [
                    {
                        "fhost00": [
                            "cd",
                            "delay0-updating"
                        ]
                    },
                    [
                        "unknown",
                        ""
                    ]
                ],
                [
                    {
                        "fhost00": [
                            "cd",
                            "delay1-updating"
                        ]
                    },
        """

        self.logger.info('Sorting ordered sensor dict by hosts!!!')
        ordered_sensor_dict = self.get_ordered_sensor_values
        mapping = {'FHOSTS': [], 'XHOSTS': [], 'SYSTEM': []}
        for i, v in ordered_sensor_dict.iteritems():
            i = i.split('.')
            if i[0].startswith('fhost'):
                new_i = dict(izip_longest(
                    *[iter([i[0], i[1:]])] * 2, fillvalue=""))
                mapping['FHOSTS'].append([new_i, v])
            elif i[0].startswith('xhost'):
                new_i = dict(izip_longest(
                    *[iter([i[0], i[1:]])] * 2, fillvalue=""))
                mapping['XHOSTS'].append([new_i, v])
            else:
                new_i = dict(izip_longest(
                    *[iter([i[0], i[1:]])] * 2, fillvalue=""))
                mapping['SYSTEM'].append([new_i, v])
        return mapping


    def write_sorted_sensors_to_file(self,):
        sensors = self.get_sorted_sensors_by_host
        sensors_dict = self.get_sensor_dict
        if args.get('sensor_json', False):
            cur_path = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
            _filename = '%s/sensor_values_by_host.json' % cur_path
            self.logger.info('Writing sorted sensors by hosts to file: %s' % _filename)
            with open(_filename, 'w') as outfile:
                json.dump(sensors, outfile, indent=4, sort_keys=True)

            _filename = '%s/sensor_values_dict.json' % cur_path
            self.logger.info('Writing sorted sensors by hosts to file: %s' % _filename)
            with open(_filename, 'w') as outfile:
                json.dump(sensors_dict, outfile, indent=4, sort_keys=True)
            self.logger.info('Done writing to file')
        return sensors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Receive data from a CBF and play.')
    parser.add_argument('--katcp', dest='katcp_con', action='store', default='127.0.0.1:7147',
                        help='IP:Port primary interface [Default: 127.0.0.1:7147]')
    parser.add_argument('--poll-sensors', dest='poll', action='store_true', default=False,
                        help='Poll the sensors every 10 seconds')
    parser.add_argument('--json', dest='sensor_json', action='store_true', default=False,
                        help='Write sensors to jsonFile')
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

    if args.get('katcp_con'):
        katcp_ip, katcp_port = args.get('katcp_con').split(':')

    sensor_poll = SensorPoll(katcp_ip, katcp_port)
    main_logger = LoggingClass()

    # Useful for debugging!!!
    # pretty print
    # pp.pprint(sensor_poll.get_sorted_sensors_by_host)
    try:
        poll = args.get('poll', False)
        assert poll
        poll_time = 10
        main_logger.logger.info('Begin sensor polling every %s seconds!!!' % poll_time)
        while poll:
            # TODO: Upload sensors to dashboard
            sensor_values = sensor_poll.write_sorted_sensors_to_file()
            # pretty print json dumps
            # print json.dumps(sensor_poll.get_sorted_sensors_by_host, indent=4)
            # pp.pprint(sensor_values)
            main_logger.logger.debug('Updating sensor on dashboard!!!')
            main_logger.logger.info('RELOADING SENSORS')
            time.sleep(poll_time)
    except Exception as e:
        main_logger.logger.exception(e.message)
        import IPython
        globals().update(locals())
        IPython.embed(header='Lets Play')
