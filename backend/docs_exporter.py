"""Dispatcher that fans Docs export messages to SQS, mirroring webhook_dispatcher."""
import json
import os
import uuid
from typing import Dict, List

import boto3

from connection_pool import get_table
from logger import get_logger

logger = get_logger(__name__)


class DocsExporter:
	"""Dispatches Google Docs export messages to SQS for async delivery."""

	@staticmethod
	def dispatch_job_completed(
		job_id: str,
		user_id: str,
		destination_ids: List[str],
		results_s3_key: str,
		job_data: Dict,
	) -> int:
		"""Returns the number of export messages sent."""
		if not destination_ids:
			return 0

		table = get_table(os.environ["DYNAMODB_EXPORT_DESTINATIONS_TABLE"])
		sqs = boto3.client("sqs")
		queue_url = os.environ["SQS_DOCS_EXPORT_QUEUE_URL"]

		sent = 0
		for destination_id in destination_ids:
			item = table.get_item(Key={"destination_id": destination_id}).get("Item")
			if not item or item.get("user_id") != user_id:
				logger.warning(
					"Destination missing or owned by another user",
					destination_id=destination_id, user_id=user_id,
				)
				continue
			export_id = f"exp_{uuid.uuid4().hex[:16]}"
			message = {
				"export_id": export_id,
				"destination_id": destination_id,
				"job_id": job_id,
				"user_id": user_id,
				"results_s3_key": results_s3_key,
				"job_name": job_data.get("name", ""),
			}
			try:
				sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
				sent += 1
				logger.info(
					"Docs export dispatched",
					export_id=export_id, destination_id=destination_id, job_id=job_id,
				)
			except Exception as e:
				logger.error(
					"Failed to dispatch Docs export",
					export_id=export_id, destination_id=destination_id, error=str(e),
				)
		return sent
