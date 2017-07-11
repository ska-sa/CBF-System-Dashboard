import context  # Ensures paho is in PYTHONPATH
import fire
import katcp
import logging
import paho.mqtt.publish as publish
import re
import time

# logging = logging.getLogger(__name__)

# Katcp Sensors in question.
sensors_required = [
            'baseline-correlation-products-destination',
            'baseline-correlation-products-int-time',
            'baseline-correlation-products-n-accs',
            'baseline-correlation-products-n-bls',
            'baseline-correlation-products-n-chans',
            'hostname-functional-mapping',
            'input-labelling',
            'instrument-state',
            'n-ants',
            'n-feng-hosts',
            'n-xeng-hosts',
            'scale-factor-timestamp',
            'synchronisation-epoch',
            ]

class NoderedFeeds(object):
    ''' Upload instrument sensor-values to node-red dashboard running on _host_ip(default: 192.168.4.23)

    _verbose: str 'verbose/--verbose/-v'
        Increase verbosity to debug
    _host_ip : str
        Host IP where node-red is running/ where the data goes!
    _katcp_ip : str
        Host IP where array is running on
    _katcp_port : int
        Host port where array is running on
    _timeout: int
        Katcp connection timeout
    '''

    def feeds(self, _verbose=None, _host_ip='192.168.4.23', _katcp_ip='localhost', _katcp_port=7147, _timeout=10):
        '''
        Upload instrument sensor-values to node-red dashboard running on _host_ip(default: 192.168.4.23)
        _verbose: str 'verbose/--verbose/-v'
            Increase verbosity to debug
        _host_ip : str
            Host IP where node-red is running/ where the data goes!
        _katcp_ip : str
            Host IP where array is running on
        _katcp_port : int
            Host port where array is running on
        _timeout: int
            Katcp connection timeout
        '''

        if _verbose in ['verbose', '--verbose', '-v']:
            logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : '
                       '%(lineno)d - %(message)s')
            logging.debug('DEBUG MODE ENABLED')
        else:
            logging.basicConfig(level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : '
                       '%(lineno)d - %(message)s')
        logging.info('______Feed updater running.______')
        while True:
            try:
                logging.info('Starting katcp connection on %s:%s'%(_katcp_ip, _katcp_port))
                kcp_client = katcp.BlockingClient(_katcp_ip, _katcp_port)
                kcp_client.setDaemon(True)
                kcp_client.start()
                is_connected = kcp_client.wait_connected(_timeout)
                logging.info('katcp connection established on %s:%s'%(_katcp_ip, _katcp_port))
                if not is_connected:
                    kcp_client.stop()
                    raise RuntimeError('Could not connect to %s:%s, timed out.' %(_katcp_ip, _katcp_port))
                logging.info('Retrieving array port on %s:%s'%(_katcp_ip, _katcp_port))
                reply, informs = kcp_client.blocking_request(katcp.Message.request('array-list'),
                    timeout=_timeout)
                errmsg = 'Failed to issue array-list on %s:%s'%(_katcp_ip, _katcp_port)
                assert reply.reply_ok(), errmsg
                kcp_client.stop()
            except Exception as e:
                logging.error(errmsg)
                logging.exception(str(e))
            else:
                try:
                    _array_port = int(informs[0].arguments[1])
                    _array_name = str(informs[0].arguments[0])
                    logging.info('subarray katcp connection established on %s:%s'%(_katcp_ip, _array_name))
                    kcp_client = katcp.BlockingClient(_katcp_ip, _array_port)
                    publish.single('instrument/array_port', _array_port , hostname=_host_ip)
                    logging.debug('Publishing %s to %s'%(_array_port, _host_ip))
                    publish.single('instrument/array_name', _array_name, hostname=_host_ip)
                    logging.debug('Publishing %s to %s'%(_array_name, _host_ip))
                    publish.single('instrument/katcp_ip', _host_ip, hostname=_host_ip)
                    logging.debug('Publishing %s to %s'%(_host_ip, _host_ip))
                    kcp_client.setDaemon(True)
                    kcp_client.start()

                    is_connected = kcp_client.wait_connected(_timeout)
                    logging.info('Subarray katcp connection established on %s:%s'%(_katcp_ip, _katcp_port))
                    if not is_connected:
                        kcp_client.stop()
                        raise RuntimeError('Could not connect to %s:%s, timed out.' %(_katcp_ip,
                            _array_port))
                    logging.info('Retrieving sensor values on subarray  on %s:%s'%(_katcp_ip, _katcp_port))
                    reply, informs = kcp_client.blocking_request(katcp.Message.request('sensor-value'),
                        timeout=_timeout)
                    errmsg = 'Failed to issue sensor-value on %s:%s'%(_katcp_ip, _array_port)
                    assert reply.reply_ok(), errmsg
                    kcp_client.stop()
                    f_hosts = [int(i.arguments[-1]) for i in informs if i.arguments[2] == 'n-feng-hosts'][0]
                    x_hosts = [int(i.arguments[-1]) for i in informs if i.arguments[2] == 'n-xeng-hosts'][0]
                except Exception as e:
                    logging.error(errmsg)
                    logging.exception(str(e))
                else:
                    hosts_sensors = []
                    for i in range(f_hosts):
                        hosts_sensors.append(''.join(['fhost', str(i), '-network-tx-ok']))
                        hosts_sensors.append(''.join(['fhost', str(i), '-phy-ok']))
                        hosts_sensors.append(''.join(['fhost', str(i), '-qdr-ok']))
                        hosts_sensors.append(''.join(['fhost', str(i), '-reorder-ok']))
                        hosts_sensors.append(''.join(['fhost', str(i),'-lru-ok']))
                        hosts_sensors.append(''.join(['fhost', str(i),'-network-rx-ok']))
                        hosts_sensors.append(''.join(['fhost', str(i),'-pfb-ok']))
                    for i in range(x_hosts):
                        hosts_sensors.append(''.join(['xhost', str(i), '-lru-ok']))
                        hosts_sensors.append(''.join(['xhost', str(i), '-network-rx-ok']))
                        hosts_sensors.append(''.join(['xhost', str(i), '-network-tx-ok']))
                        hosts_sensors.append(''.join(['xhost', str(i), '-phy-ok']))
                        hosts_sensors.append(''.join(['xhost', str(i), '-qdr-ok']))
                        hosts_sensors.append(''.join(['xhost', str(i), '-reorder-ok']))

                    sensors_required.extend(hosts_sensors)
                    sensors = {}
                    srch = re.compile('|'.join(sensors_required))
                    srch_ = re.compile('|'.join(hosts_sensors))
                    for inf in informs:
                        if srch.match(inf.arguments[2]):
                            sensors[inf.arguments[2]] = inf.arguments[4]
                        if srch_.match(inf.arguments[2]):
                            sensors[inf.arguments[2]] = inf.arguments[3]
                    for _sensor, _value in sensors.iteritems():
                        publish.single('CurrentTime', time.ctime(), hostname=_host_ip)
                        logging.debug('Publishing current time:%s to %s'%(time.ctime(), _host_ip))
                        topic = ''.join(['sensor_values/', _sensor.replace('-', '_')])
                        publish.single(topic, _value, hostname=_host_ip)
                        logging.debug('Publishing %s on topic %s to %s'%(_value,topic, _host_ip))

            time.sleep(10)


if __name__ == '__main__':
    fire.Fire(NoderedFeeds)
