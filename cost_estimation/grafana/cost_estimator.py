from decouple import config
import logging
import os
import requests
import sys
import time
import urllib.parse

# defining tables of Google Cloud prices
# current, as of 6/17/19
cost_table = {
    'n1-standard-1': {"ondemand": 0.0475, "preemptible": 0.0100},
    'n1-standard-2': {"ondemand": 0.0950, "preemptible": 0.0200},
    'n1-standard-4': {"ondemand": 0.1900, "preemptible": 0.0400},
    'n1-standard-8': {"ondemand": 0.3800, "preemptible": 0.0800},
    'n1-standard-16': {"ondemand": 0.7600, "preemptible": 0.1600},
    'n1-standard-32': {"ondemand": 1.5200, "preemptible": 0.3200},
    'n1-standard-64': {"ondemand": 3.0400, "preemptible": 0.6400},
    'n1-standard-96': {"ondemand": 4.5600, "preemptible": 0.9600},
    'n1-highmem-2': {"ondemand": 0.1184, "preemptible": 0.0250},
    'n1-highmem-4': {"ondemand": 0.2368, "preemptible": 0.0500},
    'n1-highmem-8': {"ondemand": 0.4736, "preemptible": 0.1000},
    'n1-highmem-16': {"ondemand": 0.9472, "preemptible": 0.2000},
    'n1-highmem-32': {"ondemand": 1.8944, "preemptible": 0.4000},
    'n1-highmem-64': {"ondemand": 3.7888, "preemptible": 0.8000},
    'n1-highmem-96': {"ondemand": 5.6832, "preemptible": 1.2000},
    'n1-highcpu-2': {"ondemand": 0.0709, "preemptible": 0.0150},
    'n1-highcpu-4': {"ondemand": 0.1418, "preemptible": 0.0300},
    'n1-highcpu-8': {"ondemand": 0.2836, "preemptible": 0.0600},
    'n1-highcpu-16': {"ondemand": 0.5672, "preemptible": 0.1200},
    'n1-highcpu-32': {"ondemand": 1.1344, "preemptible": 0.2400},
    'n1-highcpu-64': {"ondemand": 2.2688, "preemptible": 0.4800},
    'n1-highcpu-96': {"ondemand": 3.4020, "preemptible": 0.7200},
    'n1-ultramem-40': {"ondemand": 6.3039, "preemptible": 1.3311},
    'n1-ultramem-80': {"ondemand": 12.6078, "preemptible": 2.6622},
    'n1-ultramem-160': {"ondemand": 25.2156, "preemptible": 5.3244},
    'n1-megamem-96': {"ondemand": 10.6740, "preemptible": 2.2600}
}

gpu_table = {
    'nvidia-tesla-t4': {"ondemand": 0.95, "preemptible": 0.29},
    'nvidia-tesla-p4': {"ondemand": 0.60, "preemptible": 0.216},
    'nvidia-tesla-v100': {"ondemand": 2.48, "preemptible": 0.74},
    'nvidia-tesla-p100': {"ondemand": 1.46, "preemptible": 0.43},
    'nvidia-tesla-k80': {"ondemand": 0.45, "preemptible": 0.135}
}


