import base64
import logging
from typing import Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Query, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy import select, or_, func, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.core.celery_app import celery_app
from app.database import get_session
from app.models.meter import Meter
from app.models.reading import Reading
from app.models.user import UserRole, User
from app.schemas.base import PaginatedResponse
from app.schemas.meter import MeterResponse, MeterCreate, MeterUpdate, MeterImportResponse, MeterResponseWithReading, \
    MeterListResponse
from app.schemas.reading import ReadingResponse
from app.services.meter_service import MeterService
from app.workers.import_meter_from_import import import_meters_from_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=PaginatedResponse)
async def list_meters(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        search: Optional[str] = None,
        status: Optional[str] = None,
        type: Optional[str] = None,
        session: AsyncSession = Depends(get_session),
        current_user=Depends(get_current_user)
):
    """List all meters with pagination and filters"""
    async with session as db:
        query = select(Meter)

        # Apply filters
        filters = []
        if search:
            filters.append(or_(
                Meter.meter_number.ilike(f"%{search}%"),
                Meter.client_name.ilike(f"%{search}%"),
                Meter.location_address.ilike(f"%{search}%")
            ))
        if status:
            filters.append(Meter.status == status)
        if type:
            filters.append(Meter.type == type)

        if filters:
            query = query.where(*filters)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Meter.created_at.desc())
        result = await db.execute(query)
        meters = result.scalars().all()

        return PaginatedResponse(
            total=total,
            skip=skip,
            limit=limit,
            data=[MeterResponse.model_validate(m) for m in meters]
        )

@router.get("/with-readings", response_model=PaginatedResponse)
async def list_meters_with_readings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """List all meters that have at least one reading, with pagination and filters"""
    async with session as db:
        # Subquery to get meters with readings
        subquery = select(Meter.id).join(Reading, Meter.id == Reading.meter_id).distinct()

        # Main query
        query = select(Meter).where(Meter.id.in_(subquery))

        # Apply filters
        filters = []
        if search:
            filters.append(or_(
                Meter.meter_number.ilike(f"%{search}%"),
                Meter.client_name.ilike(f"%{search}%"),
                Meter.location_address.ilike(f"%{search}%")
            ))
        if status:
            filters.append(Meter.status == status)
        if type:
            filters.append(Meter.type == type)

        if filters:
            query = query.where(*filters)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Meter.created_at.desc())
        result = await db.execute(query)
        meters = result.scalars().all()

        # Fetch latest reading for each meter
        meter_responses = []
        for meter in meters:
            latest_reading = await db.execute(
                select(Reading)
                .where(Reading.meter_id == meter.id)
                .order_by(Reading.reading_date.desc())
                .limit(1)
            )
            reading = latest_reading.scalar_one_or_none()
            meter_response = MeterResponseWithReading(
                **MeterResponse.model_validate(meter).model_dump(),
                readings=ReadingResponse.model_validate(reading) if reading else None
            )
            meter_responses.append(meter_response)

        return PaginatedResponse(
            total=total,
            skip=skip,
            limit=limit,
            data=meter_responses
        )


@router.get("/all", response_model=MeterListResponse)
async def list_all_meters(
    search: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """List all meters without pagination, with optional filters"""
    async with session as db:
        query = select(Meter)

        # Apply filters
        filters = []
        if search:
            filters.append(or_(
                Meter.meter_number.ilike(f"%{search}%"),
                Meter.client_name.ilike(f"%{search}%"),
                Meter.location_address.ilike(f"%{search}%")
            ))
        if status:
            filters.append(Meter.status == status)
        if type:
            filters.append(Meter.type == type)

        if filters:
            query = query.where(*filters)

        # Execute query
        result = await db.execute(query.order_by(Meter.created_at.desc()))
        meters = result.scalars().all()

        # Prepare response
        return MeterListResponse(
            total=len(meters),
            data=[MeterResponse.model_validate(m) for m in meters]
        )


@router.get("/{meter_id}", response_model=MeterResponse)
async def get_meter(
        meter_id: str,
        session: AsyncSession = Depends(get_session),
        current_user = Depends(get_current_user)
):
    """Get a specific meter by ID"""
    async with session as db:
        result = await db.execute(select(Meter).where(Meter.id == meter_id))
        meter = result.scalar_one_or_none()

        if not meter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meter not found"
            )
        return MeterResponse.model_validate(meter)


