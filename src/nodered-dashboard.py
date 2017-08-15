import context  # Ensures paho is in PYTHONPATH
import fire
import katcp
import logging
import paho.mqtt.publish as publish
import re
import time
from jenkinsapi.jenkins import Jenkins
from concurrent.futures import ThreadPoolExecutor

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


class JenkinsStatus(object):

    def __init__(self, host_ip='127.0.0.1', username=None, password=None, job=None):
        self.host_ip = host_ip
        self.username = username
        self.password = password
        self.job = job
        self.jenkinsAPI = Jenkins('http://%s:8080'%self.host_ip, username=self.username,
            password=self.password)

    @property
    def get_lastbuild_status(self):
        if self.jenkinsAPI.has_job(self.job):
            job = self.jenkinsAPI.get_job(self.job)
            last_build = job.get_last_build()
            return last_build.get_status()

    @property
    def job_running(self):
        if self.jenkinsAPI.has_job(self.job):
            job = self.jenkinsAPI.get_job(self.job)
            job_status = job.is_running()
            return 'Running' if job_status is True else 'Not Running'

    @property
    def build_job(self):
        if self.jenkinsAPI.has_job(self.job):
            return self.jenkinsAPI.build_job(self.job)



class NoderedFeeds(object):
    def __init__(self, username, password, job_name='CBF_Activate_BC8N856M4K(lab)'):
        '''
        Jenkins API credentials for retrieving information of builds

        username: str
            Username used when accessing Jenkins
        password : str
            Password used when accessing Jenkins
        job_name : str
            Jenkins job to be built
        run-feeds: function
            Function that uploads instrument sensor-values to node-red dashboard running on
            _host_ip(default: 192.168.4.23)

        Usage:
            python nodered-dashboard.py --username admin --password pass --job-name RunTests run-feeds
        '''
        self.username = username
        self.password = password
        self.job_name = job_name


    def run_feeds(self, _verbose=None, _host_ip='192.168.4.23', _katcp_ip='localhost', _katcp_port=7147,
              _timeout=10, _delay_poll=30):
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
        _delay_poll: int
            sensor polling delay
        '''

        if _verbose in ['verbose', '--verbose', '-v']:
            print _verbose
            logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : '
                       '%(lineno)d - %(message)s')
            logging.debug('DEBUG MODE ENABLED')
        else:
            logging.basicConfig(level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : '
                       '%(lineno)d - %(message)s')
        logging.info('______Feed updater running.______')

        if self.username and self.password:
            self.job_status = JenkinsStatus(host_ip=_host_ip, username=self.username, password=self.password,
                job=self.job_name)

        def sensor_polling(self):

            def upload_feeds(topic, values, hostip, _delay=0.2):
                logging.debug('Publishing current time:%s to %s'%(time.ctime(), hostip))
                publish.single('CurrentTime', time.ctime(), hostname=hostip)
                publish.single(topic, values, hostname=hostip)
                logging.debug('Publishing %s on topic %s to %s'%(values, topic, hostip))
                time.sleep(_delay)

            while True:
                try:
                    assert type(self.username and self.password) is str
                    upload_feeds('jenkins/job', self.job_status.job, _host_ip)
                    upload_feeds('jenkins/job_running', self.job_status.job_running, _host_ip)
                    upload_feeds('jenkins/last_build',
                        self.job_status.get_lastbuild_status.capitalize(), _host_ip)
                except Exception:
                    upload_feeds('jenkins/last_build', 'Failure', _host_ip)

                try:
                    logging.info('Starting katcp connection on %s:%s'%(_katcp_ip, _katcp_port))
                    kcp_client = katcp.BlockingClient(_katcp_ip, _katcp_port)
                    kcp_client.setDaemon(True)
                    kcp_client.start()
                    is_connected = kcp_client.wait_connected(_timeout)
                    logging.info('katcp connection established on %s:%s'%(_katcp_ip, _katcp_port))
                    if not is_connected:
                        kcp_client.stop()
                        raise RuntimeError('Could not connect to %s:%s, timed out.' %(_katcp_ip,
                            _katcp_port))
                    logging.info('Retrieving array port on %s:%s'%(_katcp_ip, _katcp_port))
                    reply, informs = kcp_client.blocking_request(katcp.Message.request('array-list'),
                        timeout=_timeout)
                    errmsg = 'Failed to issue array-list on %s:%s'%(_katcp_ip, _katcp_port)
                    assert reply.reply_ok(), errmsg
                    kcp_client.stop()
                except Exception as e:
                    logging.error(errmsg)
                    logging.exception(str(e))
                    time.sleep(_delay_poll)
                else:
                    try:
                        _array_port = int(informs[0].arguments[1])
                        _array_name = str(informs[0].arguments[0])
                        logging.info('subarray katcp connection established on %s:%s'%(_katcp_ip,
                            _array_name))
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
                        logging.info('Subarray katcp connection established on %s:%s'%(_katcp_ip,
                            _katcp_port))
                        if not is_connected:
                            kcp_client.stop()
                            raise RuntimeError('Could not connect to %s:%s, timed out.' %(_katcp_ip,
                                _array_port))
                        logging.info('Retrieving sensor values on subarray  on %s:%s'%(_katcp_ip,
                            _katcp_port))
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
                        time.sleep(_delay_poll)
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

                        inputs_append = []
                        count = 0
                        for _sensor, _value in sensors.iteritems():
                            if re.search('-', _sensor):
                                topic = ''.join(['sensor_values/', _sensor.replace('-', '_')])
                            else:
                                topic = ''.join(['sensor_values/', _sensor])

                            if _sensor in ['hostname-functional-mapping' , 'input-labelling']:
                                __value = eval(_value)
                                inputs_append.append(__value)
                                count += 1
                                if count == 2:
                                    count = 0
                                    _host_map, _input_labels = inputs_append
                                    for _roach, _xhost in _host_map.iteritems():
                                        if _xhost.startswith('xhost'):
                                            _value = ' - '.join([_xhost, _roach])
                                            _topic = '/'.join([topic, _xhost])
                                            upload_feeds(_topic, _value, _host_ip)
                                    for x in _input_labels:
                                        for i, v in _host_map.iteritems():
                                            if i in x:
                                                _value = ' - '.join([v, x[0],x[2]])
                                                _topic = '/fhost'.join([topic, str(x[1])])
                                                upload_feeds(_topic, _value, _host_ip)
                            else:
                                upload_feeds(topic, _value, _host_ip)

                time.sleep(_delay_poll)
                logging.info('Sleeping for %s to ease up the cpu'%_delay_poll)

        with ThreadPoolExecutor(max_workers=5) as executor:
            sensor_polling(self)



if __name__ == '__main__':
    fire.Fire(NoderedFeeds)
