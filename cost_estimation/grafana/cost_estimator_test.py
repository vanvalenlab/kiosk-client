# Tests for the file cost_estimator.py

from cost_estimation.grafana.cost_estimator import CostGetter

import json
import pytest
import requests.exceptions
import time
import urllib.parse


class TestCostGetter(object):

    _creation_data = {
        'data': {
            'result': [
                {
                    "metric": {
                        "__name__": "kube_node_created",
                        "endpoint": "http",
                        "instance": "10.48.5.8:8080",
                        "job": "kube-state-metrics",
                        "namespace": "test",
                        "node": "test_node_1",
                        "pod": "prometheus-operator-kube-state-metrics-1234",
                        "service": "prometheus-operator-kube-state-metrics"
                    },
                    "values": [
                        [
                            1562872560,
                            "1562872553"
                        ],
                        [
                            1562873595,
                            "1562872553"
                        ]
                    ]
                },
            ],
            'resultType': 'matrix',
        },
        'status': 'success',
    }

    _label_data = {
        "data": {
            "result": [
                {
                    "metric": {
                        "__name__": "kube_node_labels",
                        "endpoint": "http",
                        "instance": "10.48.5.8:8080",
                        "job": "kube-state-metrics",
                        "label_beta_kubernetes_io_arch": "amd64",
                        "label_beta_kubernetes_io_fluentd_ds_ready": "true",
                        "label_beta_kubernetes_io_instance_type": "n1-highmem-2",
                        "label_beta_kubernetes_io_os": "linux",
                        "label_cloud_google_com_gke_accelerator": "nvidia-tesla-v100",
                        "label_cloud_google_com_gke_nodepool": "prediction-gpu",
                        "label_cloud_google_com_gke_os_distribution": "cos",
                        "label_cloud_google_com_gke_preemptible": "true",
                        "label_failure_domain_beta_kubernetes_io_region": "us-west1",
                        "label_failure_domain_beta_kubernetes_io_zone": "us-west1-a",
                        "label_kubernetes_io_hostname": "test_node_1",
                        "namespace": "monitoring",
                        "node": "test_node_1",
                        "pod": "prometheus-operator-kube-state-metrics-1234",
                        "service": "prometheus-operator-kube-state-metrics"
                    },
                    "values": [
                        [
                            1562872560,
                            "1"
                        ],
                        [
                            1562873595,
                            "1"
                        ]
                    ]
                },
            ],
            "resultType": "matrix"
        },
        "status": "success"
    }


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
        node_info = cg.parse_http_response_data(
            self._creation_data, self._label_data)
        name = 'test_node_1'
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
