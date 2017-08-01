from jenkinsapi.jenkins import Jenkins


job_name = 'CBF_Activate_BC8N856M4K(lab)'
username = ''
password = ''

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
            return job.is_running()

    @property
    def build_job(self):
        if self.jenkinsAPI.has_job(self.job):
            return self.jenkinsAPI.build_job(self.job)


Jobs_status = JenkinsStatus(username=username, password=password, job=job_name)