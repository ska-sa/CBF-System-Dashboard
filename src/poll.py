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

# For Debugging
# logging.getLogger('katcp').setLevel('DEBUG')

_cleanups = []
"""Callables that will be called in reverse order at package teardown. Stored as a tuples of (callable,
args, kwargs)
"""

# Global katcp timeout
_timeout = 60


def add_cleanup(_fn, *args, **kwargs):
    _cleanups.append((_fn, args, kwargs))


def teardown_package():
    """
    nose allows tests to be grouped into test packages. This allows package-level setup; for instance,
    if you need to create a test database or other data fixture for your tests, you may create it in
    package setup and remove it in package teardown once per test run, rather than having to create and
    tear it down once per test module or test case.
    To create package-level setup and teardown methods, define setup and/or teardown functions in the
    __init__.py of a test package. Setup methods may be named setup, setup_package, setUp, or
    setUpPackage; teardown may be named teardown, teardown_package, tearDown or tearDownPackage.
    Execution of tests in a test package begins as soon as the first test module is loaded from the
    test package.

    ref:https://nose.readthedocs.io/en/latest/writing_tests.html?highlight=setup_package#test-packages
    """
    while _cleanups:
        _fn, args, kwargs = _cleanups.pop()
        try:
            _fn(*args, **kwargs)
        except BaseException:
            raise NotImplementedError

class SensorPoll(object):
    def __init__(self, katcp_client="127.0.0.1:7147", array_name='array0'):
        self.katcp_client_ip, self.katcp_client_port = katcp_client.split(":")
        self.array_name = array_name
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
            add_cleanup(self.io_manager.stop)
            self.io_wrapper.default_timeout = _timeout
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
            add_cleanup(self._rct.stop)
            try:
                self._rct.until_synced(timeout=_timeout)
            except TimeoutError:
                self._rct.stop()
        return self._rct

    # @property
    # def katcp_rct(self):
    #     if self._katcp_rct is None:
    #         try:
    #             katcp_prot = self.test_config["instrument_params"]["katcp_protocol"]
    #             _major, _minor, _flags = katcp_prot.split(",")
    #             protocol_flags = ProtocolFlags(int(_major), int(_minor), _flags)
    #             LOGGER.info("katcp protocol flags %s" % protocol_flags)

    #             LOGGER.info("Getting running array.")
    #             reply, informs = self.rct.req.subordinate_list(self.array_name)
    #             assert reply.reply_ok()
    #             # If no sub-array present create one, but this could cause problems
    #             # if more than one sub-array is present. Update this to check for
    #             # required sub-array.
    #         except Exception:
    #             LOGGER.exception("Failed to list all arrays with name: %s" % self.array_name)
    #         else:
    #             try:
    #                 try:
    #                     self.katcp_array_port = int(informs[0].arguments[1])
    #                     LOGGER.info(
    #                         "Current running array name: %s, port: %s"
    #                         % (self.array_name, self.katcp_array_port)
    #                     )
    #                 except ValueError:
    #                     self.katcp_array_port, self.katcp_sensor_port = (
    #                         informs[0].arguments[1].split(",")
    #                     )
    #                     LOGGER.info(
    #                         "Current running array name: %s, port: %s, sensor port: %s"
    #                         % (self.array_name, self.katcp_array_port, self.katcp_sensor_port)
    #                     )
    #             except Exception:
    #                 errmsg = (
    #                     "Failed to retrieve running array, ensure one has been created and running"
    #                 )
    #                 LOGGER.exception(errmsg)
    #                 sys.exit(errmsg)
    #             else:
    #                 katcp_rc = resource_client.KATCPClientResource(
    #                     dict(
    #                         name="{}".format(self.katcp_client),
    #                         address=(
    #                             "{}".format(self.katcp_client),
    #                             "{}".format(self.katcp_array_port),
    #                         ),
    #                         preset_protocol_flags=protocol_flags,
    #                         controlled=True,
    #                     )
    #                 )
    #                 katcp_rc.set_ioloop(self.io_manager.get_ioloop())
    #                 self._katcp_rct = resource_client.ThreadSafeKATCPClientResourceWrapper(
    #                     katcp_rc, self.io_wrapper
    #                 )
    #                 self._katcp_rct.start()
    #                 try:
    #                     self._katcp_rct.until_synced(timeout=_timeout)
    #                 except Exception as e:
    #                     self._katcp_rct.stop()
    #                     LOGGER.exception("Failed to connect to katcp due to %s" % str(e))
    #                 else:
    #                     return self._katcp_rct
    #     else:
    #         if not self._katcp_rct.is_active():
    #             LOGGER.info("katcp resource client wasnt running, hence we need to start it.")
    #             self._katcp_rct.start()
    #             try:
    #                 time.sleep(1)
    #                 self._katcp_rct.until_synced(timeout=_timeout)
    #                 return self._katcp_rct
    #             except Exception:
    #                 self._katcp_rct.stop()
    #                 LOGGER.exception("Failed to connect to katcp")
    #         else:
    #             return self._katcp_rct

    @property
    def katcp_rct_sensor(self):
        if self._katcp_rct_sensor is None:
            try:
                katcp_prot = "5,0,M"
                _major, _minor, _flags = katcp_prot.split(",")
                protocol_flags = ProtocolFlags(int(_major), int(_minor), _flags)
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
                try:
                    self._katcp_rct_sensor.until_synced(timeout=_timeout)
                except Exception:
                    self._katcp_rct_sensor.stop()
                else:
                    return self._katcp_rct_sensor
        else:
            if not self._katcp_rct_sensor.is_active():
                self._katcp_rct_sensor.start()
                try:
                    time.sleep(1)
                    self._katcp_rct_sensor.until_synced(timeout=_timeout)
                    return self._katcp_rct_sensor
                except Exception:
                    self._katcp_rct_sensor.stop()
            else:
                return self._katcp_rct_sensor

    def get_sensors(self):
        try:
            assert hasattr(self.katcp_rct_sensor, 'req')
            reply, informs = self.katcp_rct_sensor.req.sensor_value()
            assert reply.reply_ok()
        except Exception:
            raise NotImplementedError('Not Implemented')
        else:
            return informs


if __name__ == '__main__':
    sensors = SensorPoll()
    import IPython; globals().update(locals()); IPython.embed(header='Python Debugger')