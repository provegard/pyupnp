# -*- coding: utf-8 -*-

from nose.tools import eq_

import pyupnp.upnp
import xml.etree.ElementTree as ET
from pyupnp.upnp import *
from pyupnp.ms import *
from routes.middleware import RoutesMiddleware
from webtest import TestApp
from pkg_resources import resource_filename
from StringIO import StringIO

class FakeUpnpBase(object):
    def __init__(self, callable):
        self.callable = callable

    def __call__(self, environ, start_response):
        input = environ['wsgi.input']
        environ['upnp.body'] = input.read(UpnpBase.SOAP_BODY_MAX)
        return self.callable(environ, start_response)

class TestMediaServer(object):

    @classmethod
    def setupAll(cls):
        cls.udn = 'uuid:00000000-0000-0000-001122334455'
        server_name = 'OS/1.0 UPnP/1.0 pyupnp/1.0'

        dd = resource_filename(upnp.__name__, 'xml/ms.xml')
        resource_filename(upnp.__name__, 'xml/cds.xml')
        resource_filename(upnp.__name__, 'xml/cms.xml')
        content_dir = resource_filename(__name__, "content")

        device = UpnpDevice(cls.udn, dd, FakeUpnpBase(MediaServer(content_dir)))
        base = UpnpBase()
        sid = "urn:upnp-org:serviceId:ContentDirectory"
        cls.app = TestApp(RoutesMiddleware(device, base.mapper))

    def _createBrowseMessage(self, requestedCount):
        msg = SoapMessage("urn:schemas-upnp-org:service:ContentDirectory:1",
                          "Browse")
        msg.set_arg("ObjectID", "0")
        msg.set_arg("BrowseFlag", "BrowseDirectChildren")
        msg.set_arg("Filter", "*")
        msg.set_arg("StartingIndex", "0")
        msg.set_arg("RequestedCount", requestedCount)
        msg.set_arg("SortCriteria", "")
        return msg

    def _postSoapRequest(self, sid, msg):
        app = TestMediaServer.app
        path = "/upnp/%s/%s/soap" % (TestMediaServer.udn, sid)
        res = app.post(path, msg.tostring(),
                       headers={ "SOAPAction": msg.get_header() },
                       content_type='text/xml; charset="utf-8"')
        return res


    def test_that_Browse_response_includes_the_correct_number_of_items(self):
        msg = self._createBrowseMessage("1")
        sid = "urn:upnp-org:serviceId:ContentDirectory"
        res = self._postSoapRequest(sid, msg)
        eq_(200, res.status_code)
        soap = SoapMessage.parse(StringIO(res.text), name="BrowseResponse")
        result = soap.get_arg("Result")
        didl = ET.fromstring(result)
        items = didl.findall("{urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/}item")
        eq_(1, len(items))