class CostGetter:

    def __init__(self,
                 benchmarking_start_time=None,
                 benchmarking_end_time=None):
        # bring globals into scope
        global cost_table
        global gpu_table

        # Initialize logger
        self.logger = logging.getLogger(str(self.__class__.__name__))
        logger_formatter = \
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        stderr_handler.setFormatter(logger_formatter)
        self.logger.addHandler(stderr_handler)
        file_handler = logging.FileHandler("cost_estimation_logging.txt")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logger_formatter)
        self.logger.addHandler(file_handler)

        # validate user input
        if benchmarking_start_time and not benchmarking_end_time:
            try:
                benchmarking_start_time = int(benchmarking_start_time)
            except ValueError:
                self.logger.error("{}{}{}{}".format("You need to provide either an integer",
                                                    " string (e.g., '12345') or a decimal",
                                                    " or integer number (e.g., 123.45) for",
                                                    " benchmarking_start_time."))
            now = int(time.time())
            assert benchmarking_start_time <= now
        if benchmarking_start_time and benchmarking_end_time:
            try:
                benchmarking_start_time = int(benchmarking_start_time)
            except ValueError:
                self.logger.error("{}{}{}{}".format("You need to provide either an integer",
                                                    " string (e.g., '12345') or a decimal",
                                                    " or integer number (e.g., 123.45) for",
                                                    " benchmarking_start_time."))
            try:
                benchmarking_end_time = int(benchmarking_end_time)
            except ValueError:
                self.logger.error("{}{}{}{}".format("You need to provide either an integer",
                                                    " string (e.g., '12345') or a decimal",
                                                    " or integer number (e.g., 123.45) for",
                                                    " benchmarking_end_time."))
            assert benchmarking_start_time <= benchmarking_end_time
        if not benchmarking_start_time and benchmarking_end_time:
            try:
                benchmarking_end_time = int(benchmarking_end_time)
            except ValueError:
                self.logger.error("{}{}{}{}".format("You need to provide either an integer",
                                                    " string (e.g., '12345') or a decimal",
                                                    " or integer number (e.g., 123.45) for",
                                                    " benchmarking_end_time."))
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
        self.cost_table = cost_table
        self.gpu_table = gpu_table
        self.GRAFANA_USER = config("GRAFANA_USER", cast=str, default="admin")
        self.GRAFANA_PASSWORD = config("GRAFANA_PASSWORD", cast=str, default="admin")
        self.GRAFANA_IP = config("GRAFANA_IP", cast=str, default="127.0.0.1")

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
        self.http_request = self.compose_http_requests()
        self.compose_http_requests()
        self.node_creation_data = self.send_http_requests(self.node_creation_request).json()
        self.node_label_data = self.send_http_requests(self.node_label_request).json()
        self.parse_http_response_data()
        self.compute_costs()
        # self.output_cost_data()
        return str(self.total_node_costs)

    def compose_http_requests(self):
        # This function assembles the HTTP request strings that will be sent
        # to Grafana.
        request_backbone = \
            "{}{}{}{}{}{}{}".format("http://", self.GRAFANA_USER, ":",
                                    self.GRAFANA_PASSWORD, "@", self.GRAFANA_IP,
                                    "/api/datasources/proxy/1/api/v1/query_range?")
        node_creation_http_arguments = {
            "query": "kube_node_created",
            "start": str(self.benchmarking_start_time),
            "end": str(self.benchmarking_end_time),
            "step": 15
        }
        node_label_http_arguments = {
            "query": "kube_node_labels",
            "start": str(self.benchmarking_start_time),
            "end": str(self.benchmarking_end_time),
            "step": 15
        }
        self.node_creation_request = \
            "{}{}".format(request_backbone,
                          urllib.parse.urlencode(node_creation_http_arguments))
        self.node_label_request = \
            "{}{}".format(request_backbone,
                          urllib.parse.urlencode(node_label_http_arguments))

    def send_http_requests(self, request):
        # This function sends a HTTP request to Grafana and returns the output.
        response = requests.get(request)
        return response

    def parse_http_response_data(self):
        self.node_info = {}

        # parse node liveness data
        creation_data = self.node_creation_data["data"]["result"]
        for time_series in creation_data:
            # get node name and create dictionary entry
            node_name = time_series["metric"]["node"]
            self.node_info[node_name] = {}
            # get node lifetime
            node_last_data_point = time_series["values"][-1]
            node_start_time = int(node_last_data_point[1])
            # We only want to count costs during benchmarking,
            # in case we start benchmarking long after cluster creation.
            if node_start_time < self.benchmarking_start_time:
                node_start_time = self.benchmarking_start_time
            node_end_time = node_last_data_point[0]
            node_benchmarking_time = node_end_time - node_start_time
            self.node_info[node_name]["lifetime"] = node_benchmarking_time

        # parse node label data
        label_data = self.node_label_data["data"]["result"]
        for label_set in label_data:
            instance_type = \
                label_set["metric"]["label_beta_kubernetes_io_instance_type"]
            if "label_cloud_google_com_gke_preemptible" in label_set["metric"]:
                preemptible = True
            else:
                preemptible = False
            if "label_cloud_google_com_gke_accelerator" in label_set["metric"]:
                gpu = label_set["metric"]["label_cloud_google_com_gke_accelerator"]
            else:
                gpu = "none"
            for node in self.node_info.keys():
                if node == label_set["metric"]["label_kubernetes_io_hostname"]:
                    self.node_info[node]["instance_type"] = instance_type
                    self.node_info[node]["preemptible"] = preemptible
                    self.node_info[node]["gpu"] = gpu
                    break

    def compute_costs(self):
        total_node_costs = 0
        for _, node_dict in self.node_info.items():
            node_hourly_cost = self.compute_hourly_cost(node_dict)
            node_cost = node_hourly_cost * (node_dict["lifetime"] / 60 / 60)
            total_node_costs = total_node_costs + node_cost
        self.total_node_costs = total_node_costs

    def output_cost_data(self):
        with open("cost_data.txt", "w") as cost_output_file:
            cost_output_file.write(
                "Total cost of all nodes during benchmarking: " + str(self.total_node_costs))

    # return hourly cost of a given node
    def compute_hourly_cost(self, node_dict):
        instance_type = node_dict['instance_type']
        gpu = node_dict['gpu']
        preemptible = node_dict['preemptible']

        # initialize cost
        hourly_cost = 0
        # add in instnace cost
        if not preemptible:
            hourly_cost = hourly_cost + \
                self.cost_table[instance_type]["ondemand"]
        else:
            hourly_cost = hourly_cost + \
                self.cost_table[instance_type]["preemptible"]
        # add in GPU cost
        if gpu != "none":
            if not preemptible:
                hourly_cost = hourly_cost + \
                    self.gpu_table[gpu]["ondemand"]
            else:
                hourly_cost = hourly_cost + \
                    self.gpu_table[gpu]["preemptible"]
        return hourly_cost
