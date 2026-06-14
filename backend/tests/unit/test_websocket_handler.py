"""Unit tests for websocket_handler.

`websocket_handler` is the real-time layer behind the API Gateway WebSocket API.
It is a security/reliability boundary with three distinct surfaces, none of which
had dedicated coverage before this suite:

  * connection lifecycle ($connect stores a PENDING/unauthenticated row with a
    short 5-minute TTL; $disconnect deletes it),
  * the $default message router, which MUST refuse every action except
    `authenticate` until the connection is authenticated (an auth bypass here
    would let an unauthenticated socket subscribe to and receive another user's
    job stream), and the authenticate/auth handlers that upgrade the row and
    extend the TTL to 24h,
  * the outbound fan-out (`send_to_connection`, `broadcast_to_channel`,
    `broadcast_to_user`, `notify_job_status_change`) including stale-connection
    (GoneException) cleanup.

A silent regression is either a security hole (the auth gate weakening, the
short pending TTL growing) or a reliability bug (a subscribed client never
notified, or a stale connection never reaped so broadcasts pile up errors).

Characterization only: no source change. The module reads `CONNECTIONS_TABLE`
from `os.environ` at import and caches the boto3 table on the module-level
`connections_table` global, so it is reloaded inside the active moto context by
the `ws` fixture (which also creates the connections table). The API Gateway
Management API client is faked (moto's support is thin and the source only ever
calls `post_to_connection` and catches `client.exceptions.GoneException`), and
`validate_clerk_token` is patched per test.
"""
import importlib
import json
import time
from unittest.mock import Mock, patch

import pytest


CONNECTIONS_TABLE = 'SnowscrapeConnections-test'


# ─── fakes ───────────────────────────────────────────────────────────────────

class _GoneException(Exception):
	"""Stand-in for botocore's apigatewaymanagementapi GoneException."""


class _FakeApiGwClient:
	"""Minimal apigatewaymanagementapi double.

	`post_to_connection` records the (connection_id, decoded JSON) it is handed
	unless the id is registered to raise GoneException (a stale connection) or a
	generic error. `exceptions.GoneException` is the SAME class instances are
	raised from, so the source's `except client.exceptions.GoneException` matches.
	"""

	def __init__(self, gone=None, errors=None):
		self.exceptions = Mock()
		self.exceptions.GoneException = _GoneException
		self.sent = []
		self._gone = set(gone or ())
		self._errors = set(errors or ())

	def post_to_connection(self, ConnectionId, Data):
		if ConnectionId in self._gone:
			raise _GoneException('410')
		if ConnectionId in self._errors:
			raise RuntimeError('send blew up')
		self.sent.append((ConnectionId, json.loads(Data.decode('utf-8'))))
		return {'ok': True}


# ─── fixtures + helpers ────────────────────────────────────────────────────────

@pytest.fixture
def ws(dynamodb_client):
	"""Reload websocket_handler with a moto-backed connections table.

	`dynamodb_client` opens the moto context and creates the standard tables;
	here we additionally create the connections table (the conftest does not),
	point `DYNAMODB_CONNECTIONS_TABLE` at it, and reload so the module rebinds
	`CONNECTIONS_TABLE` and clears its cached `connections_table` global.
	"""
	import os
	dynamodb_client.create_table(
		TableName=CONNECTIONS_TABLE,
		KeySchema=[{'AttributeName': 'connection_id', 'KeyType': 'HASH'}],
		AttributeDefinitions=[{'AttributeName': 'connection_id', 'AttributeType': 'S'}],
		BillingMode='PAY_PER_REQUEST',
	)
	os.environ['DYNAMODB_CONNECTIONS_TABLE'] = CONNECTIONS_TABLE
	import websocket_handler as module
	importlib.reload(module)
	yield module
	os.environ.pop('DYNAMODB_CONNECTIONS_TABLE', None)


