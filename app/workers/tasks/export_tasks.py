# =====================================
# api/app/workers/tasks/export_tasks.py
# =====================================
import asyncio
import logging
from functools import partial

from celery import current_task
from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services.export_service import ExportService
from app.models.task import TaskStatus, TaskResult
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
import io
import boto3
from app.config import settings
import uuid

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="export_readings_to_excel")
def export_readings_to_excel(
		self,
		start_date: str,
		end_date: str,
		user_id: str,
		include_photos: bool = True,
		format: str = "xlsx"
) -> Dict[str, Any]:
	"""
	Export readings to Excel/CSV in background
	"""
	task_id = self.request.id

	try:
		# Update task status
		current_task.update_state(
			state="PROCESSING",
			meta={
				"status": "Starting export...",
				"start_time": datetime.utcnow().isoformat()
			}
		)

		# Run async export
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(
			_export_readings_async(
				task_id=task_id,
				start_date=date.fromisoformat(start_date),
				end_date=date.fromisoformat(end_date),
				user_id=user_id,
				include_photos=include_photos,
				format=format,
				update_callback=partial(_update_export_progress, self)
			)
		)
		loop.close()

		return result

	except Exception as e:
		logger.error(f"Export task {task_id} failed: {str(e)}")
		current_task.update_state(
			state="FAILURE",
			meta={"error": str(e)}
		)
		raise


def _update_export_progress(task, status: str, percentage: int = 0):
	"""Update export progress"""
	task.update_state(
		state="PROCESSING",
		meta={
			"status": status,
			"percentage": percentage
		}
	)


async def _export_readings_async(
		task_id: str,
		start_date: date,
		end_date: date,
		user_id: str,
		include_photos: bool,
		format: str,
		update_callback
) -> Dict[str, Any]:
	"""Generate export file asynchronously"""

	async with AsyncSessionLocal() as db:
		try:
			# Save task record
			task_record = TaskResult(
				id=task_id,
				task_name="export_readings",
				user_id=user_id,
				status=TaskStatus.PROCESSING,
				started_at=datetime.utcnow(),
				params={
					"start_date": start_date.isoformat(),
					"end_date": end_date.isoformat(),
					"include_photos": include_photos,
					"format": format
				}
			)
			db.add(task_record)
			await db.commit()

			update_callback("Fetching readings...", 10)

			# Generate export
			export_service = ExportService(db)
			file_content = await export_service.export_readings(
				start_date=start_date,
				end_date=end_date,
				include_photos=include_photos,
				format=format,
				user_id=user_id,
				progress_callback=update_callback
			)

			update_callback("Uploading to storage...", 90)

			# Upload to S3
			s3_client = boto3.client(
				"s3",
				endpoint_url=settings.S3_ENDPOINT_URL,
				aws_access_key_id=settings.S3_ACCESS_KEY,
				aws_secret_access_key=settings.S3_SECRET_KEY,
			)

			file_name = f"exports/{user_id}/{uuid.uuid4()}.{format}"
			s3_client.upload_fileobj(
				file_content,
				settings.S3_BUCKET_NAME,
				file_name
			)

			# Generate download URL (valid for 7 days)
			download_url = s3_client.generate_presigned_url(
				"get_object",
				Params={
					"Bucket": settings.S3_BUCKET_NAME,
					"Key": file_name
				},
				ExpiresIn=7 * 24 * 3600
			)

			# Update task record
			task_record.status = TaskStatus.COMPLETED
			task_record.completed_at = datetime.utcnow()
			task_record.result = {
				"file_name": file_name,
				"download_url": download_url,
				"expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
			}
			await db.commit()

			update_callback("Export completed!", 100)

			return {
				"task_id": task_id,
				"status": "completed",
				"download_url": download_url,
				"file_name": file_name,
				"completed_at": datetime.utcnow().isoformat()
			}

		except Exception as e:
			task_record.status = TaskStatus.FAILED
			task_record.error_message = str(e)
			task_record.completed_at = datetime.utcnow()
			await db.commit()
			raise
