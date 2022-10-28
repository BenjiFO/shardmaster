import trio
from ..task_provider import BasePooledTaskProvider, BaseDedicatedTaskProvider
from ..protocols import TaskT

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
		
		with channel: # this context will close the channel at the end, thereby honoring the Provider contract
			for task in self.tasks_for_worker(worker_id):
				try:
					await channel.send(task)
				except trio.BrokenResourceError:
					# the receiver indicated, by closing the receive channel, that it does not wish to receive further tasks.
					break

	async def provide(self):
		async with trio.open_nursery() as nursery:
			for worker_id in self.tasks.keys():
				nursery.start_soon(self.provider_for_worker, worker_id)
