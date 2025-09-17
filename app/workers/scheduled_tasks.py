import asyncio
import json
import uuid
from typing import Dict, Any

from celery.schedules import crontab
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.outbox import Outbox
from app.models.task import TaskResult, TaskStatus
from app.models.meter import Meter
from app.models.reading import Reading
from app.models.photo import Photo
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
	'process-outbox': {
		'task': 'app.workers.scheduled_tasks.process_outbox',
		'schedule': 300.0,  # Every 5 minutes
	},
	'cleanup-old-tasks': {
		'task': 'app.workers.scheduled_tasks.cleanup_old_tasks',
		'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
	},
	'generate-daily-report': {
		'task': 'app.workers.scheduled_tasks.generate_daily_report',
		'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM
	},
}


@celery_app.task(name="app.workers.scheduled_tasks.process_outbox")
def process_outbox():
	"""Process pending items in outbox"""
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	result = loop.run_until_complete(_process_outbox_async())
	loop.close()
	return result


async def _process_outbox_async():
	"""Process outbox items asynchronously"""
	processed = 0
	failed = 0

	async with AsyncSessionLocal() as db:
		# Get pending items
		result = await db.execute(
			select(Outbox)
			.where(
				Outbox.status == "pending",
				Outbox.retry_count < Outbox.max_retries,
				Outbox.scheduled_at <= datetime.utcnow()
			)
			.limit(100)
		)
		items = result.scalars().all()

		for item in items:
			try:
				# Process based on entity type
				if item.entity_type == "reading":
					await _sync_reading(item, db)
				elif item.entity_type == "photo":
					await _sync_photo(item, db)

				item.status = "processed"
				item.processed_at = datetime.utcnow()
				processed += 1

			except Exception as e:
				logger.error(f"Failed to process outbox item {item.id}: {e}")
				item.retry_count += 1
				item.error_message = str(e)

				if item.retry_count >= item.max_retries:
					item.status = "failed"
				else:
					# Exponential backoff
					item.scheduled_at = datetime.utcnow() + timedelta(
						minutes=2 ** item.retry_count
					)
				failed += 1

		await db.commit()

	logger.info(f"Outbox processing: {processed} succeeded, {failed} failed")
	return {"processed": processed, "failed": failed}


async def _sync_reading(item: Outbox, db: AsyncSession):
	"""Synchronize a reading item from outbox"""
	try:
		# Parse the payload
		payload = json.loads(item.payload) if isinstance(item.payload, str) else item.payload

		# Validate required fields
		required_fields = ["meter_id", "value", "reading_date"]
		missing_fields = [field for field in required_fields if field not in payload]
		if missing_fields:
			raise ValueError(f"Missing required fields: {missing_fields}")

		# Check if meter exists
		meter_result = await db.execute(
			select(Meter).where(Meter.id == payload["meter_id"])
		)
		meter = meter_result.scalar_one_or_none()
		if not meter:
			raise ValueError(f"Meter with ID {payload['meter_id']} not found")

		# Check for duplicate readings
		existing_reading = await db.execute(
			select(Reading).where(
				Reading.meter_id == payload["meter_id"],
				Reading.reading_date == payload["reading_date"]
			)
		)
		if existing_reading.scalar_one_or_none():
			logger.warning(f"Reading already exists for meter {payload['meter_id']} on {payload['reading_date']}")
			return

		# Create new reading
		reading_data = {
			"id": payload.get("id", str(uuid.uuid4())),
			"meter_id": payload["meter_id"],
			"value": float(payload["value"]),
			"reading_date": datetime.fromisoformat(payload["reading_date"]).date()
			if isinstance(payload["reading_date"], str)
			else payload["reading_date"],
			"created_at": datetime.utcnow(),
			"updated_at": datetime.utcnow()
		}

		# Add optional fields
		optional_fields = ["notes", "reader_id", "photo_url", "coordinates"]
		for field in optional_fields:
			if field in payload and payload[field] is not None:
				reading_data[field] = payload[field]

		reading = Reading(**reading_data)
		db.add(reading)
		await db.flush()

		logger.info(f"Successfully synced reading {reading.id} for meter {meter.meter_number}")

	except Exception as e:
		logger.error(f"Error syncing reading from outbox item {item.id}: {e}")
		raise


