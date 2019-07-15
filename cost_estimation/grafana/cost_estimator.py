from decouple import config
import logging
import os
import requests
import sys
import time
import urllib.parse

# defining tables of Google Cloud prices
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
        self.logger = logging.getLogger(str(self.__class__.__name__))

        # validate user input
        if benchmarking_start_time and not benchmarking_end_time:
            try:
                benchmarking_start_time = int(benchmarking_start_time)
            except ValueError:
                self.logger.error('You need to provide either an integer '
                                  'string (e.g., "12345") or a decimal or '
                                  'integer number (e.g., 123.45) for '
                                  ' benchmarking_start_time.')
            now = int(time.time())
            assert benchmarking_start_time <= now

        if benchmarking_start_time and benchmarking_end_time:
            try:
                benchmarking_start_time = int(benchmarking_start_time)
            except ValueError:
                self.logger.error('You need to provide either an integer '
                                  'string (e.g., "12345") or a decimal or '
                                  'integer number (e.g., 123.45) for '
                                  ' benchmarking_start_time.')
            try:
                benchmarking_end_time = int(benchmarking_end_time)
            except ValueError:
                self.logger.error('You need to provide either an integer '
                                  'string (e.g., "12345") or a decimal or '
                                  'integer number (e.g., 123.45) for '
                                  ' benchmarking_end_time.')
            assert benchmarking_start_time <= benchmarking_end_time

        if not benchmarking_start_time and benchmarking_end_time:
            try:
                benchmarking_end_time = int(benchmarking_end_time)
            except ValueError:
                self.logger.error('You need to provide either an integer '
                                  'string (e.g., "12345") or a decimal or '
                                  'integer number (e.g., 123.45) for '
                                  ' benchmarking_end_time.')
            now = int(time.time())
            assert benchmarking_end_time >= now

        # parse user input
        if benchmarking_start_time:
            self.benchmarking_start_time = benchmarking_start_time
        else:
            self.benchmarking_start_time = self.get_time()
        if benchmarking_end_time:
            self.benchmarking_end_time = benchmarking_end_time

        # initialize other necessary variables
        self.cost_table = kwargs.get('cost_table', COST_TABLE)
        self.gpu_table = kwargs.get('gpu_table', GPU_TABLE)

        self.GRAFANA_USER = config('GRAFANA_USER', default='admin')
        self.GRAFANA_PASSWORD = config('GRAFANA_PASSWORD', default='admin')
        self.GRAFANA_IP = config('GRAFANA_IP', default='127.0.0.1')

    def get_time(self):
        # Get current time in epoch seconds.
        # Meant to be called at the beginning and end of a benchmarking run
        # to establish the beginning or end of cost accrual.
        return int(time.time())

    def finish(self):
        # This is the wrapper function for all the functionality
        # that will executed immediately once benchmarking is finished.
        if not self.benchmarking_end_time:
            self.benchmarking_end_time = self.get_time()

        create_request = self.get_http_request({
            'query': 'kube_node_created',
            'start': self.benchmarking_start_time,
            'end': self.benchmarking_end_time,
            'step': 15
        })

        label_request = self.get_http_request({
            'query': 'kube_node_labels',
            'start': self.benchmarking_start_time,
            'end': self.benchmarking_end_time,
            'step': 15
        })

        creation_data = requests.get(create_request).json()
        label_data = requests.get(label_request).json()

        node_data = self.parse_http_response_data(creation_data, label_data)
        total_node_costs = self.compute_costs(node_data)
        return str(total_node_costs)

    def get_http_request(self, data):
        return 'http://{user}:{passwd}@{host}{route}?{querystring}'.format(
            user=self.GRAFANA_USER,
            passwd=self.GRAFANA_PASSWORD,
            host=self.GRAFANA_IP,
            route='/api/datasources/proxy/1/api/v1/query_range',
            querystring=urllib.parse.urlencode(data))

    def parse_http_response_data(self, create_response, label_response):
        node_info = {}

        # parse node liveness data
        creation_data = create_response['data']['result']
        for time_series in creation_data:
            # get node name and create dictionary entry
            node_name = time_series['metric']['node']
            node_info[node_name] = {}
            # get node lifetime
            node_last_data_point = time_series['values'][-1]
            node_start_time = int(node_last_data_point[1])
            # We only want to count costs during benchmarking,
            # in case we start benchmarking long after cluster creation.
            if node_start_time < self.benchmarking_start_time:
                node_start_time = self.benchmarking_start_time
            node_end_time = node_last_data_point[0]
            node_benchmarking_time = node_end_time - node_start_time
            node_info[node_name]['lifetime'] = node_benchmarking_time

        # parse node label data
        label_data = label_response['data']['result']
        for label_set in label_data:
            metric = label_set['metric']

            instance_type = metric['label_beta_kubernetes_io_instance_type']
            preemptible = 'label_cloud_google_com_gke_preemptible' in metric
            gpu = metric.get('label_cloud_google_com_gke_accelerator', 'none')

            for node in node_info:
                if node == metric['label_kubernetes_io_hostname']:
                    node_info[node]['instance_type'] = instance_type
                    node_info[node]['preemptible'] = preemptible
                    node_info[node]['gpu'] = gpu
                    break
        return node_info

    def compute_costs(self, node_data):
        total_node_costs = 0
        for _, node_dict in node_data.items():
            node_hourly_cost = self.compute_hourly_cost(node_dict)
            node_cost = node_hourly_cost * (node_dict['lifetime'] / 60 / 60)
            total_node_costs = total_node_costs + node_cost
        return total_node_costs

    def output_cost_data(self):
        data = 'Total cost of all nodes during benchmarking: {}'.format(
            self.total_node_costs)

        with open('cost_data.txt', 'w') as cost_output_file:
            cost_output_file.write(data)

    # return hourly cost of a given node
    def compute_hourly_cost(self, node_dict):
        instance_type = node_dict['instance_type']
        gpu = node_dict['gpu']
        preemptible = node_dict['preemptible']

        # which types of nodes
        key = 'ondemand' if not preemptible else 'preemptible'

        instance_cost = self.cost_table[instance_type][key]

        gpu_cost = 0 if gpu == 'none' else self.gpu_table[gpu][key]

        hourly_cost = instance_cost + gpu_cost
        return hourly_cost
