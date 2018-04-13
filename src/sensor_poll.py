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

# from addict import Dict
from collections import OrderedDict
from itertools import izip_longest
from pprint import PrettyPrinter


# This class could be imported from a utility module
class LoggingClass(object):
    @property
    def logger(self):
        name = '.'.join([os.path.basename(sys.argv[0]), self.__class__.__name__])
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
        # self._started = False
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
            self.input_mapping, self.hostname_mapping = self.do_mapping()

    def cleanup(self):
        if self._started:
            self.logger.debug('Some Cleaning Up!!!')
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
            self._started = True
            self.logger.info('Connecting to running sensors servlet and getting sensors')
            self.client = katcp.BlockingClient(self.katcp_ip, which_port)
            self.client.setDaemon(True)
            self.client.start()
            time.sleep(.1)
        is_connected = self.client.wait_running(timeout)
        if not is_connected:
            self.client.stop()
            self.logger.error('Could not connect to katcp, timed out.')
            return
        try:
            time.sleep(0.3)
            if katcprequestArg:
                reply, informs = self.client.blocking_request(
                    katcp.Message.request(katcprequest, katcprequestArg), timeout=timeout)
            else:
                reply, informs = self.client.blocking_request(
                    katcp.Message.request(katcprequest), timeout=timeout)

            assert reply.reply_ok()
        except Exception:
            self.logger.exception('Failed to execute katcp command')
            return None
        else:
            return reply, informs

    @property
    def get_sensor_values(self, i=1):
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
    def get_hostmapping(self, i=1):
        try:
            assert self.katcp_sensor_port
            for i in xrange(i):
                reply, informs = self.katcp_request(which_port=self.katcp_sensor_port,
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
                reply, informs = self.katcp_request(which_port=self.katcp_array_port,
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
            self.logger.exception('Serious error occurred, cannot continue!!! Missing sensors')
            sys.exit(1)
        else:
            input_mapping = dict(list(i)[0:3:2] for i in eval(input_mapping))
            input_mapping = dict((v,k) for k,v in input_mapping.iteritems())
            update_maps = []
            for i in input_mapping.values():
                if '_y' in i:
                    i = i.replace('_y', '_xy')
                elif '_x' in i:
                    i = i.replace('_x', '_xy')
                elif '_v' in i:
                    i = i.replace('_v', '_vh')
                elif '_h' in i:
                    i = i.replace('_v', '_vh')
                else:
                    pass
                update_maps.append(i)
            update_maps = sorted(update_maps)
            input_mapping = dict(zip(input_mapping.keys(), update_maps))
            hostname_mapping = dict((v,k) for k,v in eval(hostname_mapping).iteritems())
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
            if host.startswith('fhost') and ('device-status' in key_s) :
                new_value =  [x.replace('device-status', value) for x in key_s[1:]]
                if 'network-reorder' in new_value:
                    # rename such that, it can fit on html/button
                    new_value[0] = new_value[0].replace('network-reorder', 'Net-ReOrd')
                new_dict = dict(izip_longest(*[iter([host, new_value])] * 2, fillvalue=""))
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
        Needs to be in this format

        {
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
                                    # missing sensor
                                    # ['requant', 'warn'],
                                    ['ct', 'nominal'],
                                    ['spead-tx','nominal'],
                                    ['network', 'error'],
                                    ['->XEngine', 'xhost']
                             ],
         }

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
        fhost_sig_chain = ['SKA', 'fhost', 'input', 'network', 'spead-rx', 'Net-ReOrd', 'cd', 'pfb',
        # fhost_sig_chain = ['SKA', 'fhost', 'network', 'spead-rx', 'Net-ReOrd', 'cd', 'pfb',
                           'ct', 'spead-tx', '->X']

        ordered_sensor_dict = self.get_ordered_sensor_values
        mapping = []
        for key, value in ordered_sensor_dict.iteritems():
            key_s = key.split('.')
            host = key_s[0].lower()
            if host.startswith('fhost') and ('device-status' in key_s) :
                new_value =  [x.replace('device-status', value) for x in key_s[1:]]
                if 'network-reorder' in new_value:
                    # rename such that, it fits on html/button
                    new_value[0] = new_value[0].replace('network-reorder', 'Net-ReOrd')
                new_dict = dict(izip_longest(*[iter([host, new_value])] * 2, fillvalue=""))
                mapping.append(new_dict)

        new_mapping = self.combined_Dict_List(*mapping)

        for host, _list in new_mapping.iteritems():
            if host in self.hostname_mapping:
                new_hostname = self.hostname_mapping[host].upper().replace('RAB', '-').split('-01')[0]
            _ = [value.insert(0, new_hostname) for value in _list if len(value) == 1]

        for host, values in new_mapping.iteritems():
            if host in self.hostname_mapping:
                new_hostname = self.hostname_mapping[host].upper().replace('RAB', '-').split('-01')[0]
                values.insert(1, [host, self.hostname_mapping[host]])
                # issues when reason cmc3 input labels
                values.insert(2, [self.input_mapping[self.hostname_mapping[host]], 'inputlabel'])
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


    @property
    def create_dumps_dir(self):
        """
        Create json dumps directory
        """
        # Conflicted: To store in /tmp or not to store in , that is the question
        _dir, _name = os.path.split(os.path.dirname(os.path.realpath(__file__)))
        path = _dir + '/json_dumps'
        if not os.path.exists(path):
            self.logger.info('Created %s for storing json dumps.'% path)
            os.makedirs(path)

    def write_sorted_sensors_to_file(self,):
        sensors = self.merged_sensors_dict(self.map_fhost_sensors, self.map_xhost_sensor)
        self.create_dumps_dir
        if args.get('sensor_json', False):
            cur_path = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
            # _filename = '%s/sensor_values_by_host.json' % cur_path
            # self.logger.info('Writing sorted sensors by hosts to file: %s' % _filename)
            # with open(_filename, 'w') as outfile:
            #     json.dump(sensors, outfile, indent=4, sort_keys=True)

            _filename = '%s/json_dumps/sensor_values.json' % cur_path
            self.logger.info('Writing sorted sensors by hosts to file: %s' % _filename)
            with open(_filename, 'w') as outfile:
                json.dump(sensors, outfile, indent=4, sort_keys=True)
            self.logger.info('Done writing to sensors to file')
        return sensors


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
            logging.basicConfig(level=getattr(logging, log_level), format=log_format)
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

    # Useful for debugging!!!
    # pretty print
    # pp.pprint(sensor_poll.get_sorted_sensors_by_host)
    try:
        poll_time = args.get('poll')
        main_logger.logger.info('Begin sensor polling every %s seconds!!!' % poll_time)
        while True:
            # TODO: Upload sensors to dashboard
            sensor_values = sensor_poll.write_sorted_sensors_to_file()
            # pretty print json dumps
            # print json.dumps(sensor_poll.get_sorted_sensors_by_host, indent=4)
            # pp.pprint(sensor_values)
            main_logger.logger.debug('Updating sensor on dashboard!!!')
            main_logger.logger.info('---------------------RELOADING SENSORS---------------------')
            time.sleep(poll_time)
    except Exception as e:
        main_logger.logger.exception(e.message)
        sys.exit(1)
