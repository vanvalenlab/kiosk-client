# Tests for the file cost_estimator.py

from cost_estimation.grafana.cost_estimator import CostGetter

import pytest
import requests.exceptions
import time

def test_get_time():
    cg = CostGetter()
    
    old_time = int(time.time())
    new_time = cg.get_time()
    assert old_time <= new_time

def test_compose_http_requests():
    cg = CostGetter()
    cg.benchmarking_end_time = cg.get_time()
    cg.compose_http_requests()
    assert cg.node_creation_request == "http://admin:admin@127.0.0.1/api/datasources/proxy/1/api/v1/query_range?query=kube_node_created&start=" + str(cg.benchmarking_start_time) + "&end="+ str(cg.benchmarking_end_time) + "&step=15"
    assert cg.node_label_request == "http://admin:admin@127.0.0.1/api/datasources/proxy/1/api/v1/query_range?query=kube_node_labels&start=" + str(cg.benchmarking_start_time) + "&end="+ str(cg.benchmarking_end_time) + "&step=15"

def test_send_http_requests():
    cg = CostGetter()
    cg.benchmarking_end_time = cg.get_time()
    cg.compose_http_requests()
    with pytest.raises(requests.exceptions.ConnectionError) as requests_node_creation_error:
        cg.send_http_requests(cg.node_creation_request).status == 200
    print(requests_node_creation_error.value)
    assert "/api/datasources/proxy/1/api" in str(requests_node_creation_error.value)
    with pytest.raises(requests.exceptions.ConnectionError) as requests_error:
        cg.send_http_requests(cg.node_label_request).status == 200
    assert "/api/datasources/proxy/1/api" in str(requests_node_creation_error.value)
