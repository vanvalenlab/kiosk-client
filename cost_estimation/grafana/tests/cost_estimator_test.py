# Tests for the file cost_estimator.py

from cost_estimation.grafana.cost_estimator import CostGetter

import json
import pytest
import requests.exceptions
import time


def test_get_time():
    # object creation
    cg = CostGetter()

    old_time = int(time.time())

    new_time = cg.get_time()
    assert old_time <= new_time


def test_compose_http_requests():
    # object creation
    cg = CostGetter()

    # patch for finish()
    cg.benchmarking_end_time = cg.get_time()

    cg.compose_http_requests()
    assert cg.node_creation_request == \
            "http://admin:admin@127.0.0.1/api/datasources/proxy/1/api" \
            + "/v1/query_range?query=kube_node_created&start=" \
            + str(cg.benchmarking_start_time) + "&end=" \
            + str(cg.benchmarking_end_time) + "&step=15"
    assert cg.node_label_request == \
            "http://admin:admin@127.0.0.1/api/datasources/proxy/1/api" \
            + "/v1/query_range?query=kube_node_labels&start=" \
            + str(cg.benchmarking_start_time) + "&end=" \
            + str(cg.benchmarking_end_time) + "&step=15"


def test_send_http_requests():
    # object creation
    cg = CostGetter()

    # patch for finish()
    cg.benchmarking_end_time = cg.get_time()

    # patch for compose_http_requests()
    cg.node_creation_request = \
            "http://admin:admin@127.0.0.1/api/datasources/proxy/1/api" \
            + "/v1/query_range?query=kube_node_created&start=" \
            + str(cg.benchmarking_start_time) + "&end=" \
            + str(cg.benchmarking_end_time) + "&step=15"
    cg.node_label_request = \
            "http://admin:admin@127.0.0.1/api/datasources/proxy/1/api" \
            + "/v1/query_range?query=kube_node_labels&start=" \
            + str(cg.benchmarking_start_time) + "&end=" \
            + str(cg.benchmarking_end_time) + "&step=15"

    with pytest.raises(requests.exceptions.ConnectionError) \
            as requests_node_creation_error:
        cg.send_http_requests(cg.node_creation_request).status == 200
    assert "/api/datasources/proxy/1/api" \
            in str(requests_node_creation_error.value)
    with pytest.raises(requests.exceptions.ConnectionError) \
            as requests_error:
        cg.send_http_requests(cg.node_label_request).status == 200
    assert "/api/datasources/proxy/1/api" \
            in str(requests_node_creation_error.value)

def test_parse_http_response_data():
    # object creation
    cg = CostGetter()

    # needed patch for testing
    cg.benchmarking_start_time = 0

    # patch for finish()
    with open("./cost_estimation/grafana/tests/node_creation_data.json") \
            as json_file:
        cg.node_creation_data = json.load(json_file)
    with open("./cost_estimation/grafana/tests/node_label_data.json") \
            as json_file:
        cg.node_label_data = json.load(json_file)

    cg.parse_http_response_data()
    assert cg.node_info\
            ["cluster-benchmarking-prediction-gpu-bf9b9dc6-2s70"]\
            ["lifetime"] == 1042
    assert cg.node_info\
            ["cluster-benchmarking-prediction-gpu-bf9b9dc6-2s70"]\
            ["instance_type"] == "n1-highmem-2"
    assert cg.node_info\
            ["cluster-benchmarking-prediction-gpu-bf9b9dc6-2s70"]["preemptible"]
    assert cg.node_info\
            ["cluster-benchmarking-prediction-gpu-bf9b9dc6-2s70"]\
            ["gpu"] == "nvidia-tesla-v100"
    for node_name, node_dict in cg.node_info.items():
        assert type(node_dict["lifetime"]) is int
    for node_name, node_dict in cg.node_info.items():
        assert type(node_dict["preemptible"]) is bool

def test_compute_costs():
    cg = CostGetter()
    cg.node_info = {}
    cg.node_info["node1"] = {}
    cg.node_info["node1"]['lifetime'] = 3600
    cg.node_info["node1"]['instance_type'] = "n1-highmem-2"
    cg.node_info["node1"]['gpu'] = "nvidia-tesla-v100"
    cg.node_info["node1"]['preemptible'] = False
    cg.node_info["node2"] = {}
    cg.node_info["node2"]['lifetime'] = 3600
    cg.node_info["node2"]['instance_type'] = "n1-highmem-2"
    cg.node_info["node2"]['gpu'] = "nvidia-tesla-v100"
    cg.node_info["node2"]['preemptible'] = False
    cg.compute_costs()
    assert cg.total_node_costs == 5.1968

def test_compute_hourly_cost():
    cg = CostGetter()
    node_dict = {}
    node_dict['instance_type'] = "n1-highmem-2"
    node_dict['gpu'] = "nvidia-tesla-v100"
    node_dict['preemptible'] = False
    assert cg.compute_hourly_cost(node_dict) == 2.5984
