"""Unit tests for webhook_dispatcher.

`WebhookDispatcher.dispatch_event` is the inbound half of the webhook system:
when a job changes state it queries the user's registered webhooks (GSI
`UserIdIndex`, filtered to `active = true`), keeps only the ones subscribed to
the fired event type, and enqueues one SQS message per webhook in the exact
shape the delivery Lambda (`webhook_delivery_handler`) consumes. A silent
regression here is a reliability/contract problem: a subscribed webhook that
never fires (the user is blind to job completion), an inactive/foreign webhook
that fires anyway (notifications leak), or a message whose field names drift
from what the delivery handler reads (`webhook_url`, `webhook_secret`,
`payload`, ...), which would break every delivery downstream.

Characterization only: no source change. The webhook query runs against the
moto `SnowscrapeWebhooks-test` table created by the conftest `dynamodb_client`
fixture; `sqs_client.send_message` is replaced with a Mock so the message shape
and per-message failure handling can be asserted without a real queue. The
module binds `webhooks_table` / `webhook_queue_url` / `sqs_client` at import
time from `os.environ`, so it is reloaded inside the active moto context.
"""
import importlib
import json
from unittest.mock import Mock, patch

import pytest


WEBHOOKS_TABLE = 'SnowscrapeWebhooks-test'


@pytest.fixture
def dispatcher(dynamodb_client):
	"""Reload webhook_dispatcher inside moto and stub its SQS client.

	`dynamodb_client` sets the env + creates the webhooks table; reloading
	rebinds the module's `webhooks_table` to THIS test's moto backend. The
	module-level `sqs_client` is replaced with a Mock so sends are captured
	(and can be made to fail) without touching a real queue.
	"""
	import webhook_dispatcher as module
	importlib.reload(module)
	module.sqs_client = Mock()
	return module


def _add_webhook(dynamodb, *, webhook_id, user_id='user-1', url=None,
				events=('job.completed',), active=True, secret=None, job_id=None):
	"""Insert a webhook row into the moto webhooks table."""
	item = {
		'webhook_id': webhook_id,
		'user_id': user_id,
		'url': url if url is not None else f'https://example.com/hooks/{webhook_id}',
		'events': list(events),
		'active': active,
	}
	if secret is not None:
		item['secret'] = secret
	if job_id is not None:
		item['job_id'] = job_id
	dynamodb.Table(WEBHOOKS_TABLE).put_item(Item=item)
	return item


def _sent_bodies(module):
	"""Parse every MessageBody passed to the stubbed send_message."""
	return [
		json.loads(call.kwargs['MessageBody'])
		for call in module.sqs_client.send_message.call_args_list
	]


# ─── dispatch_event: matching + count ────────────────────────────────────────

def test_single_matching_webhook_returns_one_and_sends(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {'event': 'job.completed'})
	assert n == 1
	assert dispatcher.sqs_client.send_message.call_count == 1


def test_no_webhooks_for_user_returns_zero(dispatcher, dynamodb_client):
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 0
	dispatcher.sqs_client.send_message.assert_not_called()


