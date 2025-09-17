from celery import Task
from app.api.v1.websocket import manager
import asyncio


class CallbackTask(Task):
	"""Task that sends progress updates via WebSocket"""

	def on_success(self, retval, task_id, args, kwargs):
		"""Called on successful task completion"""
		asyncio.create_task(self.send_update(
			task_id,
			{
				"type": "task_update",
				"task_id": task_id,
				"status": "SUCCESS",
				"result": retval
			}
		))

	def on_failure(self, exc, task_id, args, kwargs, einfo):
		"""Called on task failure"""
		asyncio.create_task(self.send_update(
			task_id,
			{
				"type": "task_update",
				"task_id": task_id,
				"status": "FAILURE",
				"error": str(exc)
			}
		))

	async def send_update(self, task_id: str, message: dict):
		"""Send update to subscribed users"""
		if task_id in manager.task_subscriptions:
			await manager.broadcast_to_users(
				message,
				manager.task_subscriptions[task_id]
			)
