#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    A py.test plugin which helps testing Flask applications.

    :copyright: (c) by Vital Kudzelka
    :license: MIT
"""
import pytest

from flask import json
from werkzeug import cached_property

from .fixtures import (
    client, config, accept_json, accept_jsonp, accept_any, accept_mimetype,
    client_class, live_server
)


def pytest_addoption(parser):
    group = parser.getgroup('flask')
    group.addoption('--liveserver-port',
        type=int, metavar='port', default=None,
        help="port uses to run live server when 'live_server' fixture "
             "is applyed."
    )


class JSONResponse(object):
    """Mixin with testing helper methods for JSON responses."""

    @cached_property
    def json(self):
        """Try to deserialize response data (a string containing a valid JSON
        document) to a Python object by passing it to the underlying
        :mod:`flask.json` module.
        """
        return json.loads(self.data)


def _make_test_response_class(response_class):
    """Extends the response class with special attribute to test JSON
    responses. Don't override user-defined `json` attribute if any.

    :param response_class: An original response class.
    """
    if 'json' in response_class.__dict__:
        return response_class

    return type(str(JSONResponse), (response_class, JSONResponse), {})


@pytest.fixture(autouse=True)
def _monkeypatch_response_class(request, monkeypatch):
    """Set custom response class before test suite and restore the original
    after. Custom response has `json` property to easily test JSON responses::

        @app.route('/ping')
        def ping():
            return jsonify(ping='pong')

        def test_json(client):
            res = client.get(url_for('ping'))
            assert res.json == {'ping': 'pong'}

    """
    if 'app' not in request.fixturenames:
        return

    app = request.getfuncargvalue('app')
    monkeypatch.setattr(app, 'response_class',
                        _make_test_response_class(app.response_class))


@pytest.fixture(autouse=True)
def _push_application_context(request):
    """During tests execution application has pushed context, e.g. `url_for`,
    `session`, etc. can be used in tests as is::

        def test_app(app, client):
            assert client.get(url_for('myview')).status_code == 200

    """
    if 'app' not in request.fixturenames:
        return

    app = request.getfuncargvalue('app')
    ctx = app.test_request_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)


@pytest.fixture(autouse=True)
def _configure_application(request):
    """Use `pytest.mark.app` decorator to pass options to your application
    factory::

        @pytest.mark.app(debug=False)
        def test_something(app):
            assert not app.debug, 'the application works not in debug mode!'

    """
    if 'app' not in request.fixturenames:
        return

    app = request.getfuncargvalue('app')
    options = request.keywords.get('app', None)
    if options:
        for key, value in options.kwargs.items():
            app.config[key.upper()] = value


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'app(options): pass options to your application factory')
