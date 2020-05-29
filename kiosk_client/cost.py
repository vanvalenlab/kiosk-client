# Copyright 2016-2020 The Van Valen Lab at the California Institute of
# Technology (Caltech), with support from the Paul Allen Family Foundation,
# Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
# All rights reserved.
#
# Licensed under a modified Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.github.com/vanvalenlab/kiosk-client/LICENSE
#
# The Work provided may be used for non-commercial academic purposes only.
# For any other use of the Work, including commercial use, please contact:
# vanvalenlab@gmail.com
#
# Neither the name of Caltech nor the names of its contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Class to estimate costs using the grafana API"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import time
import urllib

import requests

from kiosk_client import settings


# defining Google Cloud prices

# computed networking costs for 1,000,000 image run:
NETWORKING_COSTS = 7.00

# current, as of 6/17/19
COST_TABLE = {
    'n1-standard-1': {'ondemand': 0.0475, 'preemptible': 0.0100},
    'n1-standard-2': {'ondemand': 0.0950, 'preemptible': 0.0200},
    'n1-standard-4': {'ondemand': 0.1900, 'preemptible': 0.0400},
    'n1-standard-8': {'ondemand': 0.3800, 'preemptible': 0.0800},
    'n1-standard-16': {'ondemand': 0.7600, 'preemptible': 0.1600},
    'n1-standard-32': {'ondemand': 1.5200, 'preemptible': 0.3200},
    'n1-standard-64': {'ondemand': 3.0400, 'preemptible': 0.6400},
    'n1-standard-96': {'ondemand': 4.5600, 'preemptible': 0.9600},
    'n1-highmem-2': {'ondemand': 0.1184, 'preemptible': 0.0250},
    'n1-highmem-4': {'ondemand': 0.2368, 'preemptible': 0.0500},
    'n1-highmem-8': {'ondemand': 0.4736, 'preemptible': 0.1000},
    'n1-highmem-16': {'ondemand': 0.9472, 'preemptible': 0.2000},
    'n1-highmem-32': {'ondemand': 1.8944, 'preemptible': 0.4000},
    'n1-highmem-64': {'ondemand': 3.7888, 'preemptible': 0.8000},
    'n1-highmem-96': {'ondemand': 5.6832, 'preemptible': 1.2000},
    'n1-highcpu-2': {'ondemand': 0.0709, 'preemptible': 0.0150},
    'n1-highcpu-4': {'ondemand': 0.1418, 'preemptible': 0.0300},
    'n1-highcpu-8': {'ondemand': 0.2836, 'preemptible': 0.0600},
    'n1-highcpu-16': {'ondemand': 0.5672, 'preemptible': 0.1200},
    'n1-highcpu-32': {'ondemand': 1.1344, 'preemptible': 0.2400},
    'n1-highcpu-64': {'ondemand': 2.2688, 'preemptible': 0.4800},
    'n1-highcpu-96': {'ondemand': 3.4020, 'preemptible': 0.7200},
    'n1-ultramem-40': {'ondemand': 6.3039, 'preemptible': 1.3311},
    'n1-ultramem-80': {'ondemand': 12.6078, 'preemptible': 2.6622},
    'n1-ultramem-160': {'ondemand': 25.2156, 'preemptible': 5.3244},
    'n1-megamem-96': {'ondemand': 10.6740, 'preemptible': 2.2600},
}

GPU_TABLE = {
    'nvidia-tesla-t4': {'ondemand': 0.95, 'preemptible': 0.29},
    'nvidia-tesla-p4': {'ondemand': 0.60, 'preemptible': 0.216},
    'nvidia-tesla-v100': {'ondemand': 2.48, 'preemptible': 0.74},
    'nvidia-tesla-p100': {'ondemand': 1.46, 'preemptible': 0.43},
    'nvidia-tesla-k80': {'ondemand': 0.45, 'preemptible': 0.135},
}


