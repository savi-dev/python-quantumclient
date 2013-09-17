# Copyright 2012 NEC Corporation
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

import copy
import httplib2
import json
import uuid

import mox
import testtools

from quantumclient import client
from quantumclient.common import exceptions


USERNAME = 'testuser'
TENANT_NAME = 'testtenant'
PASSWORD = 'password'
AUTH_URL = 'authurl'
ENDPOINT_URL = 'localurl'
TOKEN = 'tokentoken'
REGION = 'RegionTest'

KS_TOKEN_RESULT = {
    'access': {
        'token': {'id': TOKEN,
                  'expires': '2012-08-11T07:49:01Z',
                  'tenant': {'id': str(uuid.uuid1())}},
        'user': {'id': str(uuid.uuid1())},
        'serviceCatalog': [
            {'endpoints_links': [],
             'endpoints': [{'adminURL': ENDPOINT_URL,
                            'internalURL': ENDPOINT_URL,
                            'publicURL': ENDPOINT_URL,
                            'region': REGION}],
             'type': 'network',
             'name': 'Quantum Service'}
        ]
    }
}

ENDPOINTS_RESULT = {
    'endpoints': [{
        'type': 'network',
        'name': 'Quantum Service',
        'region': REGION,
        'adminURL': ENDPOINT_URL,
        'internalURL': ENDPOINT_URL,
        'publicURL': ENDPOINT_URL
    }]
}


