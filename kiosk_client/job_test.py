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
"""Tests for Job class"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import os
import random
import timeit

import pytest
import pytest_twisted

from twisted.internet import defer

from kiosk_client import job

global FAILED
FAILED = False  # global toggle for failed responses


class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class DummyResponse(object):

    def __init__(self):
        self.phrase = b'PHRASE'
        self.request = Bunch(method=b'POST', absoluteURI=b'localhost')

    @property
    def code(self):
        global FAILED
        if FAILED:
            return 500
        return 200

    @pytest_twisted.inlineCallbacks
    def json(self):
        global FAILED
        if FAILED:
            FAILED = False
            yield defer.returnValue(dict({'success': True}))
        else:
            FAILED = True
            raise AttributeError('on purpose')


def _get_default_job(filepath='filepath.png'):
    return job.Job(
        filepath=filepath,
        host='localhost',
        model_name='model_name',
        model_version='0',
        download_results=True,
        update_interval=0.0001)


class TestJob(object):

    def test_basic(self, mocker):
        # create basic job
        j = _get_default_job()

        # properties should be Fals as job has not yet been started
        assert not j.is_done
        assert not j.is_summarized
        # for JSON formatting list values
        j.prediction_time = list(str(x) for x in range(5))
        j.predict_retries = list(str(x) for x in range(5))
        assert isinstance(j.json(), dict)

        # set the status to failed
        j.status = 'failed'
        assert j.is_done
        assert j.is_summarized

        # set the status to done
        j.status = 'done'
        assert j.is_done
        assert not j.is_summarized  # status=done AND other fields are not None

        # model_version should be an integer
        with pytest.raises(ValueError):
            job.Job(filepath='test.png',
                    host='localhost',
                    model_name='model',
                    model_version='version')

        # data_scale should be a float
        with pytest.raises(ValueError):
            job.Job(filepath='test.png',
                    host='localhost',
                    model_name='model',
                    model_version='version',
                    data_scale='one')

        # data_label should be an int
        with pytest.raises(ValueError):
            job.Job(filepath='test.png',
                    host='localhost',
                    model_name='model',
                    model_version='1',
                    data_label='3.14')

        # output_dir should be an existing directory
        with pytest.raises(ValueError):
            job.Job(filepath='test.png',
                    host='localhost',
                    model_name='model',
                    model_version='1',
                    output_dir='not_a_directory')

        # output_dir should be writable
        mocker.patch('os.access', return_value=False)
        with pytest.raises(ValueError):
            job.Job(filepath='test.png',
                    host='localhost',
                    model_name='model',
                    model_version='1')

    def test__log_http_response(self):
        now = timeit.default_timer()
        j = _get_default_job()

        dummy_response = DummyResponse()
        j._log_http_response(dummy_response, now)
        dummy_response.failed = True
        j._log_http_response(dummy_response, now)

    def test__make_post_request(self):
        j = _get_default_job()
        req = j._make_post_request('localhost', data={})
        assert isinstance(req, defer.Deferred)

    @pytest_twisted.inlineCallbacks
    def test_upload_file(self, tmpdir):

        @pytest_twisted.inlineCallbacks
        def dummy_request_success(*_, **__):
            yield defer.returnValue({'uploadedName': 'uploads/blah.png'})

        @pytest_twisted.inlineCallbacks
        def dummy_request_fail(*_, **__):
            yield defer.returnValue(dict())

        filepath = 'test.png'
        p = tmpdir.join(filepath)
        p.write('content')
        j = _get_default_job(filepath=str(p))

        j._retry_post_request_wrapper = dummy_request_success
        uploaded_path = yield j.upload_file()
        assert uploaded_path == 'uploads/blah.png'

        filepath = 'test2.png'
        p = tmpdir.join(filepath)
        p.write('content')
        j = _get_default_job(filepath=str(p))

        j._retry_post_request_wrapper = dummy_request_fail
        job_id = yield j.upload_file()
        assert job_id is None

    @pytest_twisted.inlineCallbacks
    def test_download_output(self, tmpdir, mocker):

        global _download_failed
        _download_failed = False

        @pytest_twisted.inlineCallbacks
        def send_get_request(_, **__):
            global _download_failed
            if _download_failed:
                _download_failed = False
                response = Bunch(collect=lambda x: x(b'success'))
                yield defer.returnValue(response)
            else:
                _download_failed = True
                errs = _get_default_job()._http_errors
                err = errs[random.randint(0, len(errs) - 1)]
                raise err('on purpose')

        mocker.patch('kiosk_client.job.get_download_path',
                     lambda: str(tmpdir))
        j = _get_default_job()
        j.output_url = 'fakeURL.com/testfile.txt'
        mocker.patch('treq.get', send_get_request)

        result = yield j.download_output()
        assert os.path.isfile(result)
        assert str(result).startswith(str(tmpdir))
        with open(result, 'r') as f:
            assert f.read() == 'success'

    @pytest_twisted.inlineCallbacks
    def test_summarize(self):
        j = _get_default_job()

        j.status = 'failed'
        j.get_redis_value = lambda x: True

        value = yield j.summarize()
        assert value

    @pytest_twisted.inlineCallbacks
    def test_monitor(self):
        j = _get_default_job()

        global _monitor_counter
        _monitor_counter = 0

        @pytest_twisted.inlineCallbacks
        def get_redis_value(_):
            global _monitor_counter
            _monitor_counter += 1

            if _monitor_counter > 3:
                yield defer.returnValue('done')
            else:
                yield defer.returnValue(_monitor_counter)

        j.get_redis_value = get_redis_value
        results = yield j.monitor()
        assert results
        assert results == j.is_done

    @pytest_twisted.inlineCallbacks
    def test_restart(self):

        @pytest_twisted.inlineCallbacks
        def _dummy():
            yield defer.returnValue(True)

        # test no job_id
        j = _get_default_job()
        j.start = _dummy
        result = yield j.restart(0.00001)
        assert result

        # test is_done
        j = _get_default_job()
        j.job_id = 1
        j.status = 'done'
        j.summarize = _dummy
        result = yield j.restart(0.000001)
        assert result

        # test not is_done
        j = _get_default_job()
        j.job_id = 1
        j.status = 'in-progress'
        j.monitor = _dummy
        result = yield j.restart(0.000001)
        assert result

    @pytest_twisted.inlineCallbacks
    def test_create(self):

        @pytest_twisted.inlineCallbacks
        def dummy_request_success(*_, **__):
            yield defer.returnValue({'hash': 'dummy_hash'})

        @pytest_twisted.inlineCallbacks
        def dummy_request_fail(*_, **__):
            yield defer.returnValue(dict())

        j = _get_default_job()
        j._retry_post_request_wrapper = dummy_request_success
        job_id = yield j.create()
        assert job_id == 'dummy_hash'

        j = _get_default_job()
        j._retry_post_request_wrapper = dummy_request_fail
        job_id = yield j.create()
        assert job_id is None

    @pytest_twisted.inlineCallbacks
    def test_get_redis_value(self):

        @pytest_twisted.inlineCallbacks
        def dummy_request_success(*_, **__):
            yield defer.returnValue({'value': 'done'})

        @pytest_twisted.inlineCallbacks
        def dummy_request_fail(*_, **__):
            yield defer.returnValue(dict())

        j = _get_default_job()
        j._retry_post_request_wrapper = dummy_request_success
        job_id = yield j.get_redis_value('status')
        assert job_id == 'done'

        j = _get_default_job()
        j._retry_post_request_wrapper = dummy_request_fail
        job_id = yield j.get_redis_value('status')
        assert job_id is None

    @pytest_twisted.inlineCallbacks
    def test_expire(self):

        @pytest_twisted.inlineCallbacks
        def dummy_request_success(*_, **__):
            yield defer.returnValue({'value': 'done'})

        @pytest_twisted.inlineCallbacks
        def dummy_request_fail(*_, **__):
            yield defer.returnValue(dict())

        j = _get_default_job()
        j._retry_post_request_wrapper = dummy_request_success
        job_id = yield j.expire()
        assert job_id == 'done'

        j = _get_default_job()
        j._retry_post_request_wrapper = dummy_request_fail
        job_id = yield j.expire()
        assert job_id is None

    @pytest_twisted.inlineCallbacks
    def test_start(self):

        @pytest_twisted.inlineCallbacks
        def dummy_request_success(*_, **__):
            yield defer.returnValue(True)

        @pytest_twisted.inlineCallbacks
        def dummy_upload_success(*_, **__):
            yield defer.returnValue('uploads/test.png')

        @pytest_twisted.inlineCallbacks
        def dummy_download_success(*_, **__):
            yield defer.returnValue('downloads/test-results.png')

        @pytest_twisted.inlineCallbacks
        def dummy_request_fail(*_, **__):
            yield defer.returnValue(None)

        # test successful path
        j = _get_default_job()
        j.create = dummy_request_success
        j.summarize = dummy_request_success
        j.monitor = dummy_request_success
        j.get_redis_value = dummy_request_success
        j.expire = dummy_request_success
        j.upload_file = dummy_upload_success
        j.download_output = dummy_download_success

        # is_done and is_summarized
        j.status = 'done'
        j.output_url = 'local'
        j.created_at = datetime.datetime.now().isoformat()
        j.finished_at = datetime.datetime.now().isoformat()

        delay = .000001
        upload = True
        value = yield j.start(delay, upload)
        assert value

        # test status is done but not summarized
        j.output_url = None
        value = yield j.start(delay, upload)
        assert value is False  # raise exception which is caught

        # test status is failed
        j.status = 'failed'
        value = yield j.start(delay, upload)
        assert value

        # test bad results
        j.create = dummy_request_fail
        value = yield j.start(delay, upload)
        assert value is False  # failed

    @pytest_twisted.inlineCallbacks
    def test__retry_post_request_wrapper(self, mocker):

        global _make_request_failed
        _make_request_failed = False

        @pytest_twisted.inlineCallbacks
        def dummy_post_request(*_, **__):
            global _make_request_failed
            if _make_request_failed:
                _make_request_failed = False
                yield defer.returnValue(DummyResponse())
            else:
                _make_request_failed = True
                errs = _get_default_job()._http_errors
                err = errs[random.randint(0, len(errs) - 1)]
                raise err('on purpose')

        j = _get_default_job()
        mocker.patch('treq.post', dummy_post_request)
        result = yield j._retry_post_request_wrapper('host', {})
        assert result.get('success')