class CostGetter(object):

    def __init__(self,
                 benchmarking_start_time=None,
                 benchmarking_end_time=None,
                 **kwargs):
        # validate benchmarking_start_time
        if benchmarking_start_time is None:
            benchmarking_start_time = self.get_time()

        try:
            benchmarking_start_time = int(benchmarking_start_time)
            assert benchmarking_start_time <= int(time.time())
        except AssertionError:
            raise ValueError('You need to provide either an integer '
                             'string (e.g., "12345") or a decimal or '
                             'integer number (e.g., 123.45) for '
                             'benchmarking_start_time.')

        if benchmarking_end_time is not None:
            try:
                benchmarking_end_time = int(benchmarking_end_time)
                assert benchmarking_start_time <= benchmarking_end_time
            except AssertionError:
                raise ValueError('You need to provide either an integer '
                                 'string (e.g., "12345") or a decimal or '
                                 'integer number (e.g., 123.45) for '
                                 'benchmarking_end_time.')

        self.benchmarking_start_time = benchmarking_start_time
        self.benchmarking_end_time = benchmarking_end_time

        # initialize other necessary variables
        self.min_step = 15
        self.cost_table = kwargs.get('cost_table', COST_TABLE)
        self.gpu_table = kwargs.get('gpu_table', GPU_TABLE)
        self.networking_costs = kwargs.get('networking_costs', NETWORKING_COSTS)

        self.grafana_user = settings.GRAFANA_USER
        self.grafana_password = settings.GRAFANA_PASSWORD
        self.grafana_host = settings.GRAFANA_HOST
        self.logger = logging.getLogger(str(self.__class__.__name__))

    @classmethod
    def get_time(cls):
        """Get current time in epoch seconds."""
        # Meant to be called at the beginning and end of a benchmarking run
        # to establish the beginning or end of cost accrual.
        return int(time.time())

    def get_query_data(self, query, step=None):
        """Return a payload of the given query for the Grafana API"""
        step = self.min_step if step is None else step
        return {
            'query': query,
            'start': self.benchmarking_start_time,
            'end': self.benchmarking_end_time,
            'step': step,
        }

    def get_url(self, data):
        """Return a formatted URL for the Grafana API"""
        # check python2 vs python3
        if hasattr(urllib, 'parse'):
            url_encode = urllib.parse.urlencode  # pylint: disable=E1101
        else:
            url_encode = urllib.urlencode  # pylint: disable=E1101
        return 'http://{user}:{passwd}@{host}{route}?{querystring}'.format(
            user=self.grafana_user,
            passwd=self.grafana_password,
            host=self.grafana_host,
            route='/api/datasources/proxy/1/api/v1/query_range',
            querystring=url_encode(data))

    def send_grafana_api_request(self, query, step=None):
        """Send a HTTP GET request with the data url encoded"""
        # initialize retry loop values
        status_code = None
        errortext = None
        is_first_req = True

        # error text found in requests that are too large. must increase step.
        retryable_errortext = 'exceeded maximum resolution'

        reqdata = self.get_query_data(query, step)

        status_is_400 = lambda x: x is None or x == 400
        retryable_error = lambda x: x is None or retryable_errortext in str(x)

        # if there are too many datapoints, a 400 error code is returned.
        # inspect the error text to confirm.
        while status_is_400(status_code) and retryable_error(errortext):
            # don't spam the API
            time.sleep(0.5 * int(not is_first_req))

            reqdata['step'] += self.min_step * int(not is_first_req)
            url = self.get_url(reqdata)

            response = requests.get(url)
            status_code = response.status_code

            jsondata = response.json()

            if status_code != 200:
                is_first_req = False  # starting to retry
                errortext = jsondata.get('error', '')
                self.logger.warning('%s request failed due to error: %s',
                                    query, errortext)

        return jsondata

    def finish(self):
        # This is the wrapper function for all the functionality
        # that will executed immediately once benchmarking is finished.
        if not self.benchmarking_end_time:
            self.benchmarking_end_time = self.get_time()

        creation_data = self.send_grafana_api_request('kube_node_created')
        label_data = self.send_grafana_api_request('kube_node_labels')

        parsed_creation_data = self.parse_create_response(creation_data)
        parsed_label_data = self.parse_label_response(label_data)

        # merge the dictionaries
        node_data = parsed_creation_data.copy()
        for node_name in parsed_label_data:
            if node_name in node_data:
                for k in parsed_label_data[node_name]:
                    node_data[node_name][k] = parsed_label_data[node_name][k]

        (cpu_node_costs, gpu_node_costs, total_node_costs) = \
            self.compute_costs(node_data)
        total_costs = total_node_costs + self.networking_costs
        return str(cpu_node_costs), str(gpu_node_costs), str(total_costs)

    def parse_create_response(self, response):
        node_info = {}
        # parse node liveness data
        for time_series in response['data']['result']:
            # get node name and create dictionary entry
            node_name = time_series['metric']['node']
            node_info[node_name] = {}
            # get node lifetime
            # Was there only one creation event?
            first_event = time_series['values'][0]
            last_event = time_series['values'][-1]

            if first_event[-1] == last_event[-1]:
                # they're the same! easy to calculate
                created_at = int(last_event[-1])
                # only count costs during the benchmarking window.
                created_at = max(created_at, self.benchmarking_start_time)
                node_info[node_name]['lifetime'] = last_event[0] - created_at
                continue

            # there was more than one creation event :(
            # loop over list backward to find the final event for each creation
            lifetime = 0
            curr_label = None
            for i in range(len(time_series['values']) - 1, 0, -1):
                ts, created_at = time_series['values'][i]
                created_at = int(created_at)
                if created_at != curr_label:  # a new label.
                    curr_label = created_at
                    created_at = max(created_at, self.benchmarking_start_time)
                    lifetime += ts - created_at

            node_info[node_name]['lifetime'] = lifetime
        return node_info

    def parse_label_response(self, response):
        node_info = {}
        # parse node label data
        for label_set in response['data']['result']:
            metric = label_set['metric']

            node_name = metric.get('label_kubernetes_io_hostname')
            node_info[node_name] = {}

            instance_type = metric['label_beta_kubernetes_io_instance_type']
            preemptible = 'label_cloud_google_com_gke_preemptible' in metric
            gpu = metric.get('label_cloud_google_com_gke_accelerator')

            node_info[node_name]['instance_type'] = instance_type
            node_info[node_name]['preemptible'] = preemptible
            node_info[node_name]['gpu'] = gpu

        return node_info

    def compute_costs(self, node_data):
        """Get cost for all nodes"""
        gpu_node_costs = 0
        cpu_node_costs = 0
        total_node_costs = 0
        for _, node_dict in node_data.items():
            node_hourly_cost = self.compute_hourly_cost(node_dict)
            node_cost = node_hourly_cost * (node_dict['lifetime'] / 60 / 60)
            if not node_dict['gpu']:
                cpu_node_costs = cpu_node_costs + node_cost
            else:
                gpu_node_costs = gpu_node_costs + node_cost
            total_node_costs = total_node_costs + node_cost
        return cpu_node_costs, gpu_node_costs, total_node_costs

    def compute_hourly_cost(self, node_data):
        """Get the hourly cost of a given node"""
        instance_type = node_data['instance_type']
        gpu = node_data['gpu']
        preemptible = node_data['preemptible']

        # which types of nodes
        key = 'ondemand' if not preemptible else 'preemptible'

        instance_cost = self.cost_table[instance_type][key]

        gpu_cost = 0 if not gpu else self.gpu_table[gpu][key]

        hourly_cost = instance_cost + gpu_cost
        return hourly_cost