class CLITestAuthKeystone(testtools.TestCase):

    def setUp(self):
        """Prepare the test environment."""
        super(CLITestAuthKeystone, self).setUp()
        self.mox = mox.Mox()
        self.client = client.HTTPClient(username=USERNAME,
                                        tenant_name=TENANT_NAME,
                                        password=PASSWORD,
                                        auth_url=AUTH_URL,
                                        region_name=REGION)
        self.addCleanup(self.mox.VerifyAll)
        self.addCleanup(self.mox.UnsetStubs)

    def test_get_token(self):
        self.mox.StubOutWithMock(self.client, "request")

        res200 = self.mox.CreateMock(httplib2.Response)
        res200.status = 200

        self.client.request(
            AUTH_URL + '/tokens', 'POST',
            body=mox.IsA(str), headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()

        self.client.do_request('/resource', 'GET')
        self.assertEqual(self.client.endpoint_url, ENDPOINT_URL)
        self.assertEqual(self.client.auth_token, TOKEN)

    def test_refresh_token(self):
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN
        self.client.endpoint_url = ENDPOINT_URL

        res200 = self.mox.CreateMock(httplib2.Response)
        res200.status = 200
        res401 = self.mox.CreateMock(httplib2.Response)
        res401.status = 401

        # If a token is expired, quantum server retruns 401
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res401, ''))
        self.client.request(
            AUTH_URL + '/tokens', 'POST',
            body=mox.IsA(str), headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')

    def test_get_endpoint_url(self):
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN

        res200 = self.mox.CreateMock(httplib2.Response)
        res200.status = 200

        self.client.request(
            mox.StrContains(AUTH_URL + '/tokens/%s/endpoints' % TOKEN), 'GET',
            headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(ENDPOINTS_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')

    def test_get_endpoint_url_other(self):
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='otherURL')
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN

        res200 = self.mox.CreateMock(httplib2.Response)
        res200.status = 200

        self.client.request(
            mox.StrContains(AUTH_URL + '/tokens/%s/endpoints' % TOKEN), 'GET',
            headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(ENDPOINTS_RESULT)))
        self.mox.ReplayAll()
        self.assertRaises(exceptions.EndpointTypeNotFound,
                          self.client.do_request,
                          '/resource',
                          'GET')

    def test_get_endpoint_url_failed(self):
        self.mox.StubOutWithMock(self.client, "request")

        self.client.auth_token = TOKEN

        res200 = self.mox.CreateMock(httplib2.Response)
        res200.status = 200
        res401 = self.mox.CreateMock(httplib2.Response)
        res401.status = 401

        self.client.request(
            mox.StrContains(AUTH_URL + '/tokens/%s/endpoints' % TOKEN), 'GET',
            headers=mox.IsA(dict)
        ).AndReturn((res401, ''))
        self.client.request(
            AUTH_URL + '/tokens', 'POST',
            body=mox.IsA(str), headers=mox.IsA(dict)
        ).AndReturn((res200, json.dumps(KS_TOKEN_RESULT)))
        self.client.request(
            mox.StrContains(ENDPOINT_URL + '/resource'), 'GET',
            headers=mox.ContainsKeyValue('X-Auth-Token', TOKEN)
        ).AndReturn((res200, ''))
        self.mox.ReplayAll()
        self.client.do_request('/resource', 'GET')

    def test_url_for(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)

        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        endpoints['publicURL'] = 'public'
        endpoints['internalURL'] = 'internal'
        endpoints['adminURL'] = 'admin'
        catalog = client.ServiceCatalog(resources)

        # endpoint_type not specified
        url = catalog.url_for(attr='region',
                              filter_value=REGION)
        self.assertEqual('public', url)

        # endpoint type specified (3 cases)
        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='adminURL')
        self.assertEqual('admin', url)

        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='publicURL')
        self.assertEqual('public', url)

        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='internalURL')
        self.assertEqual('internal', url)

        # endpoint_type requested does not exist.
        self.assertRaises(exceptions.EndpointTypeNotFound,
                          catalog.url_for,
                          attr='region',
                          filter_value=REGION,
                          endpoint_type='privateURL')

    # Test scenario with url_for when the service catalog only has publicURL.
    def test_url_for_only_public_url(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)
        catalog = client.ServiceCatalog(resources)

        # Remove endpoints from the catalog.
        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        del endpoints['internalURL']
        del endpoints['adminURL']
        endpoints['publicURL'] = 'public'

        # Use publicURL when specified explicitly.
        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='publicURL')
        self.assertEqual('public', url)

        # Use publicURL when specified explicitly.
        url = catalog.url_for(attr='region',
                              filter_value=REGION)
        self.assertEqual('public', url)

    # Test scenario with url_for when the service catalog only has adminURL.
    def test_url_for_only_admin_url(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)
        catalog = client.ServiceCatalog(resources)
        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        del endpoints['internalURL']
        del endpoints['publicURL']
        endpoints['adminURL'] = 'admin'

        # Use publicURL when specified explicitly.
        url = catalog.url_for(attr='region',
                              filter_value=REGION,
                              endpoint_type='adminURL')
        self.assertEqual('admin', url)

        # But not when nothing is specified.
        self.assertRaises(exceptions.EndpointTypeNotFound,
                          catalog.url_for,
                          attr='region',
                          filter_value=REGION)

    def test_endpoint_type(self):
        resources = copy.deepcopy(KS_TOKEN_RESULT)
        endpoints = resources['access']['serviceCatalog'][0]['endpoints'][0]
        endpoints['internalURL'] = 'internal'
        endpoints['adminURL'] = 'admin'
        endpoints['publicURL'] = 'public'

        # Test default behavior is to choose public.
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION)

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'public')

        # Test admin url
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='adminURL')

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'admin')

        # Test public url
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='publicURL')

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'public')

        # Test internal url
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='internalURL')

        self.client._extract_service_catalog(resources)
        self.assertEqual(self.client.endpoint_url, 'internal')

        # Test url that isn't found in the service catalog
        self.client = client.HTTPClient(
            username=USERNAME, tenant_name=TENANT_NAME, password=PASSWORD,
            auth_url=AUTH_URL, region_name=REGION, endpoint_type='privateURL')

        self.assertRaises(exceptions.EndpointTypeNotFound,
                          self.client._extract_service_catalog,
                          resources)