async def _sync_photo(item: Outbox, db: AsyncSession):
	"""Synchronize a photo item from outbox"""
	try:
		# Parse the payload
		payload = json.loads(item.payload) if isinstance(item.payload, str) else item.payload

		# Validate required fields
		required_fields = ["file_path", "entity_type", "entity_id"]
		missing_fields = [field for field in required_fields if field not in payload]
		if missing_fields:
			raise ValueError(f"Missing required fields: {missing_fields}")

		# Validate entity exists based on type
		if payload["entity_type"] == "reading":
			entity_result = await db.execute(
				select(Reading).where(Reading.id == payload["entity_id"])
			)
		elif payload["entity_type"] == "meter":
			entity_result = await db.execute(
				select(Meter).where(Meter.id == payload["entity_id"])
			)
		else:
			raise ValueError(f"Unsupported entity type: {payload['entity_type']}")

		entity = entity_result.scalar_one_or_none()
		if not entity:
			raise ValueError(f"Entity {payload['entity_type']} with ID {payload['entity_id']} not found")

		# Check for duplicate photos
		existing_photo = await db.execute(
			select(Photo).where(
				Photo.entity_type == payload["entity_type"],
				Photo.entity_id == payload["entity_id"],
				Photo.file_path == payload["file_path"]
			)
		)
		if existing_photo.scalar_one_or_none():
			logger.warning(f"Photo already exists for {payload['entity_type']} {payload['entity_id']}")
			return

		# Create new photo record
		photo_data = {
			"id": payload.get("id", str(uuid.uuid4())),
			"file_path": payload["file_path"],
			"entity_type": payload["entity_type"],
			"entity_id": payload["entity_id"],
			"created_at": datetime.utcnow(),
			"updated_at": datetime.utcnow()
		}

		# Add optional fields
		optional_fields = ["file_size", "mime_type", "description", "coordinates"]
		for field in optional_fields:
			if field in payload and payload[field] is not None:
				photo_data[field] = payload[field]

		photo = Photo(**photo_data)
		db.add(photo)
		await db.flush()

		logger.info(f"Successfully synced photo {photo.id} for {payload['entity_type']} {payload['entity_id']}")

	except Exception as e:
		logger.error(f"Error syncing photo from outbox item {item.id}: {e}")
		raise


@celery_app.task(name="app.workers.scheduled_tasks.cleanup_old_tasks")
def cleanup_old_tasks():
	"""Clean up old task results"""
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	result = loop.run_until_complete(_cleanup_old_tasks_async())
	loop.close()
	return result


async def _cleanup_old_tasks_async():
	"""Remove task results older than 30 days"""
	cutoff_date = datetime.utcnow() - timedelta(days=30)

	async with AsyncSessionLocal() as db:
		result = await db.execute(
			select(TaskResult)
			.where(
				TaskResult.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]),
				TaskResult.completed_at < cutoff_date
			)
		)
		tasks = result.scalars().all()

		count = len(tasks)
		for task in tasks:
			await db.delete(task)

		await db.commit()

	logger.info(f"Cleaned up {count} old task results")
	return {"deleted": count}


@celery_app.task(name="app.workers.scheduled_tasks.generate_daily_report")
def generate_daily_report():
	"""Generate daily report"""
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	result = loop.run_until_complete(_generate_daily_report_async())
	loop.close()
	return result


async def _generate_daily_report_async():
	"""Generate daily report asynchronously"""
	report_date = datetime.utcnow().date() - timedelta(days=1)  # Yesterday's report

	async with AsyncSessionLocal() as db:
		try:
			# Get statistics for yesterday
			stats = {}

			# Total meters
			meter_count = await db.execute(select(func.count(Meter.id)))
			stats["total_meters"] = meter_count.scalar()

			# Readings count for yesterday
			readings_count = await db.execute(
				select(func.count(Reading.id))
				.where(Reading.reading_date == report_date)
			)
			stats["daily_readings"] = readings_count.scalar()

			# Failed outbox items
			failed_outbox = await db.execute(
				select(func.count(Outbox.id))
				.where(
					Outbox.status == "failed",
					func.date(Outbox.created_at) == report_date
				)
			)
			stats["failed_sync_items"] = failed_outbox.scalar()

			# Completed tasks
			completed_tasks = await db.execute(
				select(func.count(TaskResult.id))
				.where(
					TaskResult.status == TaskStatus.COMPLETED,
					func.date(TaskResult.completed_at) == report_date
				)
			)
			stats["completed_tasks"] = completed_tasks.scalar()

			# Failed tasks
			failed_tasks = await db.execute(
				select(func.count(TaskResult.id))
				.where(
					TaskResult.status == TaskStatus.FAILED,
					func.date(TaskResult.completed_at) == report_date
				)
			)
			stats["failed_tasks"] = failed_tasks.scalar()

			# Log the report
			logger.info(f"Daily Report for {report_date}: {stats}")

			# Here you could also:
			# - Send email report
			# - Store in database
			# - Send to monitoring system
			# - Generate charts/graphs

			return {
				"report_date": report_date.isoformat(),
				"statistics": stats,
				"generated_at": datetime.utcnow().isoformat()
			}

		except Exception as e:
			logger.error(f"Failed to generate daily report: {e}")
			raise