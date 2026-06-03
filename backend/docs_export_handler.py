"""SQS-triggered Lambda that writes scrape results to Google Docs."""
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict

import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from connection_pool import get_table
from docs_formatter import format_rows_to_docs_requests
from google_oauth import decrypt_refresh_token, refresh_access_token
from logger import get_logger

logger = get_logger(__name__)

# one_doc_per_row creates one Google Doc per result row. Cap the count so a large
# job cannot spawn thousands of Drive/Docs API calls (rate limits) or blow the
# Lambda's 120s timeout. Comfortably covers the small-N "one doc per person" use
# case; larger runs should use new_doc_per_run or split the job.
MAX_DOCS_PER_ROW_RUN = 25


def _build_drive_service(access_token: str):
	creds = Credentials(token=access_token)
	return build("drive", "v3", credentials=creds, cache_discovery=False)


def _build_docs_service(access_token: str):
	creds = Credentials(token=access_token)
	return build("docs", "v1", credentials=creds, cache_discovery=False)


def _read_results(s3_key: str):
	s3 = boto3.client("s3")
	bucket = os.environ["S3_BUCKET"]
	obj = s3.get_object(Bucket=bucket, Key=s3_key)
	data = json.loads(obj["Body"].read())
	return data if isinstance(data, list) else data.get("rows", [])


def _render_doc_title(naming_template: str, job_name: str) -> str:
	date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
	return (
		naming_template
		.replace("{{job_name}}", job_name or "")
		.replace("{{date}}", date_str)
	)


def _log_export(export_id: str, status: str, *, doc_id="", doc_url="", doc_count=0, error=""):
	table = get_table(os.environ["DYNAMODB_DOCS_EXPORTS_TABLE"])
	table.put_item(Item={
		"export_id": export_id,
		"status": status,
		"doc_id": doc_id,
		"doc_url": doc_url,
		"doc_count": doc_count,
		"error": error[:1000],
		"timestamp": int(time.time()),
		"created_at": datetime.now(timezone.utc).isoformat(),
		"ttl": int(time.time()) + 60 * 60 * 24 * 90,
	})


def _row_label(row: Dict, index: int) -> str:
	"""Human-readable suffix for a per-row doc title."""
	return str(row.get("title") or row.get("url") or f"Row {index + 1}")


def _create_doc(drive, docs, *, folder_id: str, title: str, rows, format_template: str):
	"""Create a Google Doc in folder_id and write the formatted rows. Returns (doc_id, doc_url)."""
	created = drive.files().create(
		body={
			"name": title,
			"mimeType": "application/vnd.google-apps.document",
			"parents": [folder_id],
		},
		fields="id, webViewLink",
	).execute()
	doc_id = created["id"]
	doc_url = created["webViewLink"]
	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template=format_template,
		title=title,
	)
	docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
	return doc_id, doc_url


def _process_one(message: Dict) -> None:
	export_id = message["export_id"]
	destination_id = message["destination_id"]
	user_id = message["user_id"]
	job_name = message.get("job_name", "")

	destinations = get_table(os.environ["DYNAMODB_EXPORT_DESTINATIONS_TABLE"])
	dest = destinations.get_item(Key={"destination_id": destination_id}).get("Item")
	if not dest or dest.get("user_id") != user_id:
		raise RuntimeError(f"Destination {destination_id} not found for user {user_id}")

	accounts = get_table(os.environ["DYNAMODB_GOOGLE_ACCOUNTS_TABLE"])
	account = accounts.get_item(Key={"user_id": user_id}).get("Item")
	if not account:
		raise RuntimeError(f"No Google account for user {user_id}")

	refresh_token = decrypt_refresh_token(account["refresh_token_ciphertext"])
	tokens = refresh_access_token(refresh_token=refresh_token)
	access_token = tokens["access_token"]

	rows = _read_results(message["results_s3_key"])
	base_title = _render_doc_title(dest["naming_template"], job_name)
	folder_id = dest["drive_folder_id"]
	format_template = dest["format_template"]
	mode = dest.get("mode", "new_doc_per_run")

	drive = _build_drive_service(access_token)
	docs = _build_docs_service(access_token)

	if mode == "one_doc_per_row":
		if len(rows) > MAX_DOCS_PER_ROW_RUN:
			raise RuntimeError(
				f"one_doc_per_row supports up to {MAX_DOCS_PER_ROW_RUN} rows; "
				f"this run had {len(rows)}. Use new_doc_per_run or split the job."
			)
		first_doc_id = ""
		first_doc_url = ""
		for i, row in enumerate(rows):
			row_title = f"{base_title} — {_row_label(row, i)}"
			doc_id, doc_url = _create_doc(
				drive, docs,
				folder_id=folder_id,
				title=row_title,
				rows=[row],
				format_template=format_template,
			)
			if not first_doc_id:
				first_doc_id, first_doc_url = doc_id, doc_url
		_log_export(
			export_id, "success",
			doc_id=first_doc_id, doc_url=first_doc_url, doc_count=len(rows),
		)
	else:
		doc_id, doc_url = _create_doc(
			drive, docs,
			folder_id=folder_id,
			title=base_title,
			rows=rows,
			format_template=format_template,
		)
		_log_export(export_id, "success", doc_id=doc_id, doc_url=doc_url, doc_count=1)


def docs_export_handler(event, context):
	"""SQS handler. Uses partial batch responses for retry."""
	failed: list = []
	for record in event.get("Records", []):
		message_id = record.get("messageId", "")
		try:
			message = json.loads(record["body"])
			_process_one(message)
		except Exception as e:
			logger.error("Docs export failed", error=str(e), message_id=message_id)
			try:
				body = json.loads(record.get("body") or "{}")
				_log_export(
					body.get("export_id", message_id),
					"failed",
					error=str(e),
				)
			except Exception:
				logger.error("Could not log failure", message_id=message_id)
			failed.append({"itemIdentifier": message_id})
	return {"batchItemFailures": failed}
