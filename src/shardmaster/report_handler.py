from abc import ABC, abstractmethod
from typing import Protocol, Generic, Any, Callable
import trio
from trio import MemoryReceiveChannel, MemorySendChannel, WouldBlock
from .protocols import TaskT

class BaseReportHandler(ABC):
	@abstractmethod
	async def start_handling(self):
		pass

class BasePooledReportHandler(BaseReportHandler):
	@property
	def channel(self) -> MemoryReceiveChannel:
		return self._channel
	
	@channel.setter
	def channel(self, channel: MemoryReceiveChannel):
		self._channel = channel

class PooledReportHandlerWithCallback(BasePooledReportHandler):
	def __init__(self, callback: Callable[[Any], None]):
		self.callable = callback

	async def start_handling(self):
		async with self._channel as channel:
			async for report in channel:
				callback = self.callable
				callback(report)

class BaseDedicatedReportHandler(BaseReportHandler):
	@property
	def channels(self) -> dict[str, MemoryReceiveChannel]:
		return self._channels
	
	@channels.setter
	def channels(self, channels: dict[str, MemoryReceiveChannel]):
		self._channels = channels

class DedicatedReportHandlerWithCallback(BaseDedicatedReportHandler):
	def __init__(self, callback: Callable[[str, Any], None]):
		self.callable = callback

	@staticmethod
	async def wait_single_channel(channel, worker_id, callback):
		async for item in channel:
			callback(worker_id, item)

	async def start_handling(self):
		async with trio.open_nursery() as nursery:
			for worker_id, chan in self._channels.items():
				nursery.start_soon(self.wait_single_channel, chan, worker_id, self.callable)
