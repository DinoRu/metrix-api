from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models.reading import Reading
from app.models.meter import Meter
from app.schemas.reading import ReadingCreate
import logging

logger = logging.getLogger(__name__)


class ReadingService:
	def __init__(self, session: AsyncSession):
		self.session = session

	async def sync_readings(
			self,
			readings: List[ReadingCreate],
			user_id: str,
			device_id: str
	) -> Dict[str, Any]:
		"""Sync multiple readings from mobile device"""
		synced = 0
		failed = 0
		conflicts = []

		async with self.session as db:
			for reading_data in readings:
				try:
					# Check for existing reading with same client_id
					if reading_data.client_id:
						existing = await db.execute(
							select(Reading).where(Reading.client_id == reading_data.client_id)
						)
						existing_reading = existing.scalar_one_or_none()

						if existing_reading:
							# Conflict resolution: Last-write-wins
							if reading_data.reading_date > existing_reading.reading_date:
								# Update existing reading
								for field, value in reading_data.model_dump().items():
									if field != 'client_id':
										setattr(existing_reading, field, value)
								existing_reading.sync_status = "synced"
								synced += 1
							else:
								conflicts.append({
									"client_id": reading_data.client_id,
									"reason": "Newer reading exists on server"
								})
								failed += 1
							continue

					# Verify meter exists
					meter_result = await db.execute(
						select(Meter).where(Meter.id == reading_data.meter_id)
					)
					meter = meter_result.scalar_one_or_none()

					if not meter:
						conflicts.append({
							"meter_id": str(reading_data.meter_id),
							"reason": "Meter not found"
						})
						failed += 1
						continue

					# Create new reading
					reading = Reading(
						**reading_data.model_dump(),
						user_id=user_id,
						device_id=device_id,
						sync_status="synced"
					)
					db.add(reading)

					# Update meter's last reading date
					if reading.reading_date > (meter.last_reading_date or datetime.min):
						meter.last_reading_date = reading.reading_date

					synced += 1

				except Exception as e:
					logger.error(f"Sync error for reading: {str(e)}")
					conflicts.append({
						"error": str(e),
						"reading": reading_data.model_dump_json()
					})
					failed += 1

			if synced > 0:
				await db.commit()

		return {
			"synced": synced,
			"failed": failed,
			"conflicts": conflicts
		}
