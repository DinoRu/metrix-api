import logging
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_session, get_current_user
from sqlalchemy import select, and_, func

from app.models.meter import Meter
from app.models.reading import Reading
from app.schemas.base import PaginatedResponse
from app.schemas.reading import ReadingResponse, ReadingUpdate, ReadingSyncRequest, ReadingSyncResponse, ReadingCreate
from app.services.reading_service import ReadingService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=PaginatedResponse)
async def list_readings(
		skip: int = Query(0, ge=0),
		limit: int = Query(100, ge=1, le=1000),
		meter_id: Optional[str] = None,
		start_date: Optional[date] = None,
		end_date: Optional[date] = None,
		sync_status: Optional[str] = None,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""List readings with filters"""
	async with session as db:
		query = select(Reading)

		# Apply filters
		filters = []
		if meter_id:
			filters.append(Reading.meter_id == meter_id)
		if start_date:
			filters.append(Reading.reading_date >= start_date)
		if end_date:
			filters.append(Reading.reading_date <= end_date)
		if sync_status:
			filters.append(Reading.sync_status == sync_status)

		# For controllers, only show their own readings
		if current_user.role == "controller":
			filters.append(Reading.user_id == current_user.id)

		if filters:
			query = query.where(and_(*filters))

		# Get total count
		count_query = select(func.count()).select_from(query.subquery())
		total = await db.scalar(count_query)

		# Apply pagination and ordering
		query = query.offset(skip).limit(limit).order_by(Reading.reading_date.desc())
		result = await db.execute(query)
		readings = result.scalars().all()

		return PaginatedResponse(
			total=total,
			skip=skip,
			limit=limit,
			data=[ReadingResponse.model_validate(r) for r in readings]
		)


@router.get("/{reading_id}", response_model=ReadingResponse)
async def get_reading(
		reading_id: str,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""Get a specific reading"""
	async with session as db:
		query = select(Reading).where(Reading.id == reading_id)

		# Controllers can only see their own readings
		if current_user.role == "controller":
			query = query.where(Reading.user_id == current_user.id)

		result = await db.execute(query)
		reading = result.scalar_one_or_none()

		if not reading:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Reading not found"
			)

		return ReadingResponse.model_validate(reading)


@router.post("/", response_model=ReadingResponse, status_code=status.HTTP_201_CREATED)
async def create_reading(
		reading_data: ReadingCreate,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""Create a new reading"""
	async with session as db:
		# Verify meter exists
		meter_result = await db.execute(
			select(Meter).where(Meter.id == reading_data.meter_id)
		)
		meter = meter_result.scalar_one_or_none()

		if not meter:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Meter not found"
			)

		# Check for duplicate client_id (offline sync)
		if reading_data.client_id:
			existing = await db.execute(
				select(Reading).where(Reading.client_id == reading_data.client_id)
			)
			if existing.scalar_one_or_none():
				raise HTTPException(
					status_code=status.HTTP_409_CONFLICT,
					detail="Reading with this client_id already exists"
				)

		reading = Reading(
			**reading_data.model_dump(),
			user_id=current_user.id
		)
		db.add(reading)

		# Update meter's last reading date
		meter.last_reading_date = reading.reading_date

		await db.commit()
		await db.refresh(reading)

		logger.info(f"Reading created for meter {meter.meter_number}")
		return ReadingResponse.model_validate(reading)


@router.post("/sync", response_model=ReadingSyncResponse)
async def sync_readings(
		sync_request: ReadingSyncRequest,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""Sync multiple readings from mobile device"""
	reading_service = ReadingService(session)
	result = await reading_service.sync_readings(
		sync_request.readings,
		current_user.id,
		sync_request.device_id
	)

	logger.info(f"Sync from device {sync_request.device_id}: {result['synced']} synced, {result['failed']} failed")
	return result


@router.patch("/{reading_id}", response_model=ReadingResponse)
async def update_reading(
		reading_id: str,
		reading_update: ReadingUpdate,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""Update a reading"""
	async with session as db:
		query = select(Reading).where(Reading.id == reading_id)

		# Controllers can only update their own readings
		if current_user.role == "controller":
			query = query.where(Reading.user_id == current_user.id)

		result = await db.execute(query)
		reading = result.scalar_one_or_none()

		if not reading:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Reading not found"
			)

		# Update fields
		for field, value in reading_update.model_dump(exclude_unset=True).items():
			setattr(reading, field, value)

		await db.commit()
		await db.refresh(reading)

		return ReadingResponse.model_validate(reading)