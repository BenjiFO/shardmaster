from abc import ABC, abstractmethod
from typing import Protocol, Generic
from trio import MemoryReceiveChannel, MemorySendChannel
import trio
from .protocols import TaskT

from deprecated import deprecated

class BaseTaskProvider(ABC, Generic[TaskT]):
	"""
	The provider's contract is to take responsibility for closing the task distribution channel(s) once it is done providing them.
	Yet, the provider must be resilient to channel closure on the receiver side – it is how the receiver indicates that it does not wish to receive further tasks.
	"""

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

	def done(self):
		self._channel.close()

class BaseDedicatedTaskProvider(BaseTaskProvider):
	@property
	def channels(self) -> dict[str, MemorySendChannel]:
		return self._channels
	
	@channels.setter
	def channels(self, channels: dict[str, MemorySendChannel]):
		self._channels = channels

	def done(self):
		for channel in self._channels:
			channel.close() # closing a channel is idempotent; doesn't matter if it already was closed
