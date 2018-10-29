import logging
import os
import sys
import time
import katcp
import argcomplete
import argparse
import atexit
import coloredlogs
import functools
import gc
import json
import katcp
import logging
import os
import sys
import time

from collections import OrderedDict
from itertools import izip_longest
from pprint import PrettyPrinter

from concurrent.futures import TimeoutError

from katcp import ioloop_manager, resource_client
from katcp.core import ProtocolFlags
from katcp.resource_client import KATCPSensorError

class SensorPoll(object):
    def __init__(self, katcp_client="127.0.0.1:7147", array_name='array0', timeout=30):
        self.katcp_client_ip, self.katcp_client_port = katcp_client.split(":")
        self.array_name = array_name
        self._timeout = timeout
        self._katcp_rct = None
        self._katcp_rct_sensor = None
        self._rct = None

    @property
    def rct(self):
        if self._rct is not None:
            return self._rct
        else:
            self.io_manager = ioloop_manager.IOLoopManager()
            self.io_wrapper = resource_client.IOLoopThreadWrapper(self.io_manager.get_ioloop())
            atexit.register(self.io_manager.stop)
            self.io_wrapper.default_timeout = self._timeout
            self.io_manager.start()
            self.rc = resource_client.KATCPClientResource(
                dict(
                    name="{}".format(self.katcp_client_ip),
                    address=("{}".format(self.katcp_client_ip), self.katcp_client_port),
                    controlled=True,
                )
            )
            self.rc.set_ioloop(self.io_manager.get_ioloop())
            self._rct = resource_client.ThreadSafeKATCPClientResourceWrapper(
                self.rc, self.io_wrapper)
            self._rct.start()
            atexit.register(self._rct.stop)
            try:
                self._rct.until_synced(timeout=self._timeout)
            except Exception:
                self._rct.stop()
                # self._rct.join()
        return self._rct


    @property
    def katcp_rct_sensor(self):
        if self._katcp_rct_sensor is None:
            try:
                katcp_prot = "5,0,M"
                _major, _minor, _flags = katcp_prot.split(",")
                protocol_flags = ProtocolFlags(int(_major), int(_minor), _flags)
                assert hasattr(self.rct, 'req')
                assert hasattr(self.rct.req, 'array_list')
                reply, informs = self.rct.req.array_list(self.array_name)
                assert reply.reply_ok()
                assert informs[0].arguments > 1
                self.katcp_array_port, self.katcp_sensor_port = ([
                    int(i) for i in informs[0].arguments[1].split(",")
                    ])
            except Exception:
                raise NotImplementedError
            else:
                katcp_rc = resource_client.KATCPClientResource(
                    dict(
                        name="{}".format(self.katcp_client_ip),
                        address=(
                            "{}".format(self.katcp_client_ip),
                            "{}".format(self.katcp_sensor_port),
                            ),
                        preset_protocol_flags=protocol_flags,
                        controlled=True,
                        )
                    )
                katcp_rc.set_ioloop(self.io_manager.get_ioloop())
                self._katcp_rct_sensor = resource_client.ThreadSafeKATCPClientResourceWrapper(
                    katcp_rc, self.io_wrapper)

                self._katcp_rct_sensor.start()
                atexit.register(self._katcp_rct_sensor.start)
                try:
                    self._katcp_rct_sensor.until_synced(timeout=self._timeout)
                except Exception:
                    self._katcp_rct_sensor.stop()
                    self._katcp_rct_sensor.join()
                else:
                    return self._katcp_rct_sensor
        else:
            print "Well sensor resource_client is not None"

            # import IPython; globals().update(locals()); IPython.embed(header='Python Debugger')
            if not self._katcp_rct_sensor.is_active():
                self._katcp_rct_sensor.start()
                print "weirdness"
                try:
                    time.sleep(1)
                    self._katcp_rct_sensor.until_synced(timeout=self._timeout)
                    return self._katcp_rct_sensor
                except Exception:
                    self._katcp_rct_sensor.stop()
                    # self._katcp_rct_sensor.join()
            else:
                print 'is active'
                try:
                    assert hasattr(self._katcp_rct_sensor, "req"), 'sensors rct not running'
                    assert hasattr(self._katcp_rct_sensor.req, "sensor_value"), 'no sensors on sensors rct'
                    return self._katcp_rct_sensor
                except AssertionError:
                    print 'AssertionError(" error")'
                    del self._katcp_rct_sensor
                    self._katcp_rct_sensor = None
                    return self._katcp_rct_sensor


    def get_sensors(self):
        try:
            assert hasattr(self.katcp_rct_sensor, 'req')
            assert hasattr(self.katcp_rct_sensor.req, 'sensor_value')
            reply, informs = self.katcp_rct_sensor.req.sensor_value()
            assert reply.reply_ok()
        except Exception:
            raise NotImplementedError('Not Implemented')
        else:
            return informs


if __name__ == '__main__':
    sensors = SensorPoll()
    # import IPython; globals().update(locals()); IPython.embed(header='Python Debugger')
    while True:
        print ("Waiting")
        print (sensors.get_sensors())
        time.sleep(5)