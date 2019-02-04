#!/usr/bin/env python

import argcomplete
import argparse
import atexit
import json
import functools
import time
import katcp
import os
import ipaddress
import socket

from collections import OrderedDict
from itertools import izip_longest
from ast import literal_eval as evaluate
from pprint import PrettyPrinter

from utils import (
    LoggingClass,
    combined_Dict_List,
    merge_dicts,
    get_list_index,
    swap_dict,)


def retry(func, count=20, wait_time=300):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        retExc = TypeError
        for _ in xrange(count):
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    retExc = exc
                    time.sleep(wait_time)
                    continue
                break
        raise retExc
    return wrapper


class SensorPoll(LoggingClass):
    def __init__(self, katcp_ip="10.103.254.6", katcp_port=7147):
        """
        Parameters
        =========
        katcp_ip: str
            IP to connect to! [Defaults: 10.103.254.6]
        katcp_port: int
            Port to connect to! [Defaults: 7147]
        """
        try:
            self.katcp_ip = katcp_ip
            ipaddress.ip_address(u"{}".format(self.katcp_ip))
            self.hostname = ''.join(socket.gethostbyaddr(katcp_ip)[1])
        except Exception:
            self.logger.exception("Invalid KATCP_IP!")
            raise
        self.katcp_port = katcp_port
        self._kcp_connect()

    @retry
    def _kcp_connect(self):
        """
        """
        try:
            self._started = False
            self.primary_client = self.katcp_request(which_port=self.katcp_port)
            atexit.register(self.cleanup, self.primary_client)
            assert isinstance(self.primary_client, katcp.client.BlockingClient)
            reply, informs = self.sensor_request(self.primary_client)
            assert reply.reply_ok()
            self._prim_clnt_informs = {}
            for inform in informs:
                try:
                    array_port, sensor_port = inform.arguments[1].split(',')
                    self._prim_clnt_informs[inform.arguments[0]] = [{
                        "array_port": array_port,
                        "sensor_port": sensor_port,
                        }]
                except Exception:
                    self.logger.exception("Failed to create informs dictionary.")


            sec_client_dict = {}
            if self._started:
                self._started = False
            self._input_mapping = {}
            for _array, values in self._prim_clnt_informs.iteritems():
                for _key, _value in values[0].iteritems():
                    if _key == 'array_port':
                        if self._started:
                            self._started = False
                        _client_connect = self.katcp_request(_value)
                        assert _client_connect.running()
                        _input_labels = evaluate(self.get_inputlabel(_client_connect)[-1][-1])
                        self._input_mapping[_array] = [{
                            "{}.input_mapping".format(_array): swap_dict(dict(
                                list(i)[0:3:2] for i in _input_labels))
                            }]

                        sec_client_dict[_array] = [{
                                "{}.secondary_client".format(_array): _client_connect
                            }]
            # perhaps a better var name
            new_client_informs = merge_dicts(self._prim_clnt_informs, sec_client_dict)

            # Cleanup
            for _array, value in new_client_informs.iteritems():
                for sec_client in value:
                    if 'secondary_client' in sec_client.keys()[0]:
                        atexit.register(self.cleanup, sec_client.values()[0])

            sec_sensors_client_dict = {}
            self._hostname_mapping = {}
            if self._started:
                self._started = False
            for _array, values in self._prim_clnt_informs.iteritems():
                for _key, _value in values[0].iteritems():
                    if _key == 'sensor_port':
                        if self._started:
                            self._started = False
                        _client_connect = self.katcp_request(_value)
                        assert _client_connect.running()
                        self._hostname_mapping[_array] = [{
                            "{}.hostname_mapping".format(_array): swap_dict(evaluate(
                                self.get_hostmapping(_client_connect)[-1][-1]))
                            }]
                        sec_sensors_client_dict[_array] = [{
                                "{}.secondary_sensors_client".format(_array): _client_connect
                            }]

            new_client_informs = merge_dicts(self._prim_clnt_informs, sec_sensors_client_dict)
            # Cleanup
            for _array, value in new_client_informs.iteritems():
                for sec_sens_client in value:
                    if 'secondary_sensors_client' in sec_sens_client.keys()[0]:
                        atexit.register(self.cleanup, sec_sens_client.values()[0])

            if self._started:
                self._started = False
        except Exception:
            self.logger.exception(
                "No running array on {}:{}!!!!".format(self.katcp_ip, self.katcp_port))
            if self.primary_client.is_connected():
                self.cleanup(self.primary_client)
            raise

    def katcp_request(self, which_port, katcprequest="array-list", katcprequestArg=None, timeout=10):
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
            self.logger.info("Establishing katcp connection on {}:{}".format(self.katcp_ip,
                which_port))
            client = katcp.BlockingClient(self.katcp_ip, which_port)
            client.setDaemon(True)
            client.start()
            time.sleep(0.2)
            try:
                is_connected = client.wait_running(timeout)
                assert is_connected
                self.logger.info("Katcp client connected to {}:{}\n".format(self.katcp_ip,
                    which_port))
                return client
            except Exception:
                client.stop()
                self.logger.error("Could not connect to katcp, timed out.")

    def sensor_request(self, client, katcprequest="array-list", katcprequestArg=None, timeout=10):
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
            if katcprequestArg:
                reply, informs = client.blocking_request(
                    katcp.Message.request(katcprequest, katcprequestArg),
                    timeout=timeout,
                )
            else:
                reply, informs = client.blocking_request(
                    katcp.Message.request(katcprequest), timeout=timeout
                )
            assert reply.reply_ok()
        except Exception:
            self.logger.error("Failed to execute katcp command")
            # time.sleep(20)
            raise
        else:
            return reply, informs

    def cleanup(self, client):
        if self._started:
            self.logger.debug("Some Cleaning Up!!!")
            client.stop()
            time.sleep(0.1)
            if client.is_connected():
                self.logger.error("Did not clean up client properly, %s" % client.bind_address)

    ################################################################################################
    def get_sensor_values(self, sensor_katcp_client):
        try:
            reply, informs = self.sensor_request(sensor_katcp_client, katcprequest="sensor-value")
            assert reply.reply_ok()
            assert int(reply.arguments[-1])
            return [inform.arguments for inform in informs]
        except AssertionError:
            self.logger.error("No Sensors!!! Exiting!!!")
            raise

    def get_hostmapping(self, sensor_katcp_client):
        try:
            reply, informs = self.sensor_request(sensor_katcp_client, katcprequest="sensor-value",
                katcprequestArg="hostname-functional-mapping",)
            assert reply.reply_ok()
            assert int(reply.arguments[-1])
            return [inform.arguments for inform in informs]
        except AssertionError:
            self.cleanup(sensor_katcp_client)
            self.logger.error("No Sensors!!! Exiting!!!")
            raise

    def get_inputlabel(self, sensor_katcp_client):
        try:
            reply, informs = self.sensor_request(sensor_katcp_client, katcprequest="sensor-value",
                katcprequestArg="input-labelling",)
            assert reply.reply_ok()
            assert int(reply.arguments[-1])
            return [inform.arguments for inform in informs]
        except AssertionError:
            self.cleanup(sensor_katcp_client)
            self.logger.error("No Sensors!!! Exiting!!!")
            raise

    def get_sensor_dict(self, sensor_katcp_client, hostname_mapping, _host):
        """

        """
        try:
            sensor_value_informs = self.get_sensor_values(sensor_katcp_client)
            self.logger.debug("Converting sensor list to dict!!!")
            # # sensors name + status + value
            # self.original_sensors = dict((x[0], x[1:]) for x in [i[2:] for i in sensor_value_informs])
            # sensors name and status
            simplified_sensors = dict((x[0], x[1]) for x in [i[2:] for i in sensor_value_informs])
            ordered_sensor_dict = OrderedDict(sorted(simplified_sensors.items()))
        except Exception as exc:
            self.logger.exception("Failed to get sensors from katcp")
            raise exc
        else:
            mapping = []
            for key, value in ordered_sensor_dict.iteritems():
                key_s = key.split(".")
                host = key_s[0].lower()
                if host.startswith(_host) and ("device-status" in key_s):
                    new_value = [x.replace("device-status", value) for x in key_s[1:]]
                    if "network-reorder" in new_value:
                        # rename such that, it fits on a 1920x1080 html page as a button
                        _indices = new_value.index("network-reorder")
                        new_value[_indices] = new_value[_indices].replace(
                            "network-reorder", "Net-ReOrd")
                    if "missing-pkts" in new_value:
                        # rename such that, it fits on html/button
                        _indices = new_value.index("missing-pkts")
                        new_value[_indices] = new_value[_indices].replace(
                            "missing-pkts", "hmcReOrd")
                    if "bram-reorder" in new_value:
                        # rename such that, it fits on html/button
                        _indices = new_value.index("bram-reorder")
                        new_value[_indices] = new_value[_indices].replace(
                            "bram-reorder", "bramReOrd")

                    new_dict = dict(izip_longest(*[iter([host, new_value])] * 2, fillvalue=""))
                    mapping.append(new_dict)

            new_mapping = combined_Dict_List(*mapping)
            for host, _list in new_mapping.iteritems():
                if host in hostname_mapping:
                    new_hostname = host.replace(_host, "") + \
                    hostname_mapping[host].replace("skarab", "-").replace("-01", "")
                _ = [value.insert(0, new_hostname) for value in _list if len(value) == 1]

            try:
                assert isinstance(new_mapping, dict)
                return new_mapping
            except AssertionError:
                self.logger.exception("Failed to map the sensors with input labels and hostnames")
                raise

    ################################################################################################

    def create_mapping(self, input_mapping, hostname_mapping):
        """
        Create a simplified mapping between input labels and host-names
        Params
        ======
        input_mapping: list
            List of input labels
        hostname_mapping: list
            List of input hostnames
        """
        self.logger.debug("Mapping input labels and host names")
        import IPython; globals().update(locals()); IPython.embed(header='Python Debugger')
        update_maps = []
        for _input in input_mapping.values():
            if "_y" in _input:
                _input = _input.replace("_y", "_xy")
            elif "_x" in _input:
                _input = _input.replace("_x", "_xy")
            elif "v" in _input:
                _input = _input.replace("v", "_hv")
            elif "h" in _input:
                _input = _input.replace("h", "_hv")
            update_maps.append(_input)

        update_maps = sorted(update_maps)
        input_mapping = dict(zip(sorted(input_mapping.keys()), update_maps))
        hostname_mapping = dict((v, k) for k, v in hostname_mapping.iteritems())
        return [input_mapping, hostname_mapping]


    def map_xhost_sensors(self):
        """
        Needs to be in this format:
            'host03': [
                    ['03-020308', 'warn'],
                    ['network', 'warn'],
                    ['spead-rx', 'nominal'],
                    ['Net-ReOrd', 'nominal'],
                    ['hmcReOrd', 'warn'],
                    ['bram-reorder', 'error'],
                    ['vacc', 'error'],
                    ['spead-tx', 'nominal']
                ]
            }

        """
        xhost_sig_chain = [
            "-02",
            "network",
            "spead-rx",
            "Net-ReOrd",
            "hmcReOrd",
            "bramReOrd",
            "vacc",
            "spead-tx",
        ]
        new_mapping = self.get_sensor_dict(sec_sensors_katcp_con, self.hostname_mapping, "xhost")
        new_dict_mapping = {}
        for keys, values in new_mapping.iteritems():
            keys_ = keys[1:]
            new_dict_mapping[keys_] = []
            for value in values:
                if (len(value) <= 2) and (not value[0].startswith("xeng")):
                    new_dict_mapping[keys_].append(value)
                if (value[0].startswith("xeng") and value not in new_dict_mapping.values()):
                    if "vacc" in value:
                        new_dict_mapping[keys_].append(value[1:])
                    if "spead-tx" in value:
                        new_dict_mapping[keys_].append(value[1:])
                    if "bramReOrd" in value:
                        new_dict_mapping[keys_].append(value[1:])

        # _ = [listA.insert(_index, listA.pop(get_list_index(_sig, listA)))
        #      for _, listA in new_dict_mapping.iteritems() for _index, _sig in enumerate(xhost_sig_chain)]
        # return new_dict_mapping
        fixed_dict_mapping = {}
        for host_, listA in new_dict_mapping.iteritems():
            listA = listA[: len(xhost_sig_chain)]
            for _index, _sig in enumerate(xhost_sig_chain):
                listA.insert(_index, listA.pop(get_list_index(_sig, listA)))
            fixed_dict_mapping[host_] = listA
        return fixed_dict_mapping

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

        # Abbreviated signal chain
        # F_LRU -> Host -> input_label -> network-trx -> spead-rx -> network-reorder -> cd -> pfb -->>
        #    -->> ct -> spead-tx -> network-trx : [To Xengine ]
        # issue reading cmc3 input labels
        # fhost_sig_chain = ['SKA', 'fhost', 'network', 'spead-rx', 'Net-ReOrd', 'cd', 'pfb',
        fhost_sig_chain = [
            "-02",
            "input",
            "network",
            "spead-rx",
            "Net-ReOrd",
            "cd",
            "pfb",
            "ct",
            "spead-tx",
        ]
        try:
            import IPython; globals().update(locals()); IPython.embed(header='Python Debugger')
            new_mapping = self.new_mapping("fhost")
            assert isinstance(new_mapping, dict)
        except Exception:
            self.logger.error("Failed to map fhosts", exc_info=True)
        else:
            for host, values in new_mapping.iteritems():
                if host in self.hostname_mapping:
                    values.insert(2, [self.input_mapping[self.hostname_mapping[host]], "inputlabel"])
                    # values.append(['->XEngine', 'xhost'])

            new_dict_mapping = {}
            for host, values in new_mapping.iteritems():
                host_ = host[1:]
                new_dict_mapping[host_] = values
            # Update mappings
            _ = [listA.insert(_index, listA.pop(get_list_index(_sig, listA)))
                    for _, listA in new_dict_mapping.iteritems()
                        for _index, _sig in enumerate(fhost_sig_chain)
                ]

            return new_dict_mapping

    @property
    def get_original_mapped_sensors(self):
        mapping = []
        for key, value in self.original_sensors.iteritems():
            host = key.split(".")[0].lower()
            if host[1:].startswith("host"):
                if value[0] != "nominal":
                    value.insert(0, key)
                    new_dict = dict(izip_longest(*[iter([host, value])] * 2, fillvalue=""))
                    mapping.append(new_dict)

        new_mapping = combined_Dict_List(*mapping)
        return new_mapping

    def create_dumps_dir(self):
        """
        Create json dumps directory
        """
        # Conflicted: To store in /tmp or not to store in , that is the question
        try:
            _dir, _name = os.path.split(os.path.dirname(os.path.realpath(__file__)))
        except Exception:
            _dir, _name = os.path.split(os.path.dirname(os.path.realpath(__name__)))
        path = _dir + "/json_dumps"
        if not os.path.exists(path):
            self.logger.info("Created %s for storing json dumps." % path)
            os.makedirs(path)

    def generate_sensors_to_file(self):
        try:
            sensors = merge_dicts(self.map_fhost_sensors, self.map_xhost_sensors)
        except Exception:
            self.logger.error("Failed to map the host sensors", exc_info=True)
            raise
        else:
            self.create_dumps_dir()
            try:
                cur_path = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
            except Exception:
                cur_path = os.path.split(os.path.dirname(os.path.abspath(__name__)))[0]
            else:
                _filename = "{}/json_dumps/{}.{}.sensor_values.json".format(
                    cur_path, self.hostname, self.array_name)
                _sensor_filename = "{}/json_dumps/{}.{}.ordered_sensor_values.json".format(
                    cur_path, self.hostname, self.array_name)
                self.logger.info("Updating file: %s" % _filename)
                with open(_filename, "w") as outfile:
                    json.dump(sensors, outfile, indent=4, sort_keys=True)
                with open(_sensor_filename, "w") as outfile:
                    json.dump(
                        self.get_original_mapped_sensors,
                        outfile,
                        indent=4,
                        sort_keys=True,
                    )
                self.logger.info("Updated: %s" % _filename)


