from abc import ABC, abstractmethod
from typing import Protocol, Generic
from trio import MemoryReceiveChannel, MemorySendChannel
import trio
from .protocols import TaskT

class BaseTaskProvider(ABC, Generic[TaskT]):
	@abstractmethod
	async def provide(self):
		pass

class BasePooledTaskProvider(BaseTaskProvider):
	@property
	def channel(self) -> MemorySendChannel:
		return self._channel
	
	@channel.setter
	def channel(self, channel: MemorySendChannel):
		self._channel = channel

class BaseDedicatedTaskProvider(BaseTaskProvider):
	@property
	def channels(self) -> dict[str, MemorySendChannel]:
		return self._channels
	
	@channels.setter
	def channels(self, channels: dict[str, MemorySendChannel]):
		self._channels = channels

	def done(self):
		for w_id, c in self._channels.items():
			c.close()

class ListTaskProvider(BasePooledTaskProvider):
	def __init__(self, tasks: list[TaskT]):
		self.tasks = tasks

	async def provide(self):
		with self._channel:
			for task in self.tasks:
				await self._channel.send(task)

class DictTaskProvider(BaseDedicatedTaskProvider):
	def __init__(self, tasks: dict[str, list[TaskT]]):
		self.tasks = tasks

	def tasks_for_worker(self, worker_id):
		return self.tasks[worker_id]
	
	async def provider_for_worker(self, worker_id):
		channel = self._channels.get(worker_id, None)
		for task in self.tasks_for_worker(worker_id):
			if channel:
				await channel.send(task)
			else:
				break

	async def provide(self):
		async with trio.open_nursery() as nursery:
			for worker_id in self.tasks.keys():
				nursery.start_soon(self.provider_for_worker, worker_id)
		self.done()
