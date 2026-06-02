"""Verify Docs export fan-out runs on job completion."""
import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def set_env(mock_env_vars):
	"""Ensure required env vars are set for job_manager imports."""
	pass


@patch("job_manager.DocsExporter")
@patch("job_manager.WebhookDispatcher")
def test_completion_dispatches_to_docs_exporter(mock_webhook, mock_docs):
	"""Job with export_destination_ids dispatches to both webhook + docs."""
	from job_manager import _on_job_completed

	job_data = {
		"job_id": "job-1",
		"user_id": "user_abc",
		"name": "Test Job",
		"export_destination_ids": ["d-1", "d-2"],
		"results_s3_key": "results/job-1.json",
	}

	_on_job_completed(job_data=job_data, results_summary={"rows": 5})

	mock_webhook.dispatch_job_completed.assert_called_once()
	mock_docs.dispatch_job_completed.assert_called_once_with(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=["d-1", "d-2"],
		results_s3_key="results/job-1.json",
		job_data=job_data,
	)


@patch("job_manager.DocsExporter")
@patch("job_manager.WebhookDispatcher")
def test_completion_skips_docs_when_no_destinations(mock_webhook, mock_docs):
	from job_manager import _on_job_completed

	job_data = {
		"job_id": "job-1",
		"user_id": "user_abc",
		"name": "Test Job",
		"results_s3_key": "results/job-1.json",
	}

	_on_job_completed(job_data=job_data, results_summary={"rows": 5})

	mock_docs.dispatch_job_completed.assert_not_called()
	mock_webhook.dispatch_job_completed.assert_called_once()