@pytest.fixture
def table(dynamodb_client):
	"""The moto connections Table resource for direct assertions/seeding."""
	return dynamodb_client.Table(CONNECTIONS_TABLE)


def _event(connection_id='conn-1', body=None, domain='ws.example.com', stage='dev'):
	"""Build a minimal WebSocket Lambda event."""
	evt = {'requestContext': {'connectionId': connection_id,
							   'domainName': domain, 'stage': stage}}
	if body is not None:
		evt['body'] = body if isinstance(body, str) else json.dumps(body)
	return evt


def _seed(table, connection_id='conn-1', *, user_id='user-1', authenticated=True,
		  subscriptions=None):
	"""Insert a connection row. subscriptions, if given, is stored as a DDB set."""
	item = {'connection_id': connection_id, 'user_id': user_id,
			'authenticated': authenticated, 'connected_at': 1000}
	if subscriptions:
		item['subscriptions'] = set(subscriptions)
	table.put_item(Item=item)


def _get(table, connection_id='conn-1'):
	return table.get_item(Key={'connection_id': connection_id}).get('Item')


# ─── ws_connect_handler ────────────────────────────────────────────────────────

def test_connect_missing_connection_id_returns_400(ws):
	resp = ws.ws_connect_handler({'requestContext': {}}, None)
	assert resp['statusCode'] == 400


def test_connect_stores_pending_unauthenticated_row(ws, table):
	resp = ws.ws_connect_handler(_event('conn-new'), None)
	assert resp['statusCode'] == 200
	item = _get(table, 'conn-new')
	assert item is not None
	assert item['user_id'] == '__unauthenticated__'
	assert item['authenticated'] is False
	# `subscriptions` is intentionally NOT seeded so handle_subscribe's
	# `ADD :{set}` can create the string set (see the source note). A seeded
	# empty list would make the first subscribe 500.
	assert 'subscriptions' not in item


def test_connect_sets_short_5_minute_ttl(ws, table):
	"""Pending connections get a deliberately short 300s TTL until authenticated."""
	before = int(time.time())
	ws.ws_connect_handler(_event('conn-ttl'), None)
	item = _get(table, 'conn-ttl')
	# ttl == connected_at + 300; connected_at was stamped at/after `before`.
	assert int(item['ttl']) - int(item['connected_at']) == 300
	assert int(item['ttl']) >= before + 300


