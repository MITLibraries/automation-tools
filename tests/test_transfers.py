#!/usr/bin/env python
import collections
import os
import unittest
from unittest import mock

import requests

from transfers import errors
from transfers import models
from transfers import transfer

AM_URL = "http://127.0.0.1"
SS_URL = "http://127.0.0.1:8000"
USER = "demo"
API_KEY = "1c34274c0df0bca7edf9831dd838b4a6345ac2ef"
SS_USER = "test"
SS_KEY = "7016762e174c940df304e8343c659af5005b4d6b"

TS_LOCATION_UUID = "2a3d8d39-9cee-495e-b7ee-5e629254934d"
PATH_PREFIX = b"SampleTransfers"
DEPTH = 1
COMPLETED = set()
FILES = False


class TestAutomateTransfers(unittest.TestCase):
    def setUp(self):
        models.init_session(databasefile=":memory:")

        # Setup some data to be used for test_call_start_transfer_endpoint(..)
        # and def test_call_start_transfer(..).
        transfers_dir = (
            "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers"
        )
        Result = collections.namedtuple(
            "Result", "transfer_type target transfer_name transfer_abs_path"
        )
        self.start_tests = [
            Result(
                transfer_type="standard",
                target="standard_1",
                transfer_name="standard_1",
                transfer_abs_path=f"{transfers_dir}/standardTransfer/standard_1/",
            ),
            Result(
                transfer_type="standard",
                target="standard_1",
                transfer_name="standard_1_1",
                transfer_abs_path=f"{transfers_dir}/standardTransfer/standard_1_1/",
            ),
            Result(
                transfer_type="dspace",
                target="dspace_1.zip",
                transfer_name="dspace_1.zip",
                transfer_abs_path=f"{transfers_dir}/Dspace/dspace_1.zip",
            ),
            Result(
                transfer_type="dspace",
                target="dspace_1.zip",
                transfer_name="dspace_1_1.zip",
                transfer_abs_path=f"{transfers_dir}/Dspace/dspace_1_1.zip",
            ),
        ]

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "status": "USER_INPUT",
                        "name": "test1",
                        "microservice": "Approve standard transfer",
                        "directory": "test1",
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/standardTransfer/test1/",
                        "message": "Fetched status for dfc8cf5f-b5b1-408c-88b1-34215964e9d6 successfully.",
                        "type": "transfer",
                        "uuid": "dfc8cf5f-b5b1-408c-88b1-34215964e9d6",
                    },
                },
                spec=requests.Response,
            )
        ],
    )
    def test_get_status_transfer(self, _request):
        transfer_uuid = "dfc8cf5f-b5b1-408c-88b1-34215964e9d6"
        transfer_name = "test1"
        info = transfer.get_status(
            AM_URL, USER, API_KEY, SS_URL, SS_USER, SS_KEY, transfer_uuid, "transfer"
        )
        assert isinstance(info, dict)
        assert info["status"] == "USER_INPUT"
        assert info["type"] == "transfer"
        assert info["name"] == transfer_name
        assert info["uuid"] == transfer_uuid
        assert info["directory"] == transfer_name
        assert info["path"] == (
            "/var/archivematica/sharedDirectory/"
            "watchedDirectories/activeTransfers/"
            "standardTransfer/test1/"
        )

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "status": "COMPLETE",
                        "name": "test1",
                        "sip_uuid": "f2248e2a-b593-43db-b60c-fa8513021785",
                        "microservice": "Move to SIP creation directory for completed transfers",
                        "directory": "test1-dfc8cf5f-b5b1-408c-88b1-34215964e9d6",
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/SIPCreation/completedTransfers/test1-dfc8cf5f-b5b1-408c-88b1-34215964e9d6/",
                        "message": "Fetched status for dfc8cf5f-b5b1-408c-88b1-34215964e9d6 successfully.",
                        "type": "transfer",
                        "uuid": "dfc8cf5f-b5b1-408c-88b1-34215964e9d6",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "status": "USER_INPUT",
                        "name": "test1",
                        "microservice": "Normalize",
                        "directory": "test1-f2248e2a-b593-43db-b60c-fa8513021785",
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/workFlowDecisions/selectFormatIDToolIngest/test1-f2248e2a-b593-43db-b60c-fa8513021785/",
                        "message": "Fetched status for f2248e2a-b593-43db-b60c-fa8513021785 successfully.",
                        "type": "SIP",
                        "uuid": "f2248e2a-b593-43db-b60c-fa8513021785",
                    },
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_status_transfer_to_ingest(self, _request):
        # Reference values
        transfer_uuid = "dfc8cf5f-b5b1-408c-88b1-34215964e9d6"
        unit_name = "test1"
        sip_uuid = "f2248e2a-b593-43db-b60c-fa8513021785"
        # Setup transfer in DB
        models._update_unit(
            uuid=transfer_uuid,
            path=b"/foo",
            unit_type="transfer",
            status="PROCESSING",
            current=True,
        )
        # Run test
        info = transfer.get_status(
            AM_URL, USER, API_KEY, SS_URL, SS_USER, SS_KEY, transfer_uuid, "transfer"
        )
        # Verify
        assert isinstance(info, dict)
        assert info["status"] == "USER_INPUT"
        assert info["type"] == "SIP"
        assert info["name"] == unit_name
        assert info["uuid"] == sip_uuid
        assert info["directory"] == unit_name + "-" + sip_uuid
        assert info["path"] == (
            "/var/archivematica/sharedDirectory/"
            "watchedDirectories/workFlowDecisions/"
            "selectFormatIDToolIngest/"
            "test1-f2248e2a-b593-43db-b60c-fa8513021785/"
        )

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "status": "USER_INPUT",
                        "name": "test1",
                        "microservice": "Normalize",
                        "directory": "test1-f2248e2a-b593-43db-b60c-fa8513021785",
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/workFlowDecisions/selectFormatIDToolIngest/test1-f2248e2a-b593-43db-b60c-fa8513021785/",
                        "message": "Fetched status for f2248e2a-b593-43db-b60c-fa8513021785 successfully.",
                        "type": "SIP",
                        "uuid": "f2248e2a-b593-43db-b60c-fa8513021785",
                    },
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_status_ingest(self, _request):
        sip_uuid = "f2248e2a-b593-43db-b60c-fa8513021785"
        sip_name = "test1"
        info = transfer.get_status(
            AM_URL, USER, API_KEY, SS_URL, SS_USER, SS_KEY, sip_uuid, "ingest"
        )
        assert isinstance(info, dict)
        assert info["status"] == "USER_INPUT"
        assert info["type"] == "SIP"
        assert info["name"] == sip_name
        assert info["uuid"] == sip_uuid
        assert info["directory"] == sip_name + "-" + sip_uuid
        assert info["path"] == (
            "/var/archivematica/sharedDirectory/"
            "watchedDirectories/workFlowDecisions/"
            "selectFormatIDToolIngest/"
            "test1-f2248e2a-b593-43db-b60c-fa8513021785/"
        )

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 400,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "ok": False,
                    "reason": "BAD REQUEST",
                },
                spec=requests.Response,
            )
        ],
    )
    def test_get_status_no_unit(self, _request):
        transfer_uuid = "deadc0de-c0de-c0de-c0de-deadc0dec0de"
        info = transfer.get_status(
            AM_URL, USER, API_KEY, SS_URL, SS_USER, SS_KEY, transfer_uuid, "transfer"
        )
        self.assertEqual(info, errors.error_lookup(errors.ERR_INVALID_RESPONSE))

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 404,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "text/html; charset=utf-8"}
                    ),
                    "ok": False,
                    "reason": "NOT FOUND",
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_status_not_json(self, _request):
        transfer_uuid = "dfc8cf5f-b5b1-408c-88b1-34215964e9d6"
        info = transfer.get_status(
            AM_URL, USER, API_KEY, SS_URL, SS_USER, SS_KEY, transfer_uuid, "transfer"
        )
        self.assertEqual(info, errors.error_lookup(errors.ERR_INVALID_RESPONSE))

    def test_get_accession_id_no_script(self):
        accession_id = transfer.get_accession_id(os.path.curdir)
        self.assertEqual(accession_id, None)

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"directories": ["QmFnVHJhbnNmZXI="]},
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_first_run(self, _request):
        # All default values
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            TS_LOCATION_UUID,
            PATH_PREFIX,
            DEPTH,
            COMPLETED,
            FILES,
        )
        # Verify
        self.assertEqual(path, b"SampleTransfers/BagTransfer")

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"directories": ["Q1NWbWV0YWRhdGE="]},
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_existing_set(self, _request):
        # Set completed set
        completed = {b"SampleTransfers/BagTransfer"}
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            TS_LOCATION_UUID,
            PATH_PREFIX,
            DEPTH,
            completed,
            FILES,
        )
        # Verify
        self.assertEqual(path, b"SampleTransfers/CSVmetadata")

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"directories": ["QmFnVHJhbnNmZXI="]},
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"directories": ["ZGF0YQ=="]},
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_depth(self, _request):
        # Set depth
        depth = 2
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            TS_LOCATION_UUID,
            PATH_PREFIX,
            depth,
            COMPLETED,
            FILES,
        )
        # Verify
        self.assertEqual(path, b"SampleTransfers/BagTransfer/data")

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"directories": ["T1BGIGZvcm1hdC1jb3JwdXM="]},
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_no_prefix(self, _request):
        # Set no prefix
        path_prefix = b""
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            TS_LOCATION_UUID,
            path_prefix,
            DEPTH,
            COMPLETED,
            FILES,
        )
        # Verify
        self.assertEqual(path, b"OPF format-corpus")

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"directories": []},
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_all_complete(self, _request):
        # Set completed set to be all elements
        completed = {
            b"SampleTransfers/BagTransfer",
            b"SampleTransfers/CSVmetadata",
            b"SampleTransfers/DigitizationOutput",
            b"SampleTransfers/DSpaceExport",
            b"SampleTransfers/Images",
            b"SampleTransfers/ISODiskImage",
            b"SampleTransfers/Multimedia",
            b"SampleTransfers/OCRImage",
            b"SampleTransfers/OfficeDocs",
            b"SampleTransfers/RawCameraImages",
            b"SampleTransfers/structMapSample",
        }
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            TS_LOCATION_UUID,
            PATH_PREFIX,
            DEPTH,
            completed,
            FILES,
        )
        # Verify
        self.assertEqual(path, None)

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 404,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "text/html; charset=utf-8"}
                    ),
                    "ok": False,
                    "reason": "NOT FOUND",
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_bad_source(self, _request):
        # Set bad TS Location UUID
        ts_location_uuid = "badd8d39-9cee-495e-b7ee-5e6292549bad"
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            ts_location_uuid,
            PATH_PREFIX,
            DEPTH,
            COMPLETED,
            FILES,
        )
        # Verify
        self.assertEqual(path, None)

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {"entries": ["QmFnVHJhbnNmZXIuemlw"]},
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_files(self, _request):
        # See files
        files = True
        completed = {b"SampleTransfers/BagTransfer"}
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            SS_USER,
            SS_KEY,
            TS_LOCATION_UUID,
            PATH_PREFIX,
            DEPTH,
            completed,
            files,
        )
        # Verify
        self.assertEqual(path, b"SampleTransfers/BagTransfer.zip")

    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 401,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "text/html; charset=utf-8"}
                    ),
                    "ok": False,
                    "reason": "UNAUTHORIZED",
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_get_next_transfer_failed_auth(self, _request):
        # All default values
        ss_user = "demo"
        ss_key = "dne"
        # Test
        path = transfer.get_next_transfer(
            SS_URL,
            ss_user,
            ss_key,
            TS_LOCATION_UUID,
            PATH_PREFIX,
            DEPTH,
            COMPLETED,
            FILES,
        )
        # Verify.
        self.assertEqual(path, None)

    @mock.patch("time.sleep")
    @mock.patch(
        "requests.request",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Fetched unapproved transfers successfully.",
                        "results": [
                            {
                                "directory": "unzipped_bag_1",
                                "type": "unzipped bag",
                                "uuid": "8779909c-20e8-4471-beb2-c45591b7abb0",
                            },
                            {
                                "directory": "dspace_1",
                                "type": "dspace",
                                "uuid": "f25c71e6-1f1e-4e69-bf57-580a64d4e051",
                            },
                            {
                                "directory": "standard_1",
                                "type": "standard",
                                "uuid": "0d16e57f-df1b-4a66-a93c-989f0dc9f16f",
                            },
                        ],
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Approval successful.",
                        "uuid": "8779909c-20e8-4471-beb2-c45591b7abb0",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Fetched unapproved transfers successfully.",
                        "results": [
                            {
                                "directory": "dspace_1",
                                "type": "dspace",
                                "uuid": "f25c71e6-1f1e-4e69-bf57-580a64d4e051",
                            },
                            {
                                "directory": "standard_1",
                                "type": "standard",
                                "uuid": "0d16e57f-df1b-4a66-a93c-989f0dc9f16f",
                            },
                        ],
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Approval successful.",
                        "uuid": "f25c71e6-1f1e-4e69-bf57-580a64d4e051",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Fetched unapproved transfers successfully.",
                        "results": [
                            {
                                "directory": "standard_1",
                                "type": "standard",
                                "uuid": "0d16e57f-df1b-4a66-a93c-989f0dc9f16f",
                            },
                            {
                                "directory": "2",
                                "type": "dspace",
                                "uuid": "47908337-3134-4871-8f41-a9d7d500c2e0",
                            },
                        ],
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Approval successful.",
                        "uuid": "0d16e57f-df1b-4a66-a93c-989f0dc9f16f",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "message": "Fetched unapproved transfers successfully.",
                        "results": [
                            {
                                "directory": "transfer_1",
                                "type": "dspace",
                                "uuid": "47908337-3134-4871-8f41-a9d7d500c2e0",
                            }
                        ],
                    },
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_approve_transfer(self, _request, _sleep):
        """Test the process of approving transfers and make sure that the
        outcome is as expected.
        """
        Result = collections.namedtuple("Result", "dirname expected")
        approve_tests = [
            Result(
                dirname="unzipped_bag_1",
                expected="8779909c-20e8-4471-beb2-c45591b7abb0",
            ),
            Result(dirname="dspace_1", expected="f25c71e6-1f1e-4e69-bf57-580a64d4e051"),
            Result(
                dirname="standard_1", expected="0d16e57f-df1b-4a66-a93c-989f0dc9f16f"
            ),
            Result(dirname="dirname_four", expected=None),
        ]
        for test in approve_tests:
            res = transfer.approve_transfer(test.dirname, AM_URL, API_KEY, USER)
            assert res == test.expected

    @mock.patch(
        "requests.post",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/standardTransfer/standard_1/",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/standardTransfer/standard_1_1/",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/Dspace/dspace_1.zip",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/Dspace/dspace_1_1.zip",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_call_start_transfer_endpoint(self, _request):
        """Archivematica will rename a transfer if it is already trying to
        start one with an identical name. In the tests below, we observe (and
        test) this behavior when there is an identical name for a transfer
        twice, across two transfer types. We also make sure that the transfer
        path is preserved. This path is used in pre-transfer scripts to enable
        the automation tools to create manifests, perform arrangement tasks, or
        manipulate content prior to the transfer being approved.
        """
        for test in self.start_tests:
            transfer_name, transfer_abs_path = transfer.call_start_transfer_endpoint(
                am_url=AM_URL,
                am_user=USER,
                am_api_key=API_KEY,
                target=test.target.encode(),
                transfer_type=test.transfer_type.encode(),
                accession=test.transfer_name.encode(),
                ts_location_uuid=TS_LOCATION_UUID,
            )
            assert transfer_name == test.transfer_name
            assert transfer_abs_path == test.transfer_abs_path

    @mock.patch(
        "transfers.transfer.approve_transfer",
        return_value="4bd2006a-1178-4695-9463-5c72eec6257a",
    )
    @mock.patch(
        "requests.post",
        side_effect=[
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/standardTransfer/standard_1/",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/standardTransfer/standard_1_1/",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/Dspace/dspace_1.zip",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
            mock.Mock(
                **{
                    "status_code": 200,
                    "headers": requests.structures.CaseInsensitiveDict(
                        {"Content-Type": "application/json"}
                    ),
                    "json.return_value": {
                        "path": "/var/archivematica/sharedDirectory/watchedDirectories/activeTransfers/Dspace/dspace_1_1.zip",
                        "message": "Copy successful.",
                    },
                },
                spec=requests.Response,
            ),
        ],
    )
    def test_call_start_transfer(self, _request, _approve_transfer):
        """Provide an integration test as best as we can for the
        transfer.start_transfer function where the returned values are crucial
        to the automation of Archivematica work-flows. The test reuses the
        test_call_start_transfer_endpoint.yaml fixtures as this function is
        crucial to what eventual gets stored in the model and we can test this
        more realistically by using it instead of mocking it.
        """
        returned_uuid = "4bd2006a-1178-4695-9463-5c72eec6257a"
        for test in self.start_tests:
            models.init_session(databasefile=":memory:")
            with mock.patch(
                "transfers.transfer.get_next_transfer"
            ) as mock_get_next_transfer:
                mock_get_next_transfer.return_value = test.target.encode()
                res = transfer.call_start_transfer_endpoint(
                    am_url=AM_URL,
                    am_user=USER,
                    am_api_key=API_KEY,
                    target=test.target.encode(),
                    transfer_type=test.transfer_type.encode(),
                    accession=test.transfer_name.encode(),
                    ts_location_uuid=TS_LOCATION_UUID,
                )
                result_encoded = (res[0], res[1].encode())
                with mock.patch(
                    "transfers.transfer.call_start_transfer_endpoint"
                ) as mock_call_start_transfer_endpoint:
                    mock_call_start_transfer_endpoint.return_value = result_encoded
                    new_transfer = transfer.start_transfer(
                        ss_url="http://127.0.0.1:62081",
                        ss_user="test",
                        ss_api_key="test",
                        ts_location_uuid=None,
                        ts_path="",
                        depth="test",
                        am_url="http://127.0.0.1:62090",
                        am_user="test",
                        am_api_key="test",
                        transfer_type="standard",
                        see_files=False,
                        config_file="config.cfg",
                    )
                    assert new_transfer.path.decode() == test.target
                    assert new_transfer.uuid == returned_uuid
                    assert new_transfer.current is True
                    assert new_transfer.unit_type == "transfer"
                    # Make a secondary call to the database to see if we can
                    # retrieve our information. Obviously this should not have
                    # changed since we wrote it to memory.
                    unit = models.retrieve_unit_by_type_and_uuid(
                        returned_uuid, "transfer"
                    )
                    assert unit.uuid == returned_uuid
                    assert unit.current is True
                    assert unit.unit_type == "transfer"