@router.post("/", response_model=MeterResponse, status_code=status.HTTP_201_CREATED)
async def create_meter(
        meter_data: MeterCreate,
        session: AsyncSession = Depends(get_session),
        current_user=Depends(require_role([UserRole.ADMIN]))
):
    """Create a new meter"""
    async with session as db:
        # Check if meter number already exists
        result = await db.execute(
            select(Meter).where(Meter.meter_number == meter_data.meter_number)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meter number already exists"
            )

        meter = Meter(**meter_data.model_dump())
        db.add(meter)
        await db.commit()
        await db.refresh(meter)

        logger.info(f"Meter created: {meter.meter_number}")
        return MeterResponse.model_validate(meter)




@router.patch("/{meter_id}", response_model=MeterResponse)
async def update_meter(
        meter_id: str,
        meter_update: MeterUpdate,
        session: AsyncSession = Depends(get_session),
        current_user=Depends(require_role([UserRole.ADMIN]))
):
    """Update a meter"""
    async with session as db:
        result = await db.execute(select(Meter).where(Meter.id == meter_id))
        meter = result.scalar_one_or_none()

        if not meter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meter not found"
            )

        # Update fields
        for field, value in meter_update.model_dump(exclude_unset=True).items():
            setattr(meter, field, value)

        await db.commit()
        await db.refresh(meter)

        logger.info(f"Meter updated: {meter.meter_number}")
        return MeterResponse.model_validate(meter)



@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_meters(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(require_role([UserRole.ADMIN]))
):
    """
    Supprime tous les compteurs (Meters) ainsi que leurs lectures associées.
    Réservé aux administrateurs.
    """
    try:
        # ⚠️ Cette approche supprime tout via SQL brut
        # => les cascades ORM ne sont pas appliquées
        # => mais plus performant pour de gros volumes
        stmt = delete(Meter)
        result = await session.execute(stmt)
        await session.commit()

        logger.warning(f"{result.rowcount} meters supprimés par {current_user.username}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de la suppression de tous les meters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la suppression des meters"
        )


@router.post("/import", response_model=MeterImportResponse)
async def import_meters(
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session),
        current_user=Depends(require_role([UserRole.ADMIN]))
):
    """Import meters from CSV or XLSX file"""
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be CSV or XLSX format"
        )

    meter_service = MeterService(session)
    result = await meter_service.import_from_file(file)

    logger.info(f"Meters import: {result['success']} success, {result['failed']} failed")
    return result

@router.post("/import-meters", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_import_meters(
    file: UploadFile = File(...),
    current_user=Depends(require_role([UserRole.ADMIN])),
):
    if not file.filename.lower().endswith((".xlsx",)):
        raise HTTPException(400, "File must be XLSX")

    # Lire le fichier en mémoire (option: stocker d’abord en S3 si >50 Mo)
    content = await file.read()
    task = celery_app.send_task("tasks.import_meters", kwargs={"file_bytes": content}, queue="default")
    return {
        "task_id": task.id,
        "status_url": f"/api/v1/meters/{task.id}/status",
        "detail": "Import task enqueued",
    }

@router.post("/upload-file")
async def import_meters(
    file: UploadFile,
    user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Endpoint synchrone pour importer un fichier Excel de compteurs.
    """
    try:
        # Lecture fichier en mémoire
        raw_content = await file.read()
        file_content_b64 = base64.b64encode(raw_content).decode("utf-8")

        result = import_meters_from_file(
            file_content_b64=file_content_b64,
            file_name=file.filename,
            user_id=user.id,
            file_type=file.filename.split(".")[-1],
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{task_id}/status")
async def get_task_status(task_id: str, current_user=Depends(require_role([UserRole.ADMIN]))):
    res = AsyncResult(task_id, app=celery_app)
    meta = res.info if isinstance(res.info, dict) else {}
    return {"task_id": task_id, "state": res.state, "meta": meta}


@router.get("/{task_id}/result")
async def get_task_result(task_id: str, current_user=Depends(require_role([UserRole.ADMIN]))):
    res = AsyncResult(task_id, app=celery_app)
    if not res.ready():
        return {"task_id": task_id, "state": res.state, "meta": res.info}
    if res.failed():
        raise HTTPException(500, f"Tâche échouée: {res.info}")
    return {"task_id": task_id, "state": res.state, "result": res.result}


@router.delete("/{meter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meter(
        meter_id: str,
        session: AsyncSession = Depends(get_session),
        current_user=Depends(require_role([UserRole.ADMIN]))
):
    """Delete a meter"""
    async with session as db:
        result = await db.execute(select(Meter).where(Meter.id == meter_id))
        meter = result.scalar_one_or_none()

        if not meter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meter not found"
            )

        await db.delete(meter)
        await db.commit()

        logger.info(f"Meter deleted: {meter.meter_number}")
