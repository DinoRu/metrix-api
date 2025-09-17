from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime, timedelta
from app.models.outbox import Outbox
import logging
import json

logger = logging.getLogger(__name__)


class OutboxService:
	def __init__(self, session: AsyncSession):
		self.session = session

	async def add_to_outbox(
			self,
			entity_type: str,
			entity_id: str,
			operation: str,
			payload: dict,
			max_retries: int = 5
	) -> Outbox:
		"""Add an item to the outbox for processing"""
		async with self.session as db:
			outbox_item = Outbox(
				entity_type=entity_type,
				entity_id=entity_id,
				operation=operation,
				payload=payload,
				max_retries=max_retries,
				status="pending"
			)
			db.add(outbox_item)
			await db.commit()
			await db.refresh(outbox_item)

			logger.info(f"Added to outbox: {entity_type}/{entity_id} - {operation}")
			return outbox_item

	async def get_pending_items(
			self,
			limit: int = 100,
			entity_type: Optional[str] = None
	) -> List[Outbox]:
		"""Get pending items from outbox"""
		async with self.session as db:
			query = select(Outbox).where(
				and_(
					Outbox.status == "pending",
					Outbox.retry_count < Outbox.max_retries,
					Outbox.scheduled_at <= datetime.utcnow()
				)
			)

			if entity_type:
				query = query.where(Outbox.entity_type == entity_type)

			query = query.order_by(Outbox.scheduled_at).limit(limit)

			result = await db.execute(query)
			return result.scalars().all()

	async def mark_as_processed(self, outbox_id: str):
		"""Mark an outbox item as processed"""
		async with self.session as db:
			await db.execute(
				update(Outbox)
				.where(Outbox.id == outbox_id)
				.values(
					status="processed",
					processed_at=datetime.utcnow()
				)
			)
			await db.commit()
			logger.info(f"Outbox item {outbox_id} marked as processed")

	async def mark_as_failed(
			self,
			outbox_id: str,
			error_message: str,
			retry_delay_minutes: int = None
	):
		"""Mark an outbox item as failed and schedule retry"""
		async with self.session as db:
			result = await db.execute(
				select(Outbox).where(Outbox.id == outbox_id)
			)
			outbox_item = result.scalar_one_or_none()

			if not outbox_item:
				return

			outbox_item.retry_count += 1
			outbox_item.error_message = error_message

			if outbox_item.retry_count >= outbox_item.max_retries:
				outbox_item.status = "failed"
				logger.error(f"Outbox item {outbox_id} permanently failed after {outbox_item.retry_count} retries")
			else:
				# Exponential backoff
				if retry_delay_minutes is None:
					retry_delay_minutes = min(2 ** outbox_item.retry_count, 60)

				outbox_item.scheduled_at = datetime.utcnow() + timedelta(minutes=retry_delay_minutes)
				logger.info(f"Outbox item {outbox_id} scheduled for retry #{outbox_item.retry_count} at {outbox_item.scheduled_at}")

			await db.commit()

	async def cleanup_old_items(self, days: int = 30):
		"""Clean up old processed items"""
		cutoff_date = datetime.utcnow() - timedelta(days=days)

		async with self.session as db:
			result = await db.execute(
				select(Outbox).where(
					and_(
						Outbox.status.in_(["processed", "failed"]),
						Outbox.created_at < cutoff_date
					)
				)
			)

			items_to_delete = result.scalars().all()
			for item in items_to_delete:
				await db.delete(item)

			await db.commit()

			if items_to_delete:
				logger.info(f"Cleaned up {len(items_to_delete)} old outbox items")
