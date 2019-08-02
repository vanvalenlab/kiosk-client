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
"""Tests for Job class"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest
import pytest_twisted

from benchmarking import job


class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class TestJob(object):

    def test_basic(self):
        # create basic job
        j = job.Job(
            filepath='filepath.png',
            host='localhost',
            model_name='model_name',
            model_version='0',
            refresh_rate=0)

        # properties should be Fals as job has not yet been started
        assert not j.is_done
        assert not j.is_summarized
        assert isinstance(j.json(), dict)

        # set the status to failed
        j.status = 'failed'
        assert j.is_done
        assert j.is_summarized

        # set the status to done
        j.status = 'done'
        assert j.is_done
        assert not j.is_summarized  # status=done AND other fields are not None

        with pytest.raises(ValueError):
            # model_version should be an integer
            job.Job(filepath='test.png',
                    host='localhost',
                    model_name='model',
                    model_version='version')

    def test__log_http_response(self):
        j = job.Job(
            filepath='filepath.png',
            host='localhost',
            model_name='model_name',
            model_version='0')

        dummy_response_success = Bunch(
            code=200, phrase=b'OK',
            request=Bunch(method=b'GET', absoluteURI=b'localhost'))

        dummy_response_fail = Bunch(
            code=500, phrase=b'FAIL',
            request=Bunch(method=b'GET', absoluteURI=b'localhost'))

        j._log_http_response(dummy_response_success)
        j._log_http_response(dummy_response_fail)

    @pytest_twisted.inlineCallbacks
    def test_summarize(self):
        j = job.Job(
            filepath='filepath.png',
            host='localhost',
            model_name='model_name',
            model_version='0',
            refresh_rate=0)

        j.status = 'failed'
        j.get_redis_value = lambda x: True

        value = yield j.summarize()
        assert value
