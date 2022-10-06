from abc import ABC, abstractmethod
from typing import Generic, Any
from dataclasses import dataclass
from trio import MemoryReceiveChannel, MemorySendChannel, Event
from .agent import Agent
from .protocols import PersonaT, TaskT
from .logging import agent_logging_persona

class Worker(Agent, Generic[PersonaT]):
	def __init__(
		self,
		persona: PersonaT,
		receive_channel: MemoryReceiveChannel,
		send_channel: MemorySendChannel,
		shutdown_event: Event,
		**executor_kwargs
	):
		self.persona = persona
		self.receive_channel = receive_channel
		self.send_channel = send_channel
		self.shutdown_event = shutdown_event
		self.executor_kwargs = executor_kwargs

	async def routine(self):
		raise NotImplementedError

	def pre_routine(self):
		agent_logging_persona.set(self.persona)

	async def done(self):
		done_cb = self.done_callback
		done_cb()

	def __repr__(self):
		return f"{self.__class__.__name__}(name={self.persona.name})"

@dataclass
class ReportTicket(Generic[PersonaT, TaskT]):
	persona: PersonaT
	task: TaskT
	result: Any

class ReportingWorker(Worker, Generic[TaskT]):
	async def report(self, task: TaskT, result: Any):
		await self.send_channel.send(ReportTicket(self.persona, task, result))
