from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set
import json
import asyncio
from app.auth.jwt import auth_service
from app.core.celery_app import celery_app
from celery.result import AsyncResult
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
	"""Manage WebSocket connections for real-time updates"""

	def __init__(self):
		self.active_connections: Dict[str, Set[WebSocket]] = {}
		self.task_subscriptions: Dict[str, Set[str]] = {}  # task_id -> user_ids

	async def connect(self, websocket: WebSocket, user_id: str):
		await websocket.accept()
		if user_id not in self.active_connections:
			self.active_connections[user_id] = set()
		self.active_connections[user_id].add(websocket)
		logger.info(f"User {user_id} connected via WebSocket")

	def disconnect(self, websocket: WebSocket, user_id: str):
		if user_id in self.active_connections:
			self.active_connections[user_id].discard(websocket)
			if not self.active_connections[user_id]:
				del self.active_connections[user_id]
		logger.info(f"User {user_id} disconnected from WebSocket")

	async def send_personal_message(self, message: dict, user_id: str):
		if user_id in self.active_connections:
			disconnected = set()
			for connection in self.active_connections[user_id]:
				try:
					await connection.send_json(message)
				except:
					disconnected.add(connection)

			# Clean up disconnected
			for conn in disconnected:
				self.active_connections[user_id].discard(conn)

	async def broadcast_to_users(self, message: dict, user_ids: Set[str]):
		for user_id in user_ids:
			await self.send_personal_message(message, user_id)

	def subscribe_to_task(self, task_id: str, user_id: str):
		if task_id not in self.task_subscriptions:
			self.task_subscriptions[task_id] = set()
		self.task_subscriptions[task_id].add(user_id)

	def unsubscribe_from_task(self, task_id: str, user_id: str):
		if task_id in self.task_subscriptions:
			self.task_subscriptions[task_id].discard(user_id)
			if not self.task_subscriptions[task_id]:
				del self.task_subscriptions[task_id]


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
		websocket: WebSocket,
		token: str = Query(...)
):
	"""WebSocket endpoint for real-time task updates"""
	# Validate token
	payload = auth_service.decode_token(token)
	if not payload:
		await websocket.close(code=1008, reason="Invalid token")
		return

	user_id = payload.get("sub")
	if not user_id:
		await websocket.close(code=1008, reason="Invalid token payload")
		return

	await manager.connect(websocket, user_id)

	try:
		while True:
			# Receive message
			data = await websocket.receive_json()
			message_type = data.get("type")

			if message_type == "subscribe":
				task_id = data.get("task_id")
				if task_id:
					manager.subscribe_to_task(task_id, user_id)
					# Send initial status
					await send_task_status(task_id, user_id)

			elif message_type == "unsubscribe":
				task_id = data.get("task_id")
				if task_id:
					manager.unsubscribe_from_task(task_id, user_id)

			elif message_type == "ping":
				await websocket.send_json({"type": "pong"})

	except WebSocketDisconnect:
		manager.disconnect(websocket, user_id)
		# Clean up subscriptions
		for task_id in list(manager.task_subscriptions.keys()):
			manager.unsubscribe_from_task(task_id, user_id)


async def send_task_status(task_id: str, user_id: str):
	"""Send current task status to user"""
	result = AsyncResult(task_id)

	message = {
		"type": "task_update",
		"task_id": task_id,
		"status": result.state,
		"info": result.info if result.state != "FAILURE" else str(result.info)
	}

	await manager.send_personal_message(message, user_id)