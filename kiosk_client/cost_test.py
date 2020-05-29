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
"""Tests for the file cost_estimator.py"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import time

import pytest
import requests.exceptions

from kiosk_client import cost


class FakeCreationData:

    _status_code = 400

    @property
    def status_code(self):
        code = self._status_code
        if code == 400:
            self._status_code = 200

    @staticmethod
    def json(created_at=None, lifetime=10):
        if created_at is None:
            created_at = int(time.time())
        return {
            'data': {
                'result': [
                    {
                        'metric': {
                            '__name__': 'kube_node_created',
                            'endpoint': 'http',
                            'instance': '10.48.5.8:8080',
                            'job': 'kube-state-metrics',
                            'namespace': 'test',
                            'node': 'test_node_1',
                            'pod': 'prometheus-operator-kube-state-metrics-1',
                            'service': 'prometheus-operator-kube-state-metrics'
                        },
                        'values': [
                            [
                                created_at,
                                str(created_at)
                            ],
                            [
                                created_at + lifetime,
                                str(created_at)
                            ]
                        ]
                    },
                    {
                        'metric': {
                            '__name__': 'kube_node_created',
                            'endpoint': 'http',
                            'instance': '10.48.5.9:8080',
                            'job': 'kube-state-metrics',
                            'namespace': 'test',
                            'node': 'test_node_2',
                            'pod': 'prometheus-operator-kube-state-metrics-1',
                            'service': 'prometheus-operator-kube-state-metrics'
                        },
                        'values': [
                            [
                                created_at,
                                str(created_at)
                            ],
                            [
                                created_at + lifetime - lifetime // 2,
                                str(created_at)
                            ],
                            [
                                created_at + lifetime - lifetime // 2,
                                str(created_at + lifetime - lifetime // 2)
                            ],
                            [
                                created_at + lifetime - 1,
                                str(created_at + lifetime - lifetime // 2)
                            ],
                            [
                                created_at + lifetime,
                                str(created_at + lifetime - lifetime // 2)
                            ]
                        ]
                    },
                ],
                'resultType': 'matrix',
            },
            'status': 'success',
        }


class FakeLabelData:

    _status_code = 400

    @property
    def status_code(self):
        code = self._status_code
        if code == 400:
            self._status_code = 200

    @staticmethod
    def json(created_at=None, lifetime=10):
        if created_at is None:
            created_at = int(time.time())
        return {
            'data': {
                'result': [
                    {
                        'metric': {
                            '__name__': 'kube_node_labels',
                            'endpoint': 'http',
                            'instance': '10.48.5.8:8080',
                            'job': 'kube-state-metrics',
                            'label_beta_kubernetes_io_arch': 'amd64',
                            'label_beta_kubernetes_io_fluentd_ds_ready':
                                'true',
                            'label_beta_kubernetes_io_instance_type':
                                'n1-highmem-2',
                            'label_beta_kubernetes_io_os': 'linux',
                            'label_cloud_google_com_gke_accelerator':
                                'nvidia-tesla-v100',
                            'label_cloud_google_com_gke_nodepool':
                                'prediction-gpu',
                            'label_cloud_google_com_gke_os_distribution':
                                'cos',
                            'label_cloud_google_com_gke_preemptible': 'true',
                            'label_failure_domain_beta_kubernetes_io_region':
                                'us-west1',
                            'label_failure_domain_beta_kubernetes_io_zone':
                                'us-west1-a',
                            'label_kubernetes_io_hostname': 'test_node_1',
                            'namespace': 'monitoring',
                            'node': 'test_node_1',
                            'pod': 'prometheus-operator-kube-state-metrics-1',
                            'service': 'prometheus-operator-kube-state-metrics'
                        },
                        'values': [
                            [
                                created_at,
                                '1'
                            ],
                            [
                                created_at + lifetime,
                                '1'
                            ]
                        ]
                    },
                    {
                        'metric': {
                            '__name__': 'kube_node_labels',
                            'endpoint': 'http',
                            'instance': '10.48.5.9:8080',
                            'job': 'kube-state-metrics',
                            'label_beta_kubernetes_io_arch': 'amd64',
                            'label_beta_kubernetes_io_fluentd_ds_ready':
                                'true',
                            'label_beta_kubernetes_io_instance_type':
                                'n1-highmem-2',
                            'label_beta_kubernetes_io_os': 'linux',
                            'label_cloud_google_com_gke_nodepool':
                                'logstash-cpu',
                            'label_cloud_google_com_gke_os_distribution':
                                'cos',
                            'label_failure_domain_beta_kubernetes_io_region':
                                'us-west1',
                            'label_failure_domain_beta_kubernetes_io_zone':
                                'us-west1-a',
                            'label_kubernetes_io_hostname': 'test_node_2',
                            'namespace': 'monitoring',
                            'node': 'test_node_2',
                            'pod': 'prometheus-operator-kube-state-metrics-1',
                            'service': 'prometheus-operator-kube-state-metrics'
                        },
                        'values': [
                            [
                                created_at,
                                '1'
                            ],
                            [
                                created_at + lifetime,
                                '1'
                            ]
                        ]
                    },
                ],
                'resultType': 'matrix'
            },
            'status': 'success'
        }


class TestCostGetter(object):

    def fake_requests_get(self, http_request, **_):
        if 'kube_node_created' in http_request:
            return FakeCreationData()
        if 'kube_node_labels' in http_request:
            return FakeLabelData()
        raise ValueError('Your http_request does not contain '
                         'a recognized Grafana metric.')

    @pytest.fixture(autouse=True)
    def monkeypatch(self, monkeypatch):
        monkeypatch.setattr(requests, 'get', self.fake_requests_get)

    def test_init(self):
        # times are intentionally not being cast to ints
        now = time.time()
        nower = now * 2
        # passing start but not end time
        with pytest.raises(ValueError):
            cost.CostGetter(benchmarking_start_time=nower)
        # passing end but not start time
        with pytest.raises(ValueError):
            cost.CostGetter(benchmarking_end_time=0)
        # passing both start and end times
        cost.CostGetter(benchmarking_start_time=now, benchmarking_end_time=now)

    def test_get_time(self):
        cg = cost.CostGetter()  # object creation
        old_time = int(time.time())
        new_time = cg.get_time()
        assert old_time <= new_time

    def test_send_grafana_api_request(self):
        cg = cost.CostGetter()
        response = cg.send_grafana_api_request('kube_node_created')
        assert isinstance(response, dict)

    def test_finish(self):
        start_time = time.time() - 100  # started 100s ago
        cg = cost.CostGetter(benchmarking_start_time=start_time)

        # benchmarking_end_time is not generated until finish() is called
        assert not cg.benchmarking_end_time

        cpu_costs, gpu_costs, total_costs = cg.finish()

        # did benchmarking_end_time get auto-generated?
        assert cg.benchmarking_end_time

        # did entire pipeline process correctly?
        cpu_costs = float(cpu_costs)
        total_costs = float(total_costs)
        gpu_costs = float(gpu_costs)
        assert '%.9f' % (cpu_costs) == '0.000328889'
        assert '%.9f' % (gpu_costs) == '0.002125000'
        assert '%.9f' % (total_costs) == '7.002453889'

    def test_parse_create_response(self):
        # test node exists after benchmarking
        start_time = int(time.time()) - 100  # a little while ago.
        cg = cost.CostGetter(benchmarking_start_time=start_time)

        expected_node_names = ['test_node_1', 'test_node_2']
        lifetime = random.randint(20, 100)

        creation_data = FakeCreationData.json(
            created_at=start_time + 10,  # node started after benchmarking
            lifetime=lifetime)

        node_info = cg.parse_create_response(creation_data)

        for name in expected_node_names:
            assert node_info[name]['lifetime'] == lifetime

        # test node exists before benchmarking
        creation_data = FakeCreationData.json(
            created_at=start_time - 10,  # node started before benchmarking
            lifetime=lifetime)

        node_info = cg.parse_create_response(creation_data)

        for name in expected_node_names:
            assert node_info[name]['lifetime'] == lifetime - 10

    def test_parse_label_response(self):
        # test node exists after benchmarking
        start_time = int(time.time()) - 100  # a little while ago.
        cg = cost.CostGetter(benchmarking_start_time=start_time)

        expected_node_names = ['test_node_1', 'test_node_2']
        expected_preemptibles = [True, False]
        expected_gpus = ['nvidia-tesla-v100', None]

        expected = zip(
            expected_node_names,
            expected_preemptibles,
            expected_gpus
        )

        lifetime = random.randint(11, 100)

        creation_data = FakeLabelData.json(
            created_at=start_time + 10,  # node started after benchmarking
            lifetime=lifetime)

        node_info = cg.parse_label_response(creation_data)

        for name, pre, gpu in expected:
            assert node_info[name]['instance_type'] == 'n1-highmem-2'
            assert node_info[name]['preemptible'] is pre
            assert node_info[name]['gpu'] == gpu

        # test node exists before benchmarking
        creation_data = FakeLabelData.json(
            created_at=start_time - 10,  # node started before benchmarking
            lifetime=lifetime)

        node_info = cg.parse_label_response(creation_data)

        for name, pre, gpu in expected:
            assert node_info[name]['instance_type'] == 'n1-highmem-2'
            assert node_info[name]['preemptible'] is pre
            assert node_info[name]['gpu'] == gpu

    def test_compute_costs(self):
        cg = cost.CostGetter()
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
        cg = cost.CostGetter()
        node_dict = {
            'instance_type': 'n1-highmem-2',
            'gpu': 'nvidia-tesla-v100',
        }
        for preemptible in (True, False):
            node_dict['preemptible'] = preemptible
            k = 'preemptible' if preemptible else 'ondemand'
            expected = (cost.COST_TABLE[node_dict['instance_type']][k] +
                        cost.GPU_TABLE[node_dict['gpu']][k])
            assert cg.compute_hourly_cost(node_dict) == expected