if __name__ == "__main__":
    import logging
    import coloredlogs
    parser = argparse.ArgumentParser(description="Receive data from a CBF and play.")
    parser.add_argument(
        "--katcp",
        dest="katcp_con",
        action="store",
        default="10.103.254.6:7147",
        help="IP:Port primary interface [Default: 10.103.254.6:7147]",
    )
    parser.add_argument(
        "--poll-time",
        dest="poll",
        action="store",
        default=10,
        type=int,
        help="Poll the sensors every x seconds [Default: 10]",
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
    pp = PrettyPrinter(indent=4)
    log_level = None
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : %(lineno)d - %(message)s"
    if args.get("log_level", "INFO"):
        log_level = args.get("log_level", "INFO").upper()
        try:
            logging.basicConfig(level=getattr(logging, log_level), format=log_format)
        except AttributeError:
            raise RuntimeError("No such log level: %s" % log_level)
        else:
            if log_level == "DEBUG":
                coloredlogs.install(level=log_level, fmt=log_format)
            else:
                coloredlogs.install(level=log_level)

    if args.get("katcp_con"):
        katcp_ip, katcp_port = args.get("katcp_con").split(":")

    sensor_poll = SensorPoll(katcp_ip, katcp_port)
    main_logger = LoggingClass()
    try:
        poll_time = args.get("poll")
        main_logger.logger.info("Begin sensor polling every %s seconds!!!" % poll_time)
        while True:
            sensor_poll.generate_sensors_to_file()
            main_logger.logger.debug("Updating sensor on dashboard!!!")
            main_logger.logger.info("---------------------RELOADING SENSORS---------------------")
            time.sleep(poll_time)
    except Exception:
        main_logger.logger.error("Error occurred now breaking...")
