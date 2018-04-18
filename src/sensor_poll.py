#!/usr/bin/env python

import argcomplete
import argparse
import atexit
import coloredlogs
import gc
import json
import katcp
import logging
import os
import random
import sys
import time
import traceback
import threading

# from addict import Dict
from collections import OrderedDict
from itertools import izip_longest
from pprint import PrettyPrinter


# This class could be imported from a utility module
class LoggingClass(object):
    @property
    def logger(self):
        name = '.'.join(
            [os.path.basename(sys.argv[0]), self.__class__.__name__])
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
        try:
            self._started = False
            self.primary_client = self.katcp_request(
                which_port=self.katcp_port)
            atexit.register(self.cleanup, self.primary_client)
            assert isinstance(self.primary_client, katcp.client.BlockingClient)
            reply, informs = self.sensor_request(self.primary_client)
            assert reply.reply_ok()
            katcp_array_list = informs[0].arguments
            assert isinstance(katcp_array_list, list)
            self.katcp_array_port, self.katcp_sensor_port = [
                int(i) for i in katcp_array_list[1].split(',')]
            assert isinstance(self.katcp_array_port, int)
            assert isinstance(self.katcp_sensor_port, int)
        except IndexError:
            self.logger.error('No running array on %s:%s!!!!' %
                              (self.katcp_ip, self.katcp_port))
            sys.exit(1)
        except Exception as e:
            self.logger.exception(e.message)
            sys.exit(1)
        else:
            if self._started:
                self._started = False
                self.sec_client = self.katcp_request(
                    which_port=self.katcp_array_port)
                atexit.register(self.cleanup, self.sec_client)

            if self._started:
                self._started = False
                self.sec_sensors_katcp_con = self.katcp_request(
                    which_port=self.katcp_sensor_port)
                atexit.register(self.cleanup, self.sec_sensors_katcp_con)

            self.logger.info("Katcp connection established: IP %s, Primary Port: %s, Array Port: %s,"
                             " Sensor Port: %s" % (self.katcp_ip, self.katcp_port,
                                                   self.katcp_array_port, self.katcp_sensor_port))
            self.input_mapping, self.hostname_mapping = self.do_mapping()

    def katcp_request(self, which_port, katcprequest='array-list', katcprequestArg=None, timeout=10):
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
        # self._started = False
        if not self._started:
            self._started = True
            self.logger.info('Establishing katcp connection on %s:%s' %
                             (self.katcp_ip, which_port))
            client = katcp.BlockingClient(self.katcp_ip, which_port)
            client.setDaemon(True)
            client.start()
            time.sleep(.1)
            try:
                is_connected = client.wait_running(timeout)
                assert is_connected
                self.logger.info('Katcp client connected to %s:%s\n' %
                                 (self.katcp_ip, which_port))
                return client
            except Exception:
                client.stop()
                self.logger.error('Could not connect to katcp, timed out.')

    def sensor_request(self, client, katcprequest='array-list', katcprequestArg=None, timeout=10):
        """
        Katcp requests

        Parameters
        =========
        client: katcp.client.BlockingClient
            katcp running client
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
        try:
            time.sleep(0.3)
            if katcprequestArg:
                reply, informs = client.blocking_request(
                    katcp.Message.request(katcprequest, katcprequestArg), timeout=timeout)
            else:
                reply, informs = client.blocking_request(
                    katcp.Message.request(katcprequest), timeout=timeout)

            assert reply.reply_ok()
            return reply, informs
        except Exception:
            self.logger.exception('Failed to execute katcp command')
            sys.exit(1)

    def cleanup(self, client):
        if self._started:
            self.logger.debug('Some Cleaning Up!!!')
            client.stop()
            time.sleep(0.1)
            if client.is_connected():
                self.logger.error(
                    'Did not clean up client properly, %s' % client.bind_address)
            client = None
            gc.collect

    @property
    def get_sensor_values(self, i=1):
        try:
            assert self.katcp_sensor_port
            for i in xrange(i):
                reply, informs = self.sensor_request(self.sec_sensors_katcp_con,
                                                     katcprequest='sensor-value')
            assert int(reply.arguments[-1])
            yield [inform.arguments for inform in informs]
        except AssertionError:
            self.logger.exception("No Sensors!!! Exiting!!!")
            sys.exit(1)

    @property
    def get_hostmapping(self, i=1):
        try:
            assert self.katcp_sensor_port
            for i in xrange(i):
                reply, informs = self.sensor_request(self.sec_sensors_katcp_con,
                                                     katcprequest='sensor-value', katcprequestArg='hostname-functional-mapping')
            assert int(reply.arguments[-1])
            yield [inform.arguments for inform in informs]
        except AssertionError:
            self.logger.exception("No Sensors!!! Exiting!!!")
            sys.exit(1)

    @property
    def get_inputlabel(self, i=1):
        try:
            assert self.katcp_array_port
            for i in xrange(i):
                reply, informs = self.sensor_request(self.sec_client,
                                                     katcprequest='sensor-value', katcprequestArg='input-labelling')
            assert int(reply.arguments[-1])
            yield [inform.arguments for inform in informs]
        except AssertionError:
            self.logger.exception("No Sensors!!! Exiting!!!")
            sys.exit(1)

    @property
    def get_sensor_dict(self):
        sensor_value_informs = next(self.get_sensor_values)
        self.logger.debug('Converting sensor list to dict!!!')
        # return dict((x[0], x[1:]) for x in [i[2:] for i in sensor_value_informs])
        # return dict((x[0], dict([['status',x[1:]]])) for x in [i[2:] for i in sensor_value_informs])
        # Return with sensor full name and state
        # return dict((x[0], dict([['status',x[1]]])) for x in [i[2:] for i in sensor_value_informs])
        return dict((x[0], x[1]) for x in [i[2:] for i in sensor_value_informs])

    @property
    def get_ordered_sensor_values(self):
        self.logger.debug('Converting sensor dict to ordered!!!')
        _sensor_values = self.get_sensor_dict
        return OrderedDict(sorted(_sensor_values.items()))

    def do_mapping(self):
        self.logger.debug('Mapping input labels and hostnames')
        try:
            hostname_mapping = next(self.get_hostmapping)[-1][-1]
            input_mapping = next(self.get_inputlabel)[-1][-1]
        except Exception:
            self.logger.exception(
                'Serious error occurred, cannot continue!!! Missing sensors')
            sys.exit(1)
        else:
            input_mapping = dict(list(i)[0:3:2] for i in eval(input_mapping))
            input_mapping = dict((v, k) for k, v in input_mapping.iteritems())
            update_maps = []
            for i in input_mapping.values():
                if '_y' in i:
                    i = i.replace('_y', '_xy')
                elif '_x' in i:
                    i = i.replace('_x', '_xy')
                elif 'v' in i:
                    i = i.replace('v', '_vh')
                elif 'h' in i:
                    i = i.replace('h', '_vh')
                else:
                    pass
                update_maps.append(i)

            update_maps = sorted(update_maps)
            input_mapping = dict(
                zip(sorted(input_mapping.keys()), update_maps))
            hostname_mapping = dict((v, k)
                                    for k, v in eval(hostname_mapping).iteritems())
            return [input_mapping, hostname_mapping]

    def combined_Dict_List(self, *args):
        """
        Combining two/more dictionaries into one with the same keys

        Params
        =======
        args: list
            list of dicts to combine

        Return
        =======
        result: dict
            combined dictionaries
        """
        result = {}
        for _dict in args:
            for key in (result.viewkeys() | _dict.keys()):
                if key in _dict:
                    result.setdefault(key, []).extend([_dict[key]])
        return result

    def str_ind_frm_list(self, String, List):
        """
        Find the index of a string in a list

        Params
        =======
        String: str
            String to search in list
        List: list
            List to be searched!

        Return
        =======
        list
        """
        try:
            return [_c for _c, i in enumerate(List) if any(String in x for x in i)][0]
        except Exception:
            self.logger.exception('Failed to find the index of string in list')

    @property
    def map_xhost_sensor(self):
        """
        Needs to be in this format:

        """
        self.logger.debug('Sorting ordered sensor dict by xhosts!!!')
        ordered_sensor_dict = self.get_ordered_sensor_values
        mapping = []
        for key, value in ordered_sensor_dict.iteritems():
            key_s = key.split('.')
            host = key_s[0].lower()
            if host.startswith('fhost') and ('device-status' in key_s):
                new_value = [x.replace('device-status', value)
                             for x in key_s[1:]]
                if 'network-reorder' in new_value:
                    # rename such that, it can fit on html/button
                    new_value[0] = new_value[0].replace(
                        'network-reorder', 'Net-ReOrd')
                new_dict = dict(izip_longest(
                    *[iter([host, new_value])] * 2, fillvalue=""))
                mapping.append(new_dict)
            elif host.startswith('xhost'):
                # Fix for xengines
                # new_value =  [x.replace('device-status', value) for x in key_s[1:]]
                # new_dict = dict(izip_longest(*[iter([host, new_value])] * 2, fillvalue=""))
                # mapping.append(new_dict)
                pass
            else:
                pass
        # Fix for xengines
        return {}

    @property
    def map_fhost_sensors(self):
        """
        {
             'fhost03': [
                            ['SKA-020709', 'warn'],
                            ['fhost00', 'skarab020709-01'],
                            ['ant0_y', 'inputlabel'],
                            ['network', 'nominal'],
                            ['spead-rx', 'failure'],
                            ['Net-ReOrd', 'nominal'],
                            ['cd', 'warn'],
                            ['pfb', 'warn'],
                            ['ct', 'nominal'],
                            ['spead-tx', 'nominal'],
                            ['->XEngine', 'xhost']
                        ]
        }

        """

        self.logger.debug('Sorting ordered sensor dict by fhosts!!!')
        # Abbreviated signal chain
        # F_LRU -> Host -> input_label -> network-trx -> spead-rx -> network-reorder -> cd -> pfb -->>
        #    -->> ct -> spead-tx -> network-trx : [To Xengine ]
        # issue reading cmc3 input labels
        fhost_sig_chain = ['-02', 'input', 'network', 'spead-rx', 'Net-ReOrd', 'cd', 'pfb',
                           # fhost_sig_chain = ['SKA', 'fhost', 'network', 'spead-rx', 'Net-ReOrd', 'cd', 'pfb',
                           'ct', 'spead-tx', '->X']

        ordered_sensor_dict = self.get_ordered_sensor_values
        mapping = []
        for key, value in ordered_sensor_dict.iteritems():
            key_s = key.split('.')
            host = key_s[0].lower()
            if host.startswith('fhost') and ('device-status' in key_s):
                new_value = [x.replace('device-status', value)
                             for x in key_s[1:]]
                if 'network-reorder' in new_value:
                    # rename such that, it fits on html/button
                    new_value[0] = new_value[0].replace(
                        'network-reorder', 'Net-ReOrd')
                new_dict = dict(izip_longest(
                    *[iter([host, new_value])] * 2, fillvalue=""))
                mapping.append(new_dict)

        new_mapping = self.combined_Dict_List(*mapping)

        for host, _list in new_mapping.iteritems():
            if host in self.hostname_mapping:
                new_hostname = host.replace('fhost', '') + self.hostname_mapping[host].replace(
                    'skarab', '-').replace('-01', '')
            _ = [value.insert(0, new_hostname)
                 for value in _list if len(value) == 1]

        for host, values in new_mapping.iteritems():
            if host in self.hostname_mapping:
                values.insert(
                    2, [self.input_mapping[self.hostname_mapping[host]], 'inputlabel'])
                values.append(['->XEngine', 'xhost'])

        # Update mappings
        _ = [listA.insert(_index, listA.pop(self.str_ind_frm_list(_sig, listA)))
             for _, listA in new_mapping.iteritems() for _index, _sig in enumerate(fhost_sig_chain)]
        return new_mapping

    def merged_sensors_dict(self, f_sensors, x_sensors):
        """
        merge two dictionaries
        https://stackoverflow.com/questions/38987/how-to-merge-two-dictionaries-in-a-single-expression#26853961
        """
        merged_sensors = f_sensors.copy()
        merged_sensors.update(x_sensors)
        return merged_sensors

    # @property
    def create_dumps_dir(self):
        """
        Create json dumps directory
        """
        # Conflicted: To store in /tmp or not to store in , that is the question
        try:
            _dir, _name = os.path.split(
                os.path.dirname(os.path.realpath(__file__)))
        except Exception:
            _dir, _name = os.path.split(
                os.path.dirname(os.path.realpath(__name__)))
        path = _dir + '/json_dumps'
        if not os.path.exists(path):
            self.logger.info('Created %s for storing json dumps.' % path)
            os.makedirs(path)

    def write_sorted_sensors_to_file(self,):
        sensors = self.merged_sensors_dict(
            self.map_fhost_sensors, self.map_xhost_sensor)
        self.create_dumps_dir()
        if args.get('sensor_json', False):
            try:
                cur_path = os.path.split(
                    os.path.dirname(os.path.abspath(__file__)))[0]
            except Exception:
                cur_path = os.path.split(
                    os.path.dirname(os.path.abspath(__name__)))[0]
            _filename = '%s/json_dumps/sensor_values.json' % cur_path
            self.logger.info('Updating sensors file: %s' % _filename)
            with open(_filename, 'w') as outfile:
                json.dump(sensors, outfile, indent=4, sort_keys=True)
            self.logger.info('Done updating sensors file!!!')
        # return sensors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Receive data from a CBF and play.')
    parser.add_argument('--katcp', dest='katcp_con', action='store', default='127.0.0.1:7147',
                        help='IP:Port primary interface [Default: 127.0.0.1:7147]')
    parser.add_argument('--poll-sensors', dest='poll', action='store', default=10, type=int,
                        help='Poll the sensors every 10 seconds [Default: 10]')
    parser.add_argument('--json', dest='sensor_json', action='store_true', default=False,
                        help='Write sensors to jsonFile')
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
            logging.basicConfig(level=getattr(
                logging, log_level), format=log_format)
        except AttributeError:
            raise RuntimeError('No such log level: %s' % log_level)
        else:
            if log_level == 'DEBUG':
                coloredlogs.install(level=log_level, fmt=log_format)
            else:
                coloredlogs.install(level=log_level)

    if args.get('katcp_con'):
        katcp_ip, katcp_port = args.get('katcp_con').split(':')

    sensor_poll = SensorPoll(katcp_ip, katcp_port)
    main_logger = LoggingClass()
    try:
        poll_time = args.get('poll')
        main_logger.logger.info(
            'Begin sensor polling every %s seconds!!!' % poll_time)
        while True:
            sensor_poll.write_sorted_sensors_to_file()
            main_logger.logger.debug('Updating sensor on dashboard!!!')
            main_logger.logger.info(
                '---------------------RELOADING SENSORS---------------------')
            time.sleep(poll_time)
    except Exception as e:
        main_logger.logger.exception(e.message)
        sys.exit(1)
