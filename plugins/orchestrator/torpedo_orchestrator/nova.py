import random
import string

from base import Base
from logger_agent import logger
from openstack import Openstack


class Nova(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)
        self.hostname = ""

    def get(self):
        (tc_status, message) = self.gc.GET(self.url, self.headers,
                                           data=self.data)
        return tc_status, message, self.tc

    def create_vm(self):
        random_string = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(6))
        flavor_id = self.gc.get_flavor_id(self.url, self.headers,
                                          name=self.tc['flavor'])
        image_id = self.gc.get_image_id(self.headers)
        network = self.gc.get_network_id(self.headers, self.tc['private_network'])
        self.tc['data'] = {
            'server': {
                "name": "resiliency_vm_{}".format(random_string),
                "imageRef": image_id,
                "flavorRef": flavor_id,
                "networks": [{ "uuid": network }]
                }
        }
        response = self.gc.POST(self.url, self.headers, data=self.tc['data'])
        if response.status_code >= 200 and response.status_code < 400:
            tc_status = "PASS"
            message = "Stripped not printing"
            vm_id = response.json()['server']['id']
            url = self.url + '/' + vm_id
            result = self.gc.check_resource_status(url, self.headers)
            logger.info("Waiting for %s vm to come to active state" % (vm_id))
            if result.status_code >= 200 and result.status_code < 400:
                while result.json()['server']['status'].lower() != 'active':
                    if result.json()['server']['status'].lower() == 'error':
                        tc_status = 'FAIL'
                        message = 'stripped not printing'
                        break
                    result = self.gc.check_resource_status(url, self.headers)
            if tc_status == "PASS":
                hostname = result.json()['server']['OS-EXT-SRV-ATTR:host']
        else:
            tc_status = "FAIL"
            message = result.text
            vm_id = ""
            hostname = ""
        return tc_status, message, vm_id, hostname

    def delete_vm(self, vm_id):

        logger.info('Deleting the created instance: {}'.format(
                vm_id))
        delete_url = "{}/{}".format(self.url, vm_id)
        result = self.gc.DELETE(delete_url, self.headers)
        if result.status_code >= 200 and result.status_code < 400:
            tc_status = 'PASS'
            message = 'stripped not printing'
        else:
            tc_status = 'FAIL'
            message = result.text
        logger.info('Instance Deleted')
        return tc_status, message

    def post(self):

        tc_status, message, vm_id, hostname = self.create_vm()
        if vm_id:
            tc_status, message = self.delete_vm(vm_id)
        return tc_status, message, self.tc