def test_webhook_not_subscribed_to_event_is_filtered(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.failed'])
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 0
	dispatcher.sqs_client.send_message.assert_not_called()


def test_webhook_with_no_events_is_filtered(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=[])
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 0


def test_inactive_webhook_excluded_by_query_filter(dispatcher, dynamodb_client):
	# active=False is filtered out at the DynamoDB query (FilterExpression),
	# so it never reaches the event-subscription filter.
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'], active=False)
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 0
	dispatcher.sqs_client.send_message.assert_not_called()


def test_only_subscribed_of_many_are_counted(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	_add_webhook(dynamodb_client, webhook_id='wh-2', events=['job.failed'])
	_add_webhook(dynamodb_client, webhook_id='wh-3', events=['job.completed', 'job.started'])
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 2
	assert dispatcher.sqs_client.send_message.call_count == 2


def test_other_users_webhook_not_dispatched(dispatcher, dynamodb_client):
	# The GSI query is keyed on the passed user_id; another user's active,
	# subscribed webhook must not be selected.
	_add_webhook(dynamodb_client, webhook_id='wh-other', user_id='user-2', events=['job.completed'])
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 0


def test_subscribed_webhook_with_foreign_job_id_still_fires(dispatcher, dynamodb_client):
	# Characterization: the first match clause (event_type in events) ignores
	# job_id, so a webhook carrying a DIFFERENT job_id but subscribed to the
	# event is STILL dispatched. job_id is not an effective scoping filter.
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'], job_id='some-other-job')
	n = dispatcher.WebhookDispatcher.dispatch_event(
		'job.completed', 'job-1', 'user-1', {})
	assert n == 1


# ─── dispatch_event: SQS message shape ───────────────────────────────────────

def test_message_shape_matches_delivery_handler_contract(dispatcher, dynamodb_client):
	_add_webhook(
		dynamodb_client, webhook_id='wh-1',
		url='https://hooks.example.com/x', events=['job.completed'], secret='shh')
	payload = {'event': 'job.completed', 'job_id': 'job-1', 'foo': 'bar'}
	dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', payload)

	(body,) = _sent_bodies(dispatcher)
	assert body['webhook_id'] == 'wh-1'
	assert body['webhook_url'] == 'https://hooks.example.com/x'
	assert body['webhook_secret'] == 'shh'
	assert body['event_type'] == 'job.completed'
	assert body['job_id'] == 'job-1'
	assert body['user_id'] == 'user-1'
	assert body['payload'] == payload
	assert body['delivery_id']  # non-empty uuid


def test_missing_secret_serializes_as_empty_string(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])  # no secret
	dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	(body,) = _sent_bodies(dispatcher)
	assert body['webhook_secret'] == ''


def test_send_message_targets_configured_queue_url(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	_, kwargs = dispatcher.sqs_client.send_message.call_args
	# Pin both the module global AND the literal conftest URL, so the test
	# fails if either the source stops reading the global or the global drifts
	# from the SQS_WEBHOOK_QUEUE_URL env it is bound from.
	assert kwargs['QueueUrl'] == dispatcher.webhook_queue_url
	assert kwargs['QueueUrl'] == 'https://sqs.us-east-2.amazonaws.com/test/SnowscrapeWebhookQueue-test'


def test_delivery_id_in_body_matches_a_uuid_per_webhook(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	_add_webhook(dynamodb_client, webhook_id='wh-2', events=['job.completed'])
	dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	bodies = _sent_bodies(dispatcher)
	ids = {b['delivery_id'] for b in bodies}
	assert len(ids) == 2  # distinct delivery id per webhook


# ─── dispatch_event: FIFO vs standard queue ──────────────────────────────────

def test_standard_queue_sets_group_and_dedup_none(dispatcher, dynamodb_client):
	# The conftest queue URL does not end in .fifo, so both FIFO-only params
	# are passed as None.
	assert not dispatcher.webhook_queue_url.endswith('.fifo')
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	_, kwargs = dispatcher.sqs_client.send_message.call_args
	assert kwargs['MessageGroupId'] is None
	assert kwargs['MessageDeduplicationId'] is None


def test_fifo_queue_sets_group_to_webhook_id_and_dedup_to_delivery_id(dispatcher, dynamodb_client):
	dispatcher.webhook_queue_url = dispatcher.webhook_queue_url + '.fifo'
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	_, kwargs = dispatcher.sqs_client.send_message.call_args
	body = json.loads(kwargs['MessageBody'])
	assert kwargs['MessageGroupId'] == 'wh-1'
	assert kwargs['MessageDeduplicationId'] == body['delivery_id']


# ─── dispatch_event: failure isolation ───────────────────────────────────────

def test_single_send_failure_is_isolated_and_others_counted(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	_add_webhook(dynamodb_client, webhook_id='wh-2', events=['job.completed'])
	# First send raises, second succeeds; the raise is caught per-iteration.
	dispatcher.sqs_client.send_message.side_effect = [RuntimeError('sqs down'), None]
	n = dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	assert n == 1  # only the successful send is counted
	assert dispatcher.sqs_client.send_message.call_count == 2


def test_all_sends_failing_returns_zero(dispatcher, dynamodb_client):
	_add_webhook(dynamodb_client, webhook_id='wh-1', events=['job.completed'])
	_add_webhook(dynamodb_client, webhook_id='wh-2', events=['job.completed'])
	dispatcher.sqs_client.send_message.side_effect = RuntimeError('sqs down')
	n = dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	assert n == 0


def test_query_error_returns_zero_and_no_send(dispatcher, dynamodb_client):
	# An exception raised by the webhooks query is swallowed by the outer
	# try/except, which returns 0 rather than propagating into the job flow.
	with patch.object(dispatcher.webhooks_table, 'query', side_effect=RuntimeError('ddb down')):
		n = dispatcher.WebhookDispatcher.dispatch_event('job.completed', 'job-1', 'user-1', {})
	assert n == 0
	dispatcher.sqs_client.send_message.assert_not_called()


# ─── convenience wrappers: payload shape + delegation ────────────────────────

def _patched_dispatch(dispatcher):
	"""Patch dispatch_event to a Mock returning a sentinel count."""
	return patch.object(
		dispatcher.WebhookDispatcher, 'dispatch_event', return_value=7)


def test_dispatch_job_created_payload_and_delegation(dispatcher):
	job_data = {'name': 'My Job', 'created_at': '2026-06-14T00:00:00Z',
				'source': 'https://example.com', 'link_count': 5}
	with _patched_dispatch(dispatcher) as m:
		out = dispatcher.WebhookDispatcher.dispatch_job_created('job-1', 'user-1', job_data)
	assert out == 7
	args, _ = m.call_args
	event_type, job_id, user_id, payload = args
	assert event_type == 'job.created'
	assert job_id == 'job-1' and user_id == 'user-1'
	assert payload == {
		'event': 'job.created', 'job_id': 'job-1', 'job_name': 'My Job',
		'created_at': '2026-06-14T00:00:00Z', 'source': 'https://example.com',
		'link_count': 5,
	}


def test_dispatch_job_created_link_count_defaults_to_zero(dispatcher):
	with _patched_dispatch(dispatcher) as m:
		dispatcher.WebhookDispatcher.dispatch_job_created('job-1', 'user-1', {'name': 'J'})
	payload = m.call_args[0][3]
	assert payload['link_count'] == 0
	assert payload['created_at'] is None  # job_data.get('created_at')


def test_dispatch_job_started_payload(dispatcher):
	job_data = {'name': 'J', 'last_run': '2026-06-14T01:00:00Z', 'link_count': 3}
	with _patched_dispatch(dispatcher) as m:
		dispatcher.WebhookDispatcher.dispatch_job_started('job-1', 'user-1', job_data)
	event_type, _, _, payload = m.call_args[0]
	assert event_type == 'job.started'
	assert payload['event'] == 'job.started'
	assert payload['started_at'] == '2026-06-14T01:00:00Z'  # from last_run
	assert payload['link_count'] == 3


def test_dispatch_job_completed_payload_carries_summary_and_s3_key(dispatcher):
	job_data = {'name': 'J', 'last_run': '2026-06-14T02:00:00Z', 'results_s3_key': 'k/results.json'}
	summary = {'urls': 10, 'success': 9}
	with _patched_dispatch(dispatcher) as m:
		dispatcher.WebhookDispatcher.dispatch_job_completed('job-1', 'user-1', job_data, summary)
	event_type, _, _, payload = m.call_args[0]
	assert event_type == 'job.completed'
	assert payload['completed_at'] == '2026-06-14T02:00:00Z'  # from last_run
	assert payload['results_s3_key'] == 'k/results.json'
	assert payload['summary'] == summary


def test_dispatch_job_failed_payload_carries_error(dispatcher):
	job_data = {'name': 'J', 'last_run': '2026-06-14T03:00:00Z'}
	with _patched_dispatch(dispatcher) as m:
		dispatcher.WebhookDispatcher.dispatch_job_failed('job-1', 'user-1', job_data, 'boom')
	event_type, _, _, payload = m.call_args[0]
	assert event_type == 'job.failed'
	assert payload['failed_at'] == '2026-06-14T03:00:00Z'  # from last_run
	assert payload['error'] == 'boom'


def test_dispatch_job_cancelled_payload(dispatcher):
	job_data = {'name': 'J', 'last_run': '2026-06-14T04:00:00Z'}
	with _patched_dispatch(dispatcher) as m:
		dispatcher.WebhookDispatcher.dispatch_job_cancelled('job-1', 'user-1', job_data)
	event_type, _, _, payload = m.call_args[0]
	assert event_type == 'job.cancelled'
	assert payload['cancelled_at'] == '2026-06-14T04:00:00Z'  # from last_run
	assert set(payload) == {'event', 'job_id', 'job_name', 'cancelled_at'}


def test_convenience_wrappers_return_dispatch_event_count(dispatcher):
	# Every wrapper returns dispatch_event's value verbatim (the webhook count).
	with _patched_dispatch(dispatcher):
		assert dispatcher.WebhookDispatcher.dispatch_job_started('j', 'u', {}) == 7
		assert dispatcher.WebhookDispatcher.dispatch_job_failed('j', 'u', {}, 'e') == 7
		assert dispatcher.WebhookDispatcher.dispatch_job_cancelled('j', 'u', {}) == 7


def test_job_name_falls_back_to_none_when_absent(dispatcher):
	# job_data without a name -> job_name is None (job_data.get('name')).
	with _patched_dispatch(dispatcher) as m:
		dispatcher.WebhookDispatcher.dispatch_job_completed('job-1', 'user-1', {}, {})
	payload = m.call_args[0][3]
	assert payload['job_name'] is None
