# Tests for the file cost_estimator.py

from cost_estimation.grafana.cost_estimator import CostGetter

import json
import pytest
import requests.exceptions
import time
import urllib.parse


class TestCostGetter(object):

    def test_get_time(self):
        # object creation
        cg = CostGetter()

        old_time = int(time.time())

        new_time = cg.get_time()
        assert old_time <= new_time

    def test_parse_http_response_data(self):
        # object creation
        cg = CostGetter()

        # needed patch for testing
        cg.benchmarking_start_time = 0

        # patch for finish()
        with open('./cost_estimation/grafana/tests/node_creation_data.json') as json_file:
            creation_data = json.load(json_file)
        with open('./cost_estimation/grafana/tests/node_label_data.json') as json_file:
            label_data = json.load(json_file)

        node_info = cg.parse_http_response_data(creation_data, label_data)
        name = 'cluster-benchmarking-prediction-gpu-bf9b9dc6-2s70'
        assert node_info[name]['lifetime'] == 1042
        assert node_info[name]['instance_type'] == 'n1-highmem-2'
        assert node_info[name]['preemptible']
        assert node_info[name]['gpu'] == 'nvidia-tesla-v100'

        for key in node_info:
            assert isinstance(node_info[key]['lifetime'], int)
            assert isinstance(node_info[key]['preemptible'], bool)

    def test_compute_costs(self):
        cg = CostGetter()
        node_info = {
            'node1': {
                'lifetime': 3600,
                'instance_type': 'n1-highmem-2',
                'gpu': 'nvidia-tesla-v100',
                'preemptible': False
            },
            'node2': {
                'lifetime': 3600,
                'instance_type': 'n1-highmem-2',
                'gpu': 'nvidia-tesla-v100',
                'preemptible': False
            }
        }
        total_node_costs = cg.compute_costs(node_info)
        assert total_node_costs == 5.1968

    def test_compute_hourly_cost(self):
        cg = CostGetter()
        node_dict = {
            'instance_type': 'n1-highmem-2',
            'gpu': 'nvidia-tesla-v100',
            'preemptible': False
        }
        assert cg.compute_hourly_cost(node_dict) == 2.5984
