# Copyright 2016-2019 The Van Valen Lab at the California Institute of
# Technology (Caltech), with support from the Paul Allen Family Foundation,
# Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
# All rights reserved.
#
# Licensed under a modified Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.github.com/vanvalenlab/kiosk-benchmarking/LICENSE
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
"""Tests for the file cost_estimator.py"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

import pytest
import requests.exceptions

from benchmarking.cost import CostGetter


class FakeCreationData:

    @staticmethod
    def json():
        return {
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
                            "pod": "prometheus-operator-kube-state-metrics-1",
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
                    {
                        "metric": {
                            "__name__": "kube_node_created",
                            "endpoint": "http",
                            "instance": "10.48.5.9:8080",
                            "job": "kube-state-metrics",
                            "namespace": "test",
                            "node": "test_node_2",
                            "pod": "prometheus-operator-kube-state-metrics-1",
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


class FakeLabelData:

    @staticmethod
    def json():
        return {
            "data": {
                "result": [
                    {
                        "metric": {
                            "__name__": "kube_node_labels",
                            "endpoint": "http",
                            "instance": "10.48.5.8:8080",
                            "job": "kube-state-metrics",
                            "label_beta_kubernetes_io_arch": "amd64",
                            "label_beta_kubernetes_io_fluentd_ds_ready":
                                "true",
                            "label_beta_kubernetes_io_instance_type":
                                "n1-highmem-2",
                            "label_beta_kubernetes_io_os": "linux",
                            "label_cloud_google_com_gke_accelerator":
                                "nvidia-tesla-v100",
                            "label_cloud_google_com_gke_nodepool":
                                "prediction-gpu",
                            "label_cloud_google_com_gke_os_distribution":
                                "cos",
                            "label_cloud_google_com_gke_preemptible": "true",
                            "label_failure_domain_beta_kubernetes_io_region":
                                "us-west1",
                            "label_failure_domain_beta_kubernetes_io_zone":
                                "us-west1-a",
                            "label_kubernetes_io_hostname": "test_node_1",
                            "namespace": "monitoring",
                            "node": "test_node_1",
                            "pod": "prometheus-operator-kube-state-metrics-1",
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
                    {
                        "metric": {
                            "__name__": "kube_node_labels",
                            "endpoint": "http",
                            "instance": "10.48.5.9:8080",
                            "job": "kube-state-metrics",
                            "label_beta_kubernetes_io_arch": "amd64",
                            "label_beta_kubernetes_io_fluentd_ds_ready":
                                "true",
                            "label_beta_kubernetes_io_instance_type":
                                "n1-highmem-2",
                            "label_beta_kubernetes_io_os": "linux",
                            "label_cloud_google_com_gke_nodepool":
                                "logstash-cpu",
                            "label_cloud_google_com_gke_os_distribution":
                                "cos",
                            "label_failure_domain_beta_kubernetes_io_region":
                                "us-west1",
                            "label_failure_domain_beta_kubernetes_io_zone":
                                "us-west1-a",
                            "label_kubernetes_io_hostname": "test_node_2",
                            "namespace": "monitoring",
                            "node": "test_node_1",
                            "pod": "prometheus-operator-kube-state-metrics-1",
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


class TestCostGetter(object):

    def fake_requests_get(self, http_request, **_):
        if "kube_node_created" in http_request:
            return FakeCreationData()
        if "kube_node_labels" in http_request:
            return FakeLabelData()
        raise ValueError("Your http_request doesn't "
                         "contain a recognized Grafana metric.")

    @pytest.fixture(autouse=True)
    def monkeypatch(self, monkeypatch):
        monkeypatch.setattr(requests, "get", self.fake_requests_get)

    def test___init__(self):
        # times are intentionally not being cast to ints
        now = time.time()
        nower = now * 2
        # passing start but not end time
        with pytest.raises(ValueError):
            CostGetter(benchmarking_start_time=nower)
        # passing end but not start time
        with pytest.raises(ValueError):
            CostGetter(benchmarking_end_time=0)
        # passing both start and end times
        CostGetter(benchmarking_start_time=now, benchmarking_end_time=now)

    def test_get_time(self):
        cg = CostGetter()  # object creation
        old_time = int(time.time())
        new_time = cg.get_time()
        assert old_time <= new_time

    def test_finish(self):
        cg = CostGetter()
        # benchmarking_end_time is not generated until finish() is called
        assert not cg.benchmarking_end_time

        # needed patch for testing
        cg.benchmarking_start_time = 1562872553

        cpu_costs, gpu_costs, total_costs = cg.finish()
        # did benchmarking_end_time get auto-generated?
        assert cg.benchmarking_end_time
        # did patch work?
        assert cg.creation_data == FakeCreationData.json()
        assert cg.label_data == FakeLabelData.json()
        # did entire pipeline process correctly?
        cpu_costs = float(cpu_costs)
        total_costs = float(total_costs)
        assert "%.9f" % (cpu_costs) == "0.034270222"
        assert gpu_costs == "0.221425"
        assert "%.9f" % (total_costs) == "7.255695222"

    def test_parse_http_response_data_fresh_node(self):
        # object creation
        cg = CostGetter()

        # needed patch for testing
        cg.benchmarking_start_time = 1562872552

        # patching HTTP request responses
        creation_data = FakeCreationData.json()
        label_data = FakeLabelData.json()

        node_info = cg.parse_http_response_data(creation_data, label_data)
        name = 'test_node_1'
        assert node_info[name]['lifetime'] == 1042
        assert node_info[name]['instance_type'] == 'n1-highmem-2'
        assert node_info[name]['preemptible']
        assert node_info[name]['gpu'] == 'nvidia-tesla-v100'

        for key in node_info:
            assert isinstance(node_info[key]['lifetime'], int)
            assert isinstance(node_info[key]['preemptible'], bool)

    def test_parse_http_response_data_old_node(self):
        # object creation
        cg = CostGetter()

        # needed patch for testing
        cg.benchmarking_start_time = 1562872554

        # patching HTTP request responses
        creation_data = FakeCreationData.json()
        label_data = FakeLabelData.json()

        node_info = cg.parse_http_response_data(creation_data, label_data)
        name = 'test_node_1'
        assert node_info[name]['lifetime'] == 1041
        assert node_info[name]['instance_type'] == 'n1-highmem-2'
        assert node_info[name]['preemptible']
        assert node_info[name]['gpu'] == 'nvidia-tesla-v100'

        for key in node_info:
            assert isinstance(node_info[key]['lifetime'], int)
            assert isinstance(node_info[key]['preemptible'], bool)

    def test_compute_costs_with_patched_function(self):
        cg = CostGetter()

        # needed patch for testing
        cg.benchmarking_start_time = 1562872553

        # patching HTTP request responses
        creation_data = FakeCreationData.json()
        label_data = FakeLabelData.json()

        node_info = cg.parse_http_response_data(creation_data, label_data)

        cpu_costs, gpu_costs, total_costs = cg.compute_costs(node_info)
        assert float("%.9f" % (cpu_costs)) == 0.034270222
        assert gpu_costs == 0.221425
        assert float("%.9f" % (total_costs)) == 0.255695222

    def test_compute_costs_without_patched_function(self):
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
        cpu_costs, gpu_costs, total_costs = cg.compute_costs(node_info)
        assert cpu_costs == 0
        assert gpu_costs == 5.1968
        assert total_costs == 5.1968

    def test_compute_hourly_cost(self):
        cg = CostGetter()
        node_dict = {
            'instance_type': 'n1-highmem-2',
            'gpu': 'nvidia-tesla-v100',
            'preemptible': False
        }
        assert cg.compute_hourly_cost(node_dict) == 2.5984