def test_connect_put_failure_returns_500(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.put_item.side_effect = RuntimeError('ddb down')
		resp = ws.ws_connect_handler(_event('conn-x'), None)
	assert resp['statusCode'] == 500


# ─── ws_disconnect_handler ─────────────────────────────────────────────────────

def test_disconnect_missing_connection_id_returns_400(ws):
	resp = ws.ws_disconnect_handler({'requestContext': {}}, None)
	assert resp['statusCode'] == 400


def test_disconnect_deletes_the_row(ws, table):
	_seed(table, 'conn-bye')
	assert _get(table, 'conn-bye') is not None
	resp = ws.ws_disconnect_handler(_event('conn-bye'), None)
	assert resp['statusCode'] == 200
	assert _get(table, 'conn-bye') is None


def test_disconnect_delete_failure_returns_500(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.delete_item.side_effect = RuntimeError('ddb down')
		resp = ws.ws_disconnect_handler(_event('conn-x'), None)
	assert resp['statusCode'] == 500


# ─── is_connection_authenticated ───────────────────────────────────────────────

def test_is_authenticated_true_when_flag_set(ws, table):
	_seed(table, 'conn-a', authenticated=True)
	assert ws.is_connection_authenticated('conn-a') is True


def test_is_authenticated_false_when_flag_false(ws, table):
	_seed(table, 'conn-a', authenticated=False)
	assert ws.is_connection_authenticated('conn-a') is False


def test_is_authenticated_false_when_no_item(ws):
	assert ws.is_connection_authenticated('conn-missing') is False


def test_is_authenticated_false_when_attribute_absent(ws, table):
	"""A row lacking `authenticated` defaults to unauthenticated (.get default False)."""
	table.put_item(Item={'connection_id': 'conn-noattr', 'user_id': 'u'})
	assert ws.is_connection_authenticated('conn-noattr') is False


def test_is_authenticated_false_on_ddb_error(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.get_item.side_effect = RuntimeError('ddb down')
		assert ws.is_connection_authenticated('conn-a') is False


# ─── ws_default_handler: routing + auth gate ───────────────────────────────────

def test_default_missing_connection_id_returns_400(ws):
	assert ws.ws_default_handler({'requestContext': {}}, None)['statusCode'] == 400


def test_default_invalid_json_returns_400(ws):
	resp = ws.ws_default_handler(_event('conn-1', body='{not json'), None)
	assert resp['statusCode'] == 400


def test_default_authenticate_action_dispatches_to_handle_authenticate(ws):
	sentinel = {'statusCode': 200, 'body': 'auth-handled'}
	with patch.object(ws, 'handle_authenticate', return_value=sentinel) as ha:
		resp = ws.ws_default_handler(
			_event('conn-1', body={'action': 'authenticate', 'token': 't'}), None)
	ha.assert_called_once()
	assert ha.call_args.args[0] == 'conn-1'
	assert resp is sentinel


def test_default_unauthenticated_non_authenticate_is_rejected_before_routing(ws, table):
	"""The core security gate: an unauthenticated socket cannot subscribe."""
	_seed(table, 'conn-1', authenticated=False)
	with patch.object(ws, 'handle_subscribe') as hs, \
		 patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.ws_default_handler(
			_event('conn-1', body={'type': 'subscribe', 'channel': 'jobs:all'}), None)
	hs.assert_not_called()
	assert client.sent[0][1] == {
		'type': 'auth_error',
		'message': 'Not authenticated. Send an authenticate action first.',
	}


def test_default_authenticated_auth_type_dispatches_to_handle_auth(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	with patch.object(ws, 'handle_auth', return_value={'statusCode': 200}) as h:
		ws.ws_default_handler(_event('conn-1', body={'type': 'auth', 'token': 't'}), None)
	h.assert_called_once()


def test_default_authenticated_subscribe_dispatches_to_handle_subscribe(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	with patch.object(ws, 'handle_subscribe', return_value={'statusCode': 200}) as h:
		ws.ws_default_handler(
			_event('conn-1', body={'type': 'subscribe', 'channel': 'c'}), None)
	h.assert_called_once()


def test_default_authenticated_unsubscribe_dispatches_to_handle_unsubscribe(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	with patch.object(ws, 'handle_unsubscribe', return_value={'statusCode': 200}) as h:
		ws.ws_default_handler(
			_event('conn-1', body={'type': 'unsubscribe', 'channel': 'c'}), None)
	h.assert_called_once()


def test_default_authenticated_ping_responds_pong(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	with patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.ws_default_handler(_event('conn-1', body={'type': 'ping'}), None)
	assert client.sent[0][1] == {'type': 'pong'}


def test_default_authenticated_unknown_type_responds_error(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	with patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.ws_default_handler(_event('conn-1', body={'type': 'bogus'}), None)
	assert client.sent[0][1]['type'] == 'error'
	assert 'bogus' in client.sent[0][1]['message']


def test_default_unexpected_error_returns_500(ws):
	with patch.object(ws, 'is_connection_authenticated', side_effect=RuntimeError('x')):
		resp = ws.ws_default_handler(
			_event('conn-1', body={'type': 'ping'}), None)
	assert resp['statusCode'] == 500


# ─── handle_authenticate ───────────────────────────────────────────────────────

def test_authenticate_no_token_returns_auth_error(ws):
	with patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_authenticate('conn-1', {}, _event('conn-1'))
	assert client.sent[0][1] == {'type': 'auth_error', 'message': 'No token provided'}


def test_authenticate_valid_token_upgrades_row_and_extends_ttl(ws, table):
	_seed(table, 'conn-1', user_id='__unauthenticated__', authenticated=False)
	before = int(time.time())
	with patch.object(ws, 'validate_clerk_token', return_value={'sub': 'user-42'}), \
		 patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_authenticate('conn-1', {'token': 'good'}, _event('conn-1'))
	item = _get(table, 'conn-1')
	assert item['authenticated'] is True
	assert item['user_id'] == 'user-42'
	assert int(item['ttl']) >= before + 86400  # extended to ~24h
	assert client.sent[0][1] == {'type': 'auth_success', 'user_id': 'user-42'}


def test_authenticate_token_without_sub_returns_auth_error(ws, table):
	_seed(table, 'conn-1', authenticated=False)
	with patch.object(ws, 'validate_clerk_token', return_value={}), \
		 patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_authenticate('conn-1', {'token': 'good'}, _event('conn-1'))
	assert client.sent[0][1] == {'type': 'auth_error', 'message': 'Invalid token: no user ID'}
	# The row is NOT upgraded.
	assert _get(table, 'conn-1')['authenticated'] is False


def test_authenticate_invalid_token_returns_auth_error_with_message(ws, table):
	_seed(table, 'conn-1', authenticated=False)
	with patch.object(ws, 'validate_clerk_token', side_effect=ValueError('bad token')), \
		 patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_authenticate('conn-1', {'token': 'bad'}, _event('conn-1'))
	assert client.sent[0][1] == {'type': 'auth_error', 'message': 'bad token'}
	assert _get(table, 'conn-1')['authenticated'] is False


# ─── handle_auth (token refresh on an already-authenticated socket) ────────────

def test_auth_refresh_no_token_returns_auth_error(ws):
	with patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_auth('conn-1', {}, _event('conn-1'))
	assert client.sent[0][1] == {'type': 'auth_error', 'message': 'No token provided'}


def test_auth_refresh_valid_updates_user_and_ttl(ws, table):
	_seed(table, 'conn-1', user_id='user-old', authenticated=True)
	before = int(time.time())
	with patch.object(ws, 'validate_clerk_token', return_value={'sub': 'user-new'}), \
		 patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_auth('conn-1', {'token': 'good'}, _event('conn-1'))
	item = _get(table, 'conn-1')
	assert item['user_id'] == 'user-new'
	assert int(item['ttl']) >= before + 86400
	assert client.sent[0][1] == {'type': 'auth_success', 'user_id': 'user-new'}


def test_auth_refresh_invalid_token_returns_auth_error(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	with patch.object(ws, 'validate_clerk_token', side_effect=ValueError('nope')), \
		 patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		ws.handle_auth('conn-1', {'token': 'bad'}, _event('conn-1'))
	assert client.sent[0][1] == {'type': 'auth_error', 'message': 'nope'}


# ─── handle_subscribe / handle_unsubscribe ─────────────────────────────────────

def test_subscribe_no_channel_returns_400(ws):
	assert ws.handle_subscribe('conn-1', {})['statusCode'] == 400


def test_subscribe_adds_channel_to_subscription_set(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	resp = ws.handle_subscribe('conn-1', {'channel': 'job:123'})
	assert resp['statusCode'] == 200
	assert _get(table, 'conn-1')['subscriptions'] == {'job:123'}


def test_subscribe_after_real_connect_lifecycle_succeeds(ws, table):
	"""End-to-end: a freshly $connect-ed socket can subscribe.

	Regression guard for the list-vs-set bug: `ws_connect_handler` must NOT seed
	`subscriptions` as an attribute that `ADD :{set}` cannot extend, or the first
	subscribe after connect fails with a DynamoDB ValidationException (500).
	"""
	ws.ws_connect_handler(_event('conn-real'), None)
	resp = ws.handle_subscribe('conn-real', {'channel': 'jobs:all'})
	assert resp['statusCode'] == 200
	assert _get(table, 'conn-real')['subscriptions'] == {'jobs:all'}


def test_subscribe_accumulates_multiple_channels(ws, table):
	_seed(table, 'conn-1', authenticated=True)
	ws.handle_subscribe('conn-1', {'channel': 'jobs:all'})
	ws.handle_subscribe('conn-1', {'channel': 'job:7'})
	assert _get(table, 'conn-1')['subscriptions'] == {'jobs:all', 'job:7'}


def test_subscribe_ddb_error_returns_500(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.update_item.side_effect = RuntimeError('ddb down')
		assert ws.handle_subscribe('conn-1', {'channel': 'c'})['statusCode'] == 500


def test_unsubscribe_no_channel_returns_400(ws):
	assert ws.handle_unsubscribe('conn-1', {})['statusCode'] == 400


def test_unsubscribe_removes_only_that_channel(ws, table):
	_seed(table, 'conn-1', authenticated=True, subscriptions={'jobs:all', 'job:7'})
	resp = ws.handle_unsubscribe('conn-1', {'channel': 'job:7'})
	assert resp['statusCode'] == 200
	assert _get(table, 'conn-1')['subscriptions'] == {'jobs:all'}


def test_unsubscribe_ddb_error_returns_500(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.update_item.side_effect = RuntimeError('ddb down')
		assert ws.handle_unsubscribe('conn-1', {'channel': 'c'})['statusCode'] == 500


# ─── send_to_connection ────────────────────────────────────────────────────────

def test_send_to_connection_posts_payload_and_returns_200(ws):
	with patch.object(ws, 'get_api_gateway_client') as gc:
		client = _FakeApiGwClient()
		gc.return_value = client
		resp = ws.send_to_connection(_event('conn-1'), 'conn-1', {'type': 'pong'})
	assert resp['statusCode'] == 200
	assert client.sent == [('conn-1', {'type': 'pong'})]


def test_send_to_connection_gone_deletes_row_and_returns_410(ws, table):
	_seed(table, 'conn-gone')
	with patch.object(ws, 'get_api_gateway_client') as gc:
		gc.return_value = _FakeApiGwClient(gone={'conn-gone'})
		resp = ws.send_to_connection(_event('conn-gone'), 'conn-gone', {'type': 'x'})
	assert resp['statusCode'] == 410
	assert _get(table, 'conn-gone') is None  # stale connection reaped


def test_send_to_connection_generic_error_returns_500(ws):
	with patch.object(ws, 'get_api_gateway_client') as gc:
		gc.return_value = _FakeApiGwClient(errors={'conn-1'})
		resp = ws.send_to_connection(_event('conn-1'), 'conn-1', {'type': 'x'})
	assert resp['statusCode'] == 500


# ─── broadcast_to_channel ──────────────────────────────────────────────────────

def test_broadcast_to_channel_sends_to_all_subscribers(ws, table):
	_seed(table, 'c1', subscriptions={'jobs:all'})
	_seed(table, 'c2', subscriptions={'jobs:all'})
	_seed(table, 'c3', subscriptions={'job:other'})  # not subscribed
	client = _FakeApiGwClient()
	with patch.object(ws.boto3, 'client', return_value=client):
		ws.broadcast_to_channel('d', 's', 'jobs:all', {'type': 'job:status'})
	got = sorted(cid for cid, _ in client.sent)
	assert got == ['c1', 'c2']


def test_broadcast_to_channel_excludes_named_connection(ws, table):
	_seed(table, 'c1', subscriptions={'jobs:all'})
	_seed(table, 'c2', subscriptions={'jobs:all'})
	client = _FakeApiGwClient()
	with patch.object(ws.boto3, 'client', return_value=client):
		ws.broadcast_to_channel('d', 's', 'jobs:all', {'x': 1}, exclude_connection='c1')
	assert [cid for cid, _ in client.sent] == ['c2']


def test_broadcast_to_channel_reaps_stale_connections(ws, table):
	_seed(table, 'c1', subscriptions={'jobs:all'})
	_seed(table, 'c2', subscriptions={'jobs:all'})
	client = _FakeApiGwClient(gone={'c1'})
	with patch.object(ws.boto3, 'client', return_value=client):
		ws.broadcast_to_channel('d', 's', 'jobs:all', {'x': 1})
	assert _get(table, 'c1') is None      # gone -> deleted
	assert _get(table, 'c2') is not None   # healthy -> kept


def test_broadcast_to_channel_swallows_scan_error(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.scan.side_effect = RuntimeError('scan failed')
		# Must not raise.
		ws.broadcast_to_channel('d', 's', 'jobs:all', {'x': 1})


# ─── broadcast_to_user ─────────────────────────────────────────────────────────

def test_broadcast_to_user_sends_to_all_user_connections(ws, table):
	_seed(table, 'c1', user_id='user-1')
	_seed(table, 'c2', user_id='user-1')
	_seed(table, 'c3', user_id='user-2')
	client = _FakeApiGwClient()
	with patch.object(ws.boto3, 'client', return_value=client):
		ws.broadcast_to_user('d', 's', 'user-1', {'x': 1})
	assert sorted(cid for cid, _ in client.sent) == ['c1', 'c2']


def test_broadcast_to_user_reaps_stale_connections(ws, table):
	_seed(table, 'c1', user_id='user-1')
	_seed(table, 'c2', user_id='user-1')
	client = _FakeApiGwClient(gone={'c1'})
	with patch.object(ws.boto3, 'client', return_value=client):
		ws.broadcast_to_user('d', 's', 'user-1', {'x': 1})
	assert _get(table, 'c1') is None
	assert _get(table, 'c2') is not None


def test_broadcast_to_user_swallows_scan_error(ws):
	with patch.object(ws, 'get_connections_table') as gct:
		gct.return_value.scan.side_effect = RuntimeError('scan failed')
		ws.broadcast_to_user('d', 's', 'user-1', {'x': 1})


# ─── notify_job_status_change ──────────────────────────────────────────────────

def test_notify_no_ws_domain_is_a_noop(ws, monkeypatch):
	monkeypatch.delenv('WS_API_DOMAIN', raising=False)
	with patch.object(ws, 'broadcast_to_channel') as bc, \
		 patch.object(ws, 'broadcast_to_user') as bu:
		ws.notify_job_status_change('job-1', 'user-1', 'COMPLETED')
	bc.assert_not_called()
	bu.assert_not_called()


def test_notify_broadcasts_to_job_channel_all_channel_and_user(ws, monkeypatch):
	monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
	monkeypatch.setenv('WS_API_STAGE', 'prod')
	with patch.object(ws, 'broadcast_to_channel') as bc, \
		 patch.object(ws, 'broadcast_to_user') as bu:
		ws.notify_job_status_change('job-1', 'user-1', 'COMPLETED', {'progress': 100})

	channels = [call.args[2] for call in bc.call_args_list]
	assert channels == ['job:job-1', 'jobs:all']
	# Message shape: type job:status, data merges job_id/status + extra job_data.
	msg = bc.call_args_list[0].args[3]
	assert msg['type'] == 'job:status'
	assert msg['data'] == {'job_id': 'job-1', 'status': 'COMPLETED', 'progress': 100}
	# User broadcast uses the configured domain + stage and the same message.
	bu.assert_called_once()
	assert bu.call_args.args[0] == 'ws.example.com'
	assert bu.call_args.args[1] == 'prod'
	assert bu.call_args.args[2] == 'user-1'
	assert bu.call_args.args[3] == msg
