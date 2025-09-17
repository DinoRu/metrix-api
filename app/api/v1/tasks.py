# =====================================
# api/app/api/v1/tasks.py
# =====================================
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.database import get_session
from app.schemas.task import TaskResponse, TaskStatusResponse
from app.models.task import TaskResult, TaskStatus
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=List[TaskResponse])
async def list_user_tasks(
		status: Optional[TaskStatus] = None,
		task_name: Optional[str] = None,
		skip: int = Query(0, ge=0),
		limit: int = Query(20, ge=1, le=100),
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""List all tasks for current user"""
	async with session as db:
		query = select(TaskResult).where(TaskResult.user_id == current_user.id)

		if status:
			query = query.where(TaskResult.status == status)
		if task_name:
			query = query.where(TaskResult.task_name == task_name)

		query = query.order_by(TaskResult.created_at.desc())
		query = query.offset(skip).limit(limit)

		result = await db.execute(query)
		tasks = result.scalars().all()

		return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_details(
		task_id: str,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""Get detailed task information"""
	async with session as db:
		result = await db.execute(
			select(TaskResult).where(
				TaskResult.id == task_id,
				TaskResult.user_id == current_user.id
			)
		)
		task = result.scalar_one_or_none()

		if not task:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Task not found"
			)

		# Get real-time status from Celery
		celery_result = AsyncResult(task_id)

		# Update task status if needed
		if celery_result.state != task.status:
			task.status = TaskStatus(celery_result.state.lower())
			if celery_result.state == "SUCCESS":
				task.result = celery_result.result
			elif celery_result.state == "FAILURE":
				task.error_message = str(celery_result.info)
			await db.commit()

		return TaskResponse.model_validate(task)


@router.delete("/{task_id}")
async def delete_task_result(
		task_id: str,
		session: AsyncSession = Depends(get_session),
		current_user=Depends(get_current_user)
):
	"""Delete completed task result"""
	async with session as db:
		result = await db.execute(
			select(TaskResult).where(
				TaskResult.id == task_id,
				TaskResult.user_id == current_user.id,
				TaskResult.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
			)
		)
		task = result.scalar_one_or_none()

		if not task:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Task not found or still running"
			)

		await db.delete(task)
		await db.commit()

		return {"message": "Task result deleted successfully"}