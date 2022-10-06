from collections.abc import Sequence
from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, Generic, Generator, Callable, Type, Any, Union
from dataclasses import dataclass
from enum import Enum
from inspect import signature
import math
import trio
from trio import MemorySendChannel, MemoryReceiveChannel
import signal

from . import logging
from .protocols import *
from .worker import *
from .report_handler import *
from .task_provider import *

@dataclass
class _ConcreteAbstractWorkerPersona(AbstractWorkerPersona):
	name: str

class DistributionStructure(Enum):
	pooled = 1
	dedicated = 2

class ChannelProvider:
	def __init__(self, mode: DistributionStructure, workers: list[str]):
		self.worker_channels: dict[str, tuple[MemorySendChannel, MemoryReceiveChannel]]
		self.master_channels: Union[dict[str, tuple[MemoryReceiveChannel, MemorySendChannel]], tuple[MemoryReceiveChannel, MemorySendChannel]]

		self.mode = mode
		if mode == DistributionStructure.pooled:
			worker_count = len(workers)
			report_send_channel, report_receive_channel = trio.open_memory_channel(worker_count)
			distribution_send_channel, distribution_receive_channel = trio.open_memory_channel(worker_count)
			
			self.worker_channels = {p: (report_send_channel.clone(), distribution_receive_channel.clone()) for p in workers}
			self.master_channels = (report_receive_channel, distribution_send_channel)
			self.__channels = [report_send_channel, report_receive_channel, distribution_send_channel, distribution_receive_channel]
		else:
			self.worker_channels = {}
			self.master_channels = {}
			for worker_id in workers:
				report_send_channel, report_receive_channel = trio.open_memory_channel(1)
				distribution_send_channel, distribution_receive_channel = trio.open_memory_channel(1)
				self.worker_channels[worker_id] = (report_send_channel, distribution_receive_channel)
				self.master_channels[worker_id] = (report_receive_channel, distribution_send_channel)

	def channels_for_worker(self, worker):
		return self.worker_channels[worker]

	def channels_for_master(self):# -> Union[]:
		return self.master_channels

	async def __aenter__(self):
		if self.mode == DistributionStructure.pooled:
			for channel in self.__channels:
				await channel.__aenter__()
			return self
		else:
			return self

	async def __aexit__(self, *args):
		if self.mode == DistributionStructure.pooled:
			for channel in self.__channels:
				await channel.__aexit__(*args)

class TaskSharder(Generic[PersonaT, TaskT]):
	def __init__(
		self, 
		worker_type: Type[Worker[PersonaT]], 
		report_handler: Union[Union[Callable[[Any], None], Callable[[str, Any], None]], BaseReportHandler], 
		personas: list[PersonaT], 
		task_provider: BaseTaskProvider[TaskT]
	):
		if callable(report_handler):
			if len(signature(report_handler).parameters) == 2:
				report_handler = DedicatedReportHandlerWithCallback(report_handler)
			else:
				report_handler = PooledReportHandlerWithCallback(report_handler)
		self.report_handler = report_handler
		self.personas = personas
		self.worker_type = worker_type
		self.task_provider = task_provider
		
		if isinstance(task_provider, BaseDedicatedTaskProvider):
			assert isinstance(report_handler, BaseDedicatedReportHandler)
			self.distribution_structure = DistributionStructure.dedicated
		else:
			assert isinstance(task_provider, BasePooledTaskProvider)
			assert isinstance(report_handler, BasePooledReportHandler)
			self.distribution_structure = DistributionStructure.pooled

	@staticmethod
	async def control_c_watcher(nursery: trio.Nursery, trigger: trio.Event):
		with trio.open_signal_receiver(signal.SIGINT) as signal_aiter:
			async for signum in signal_aiter:
				assert signum == signal.SIGINT
				# the user hit control-C

				if trigger.is_set():
					# SIGINT already received once
					nursery.cancel_scope.cancel()
					logging.error("Okay, aborting.")
				else:
					trigger.set()
					logging.error("Terminating current tasks, will exit afterwards.")

	def _make_done_callback(self, nursery: trio.Nursery, worker: Worker[PersonaT]):
		def _cb():
			self.workers.remove(worker)
			if len(self.workers) == 0:
				nursery.cancel_scope.cancel()
		return _cb

	async def start(self):
		agent_logging_persona.set(_ConcreteAbstractWorkerPersona(name="puppetmaster"))
		logging.info("Starting task sharder")

		self.workers = list[Worker[PersonaT]]()

		async with trio.open_nursery() as nursery:
			async with ChannelProvider(self.distribution_structure, [p.name for p in self.personas]) as channel_provider:
				trigger_graceful_shutdown = trio.Event()

				for w_persona in self.personas:
					local_status_report_send_channel, local_tasks_receive_channel = channel_provider.channels_for_worker(w_persona.name)
					worker = self.worker_type(w_persona, local_tasks_receive_channel, local_status_report_send_channel, trigger_graceful_shutdown)
					worker.done_callback = self._make_done_callback(nursery, worker)
					self.workers.append(worker)

					logging.info(f"Spawning worker for persona {worker.persona.name}")
					nursery.start_soon(worker.routine)

				if self.distribution_structure == DistributionStructure.pooled:
					status_report_receive_channel, tasks_send_channel = channel_provider.channels_for_master()
					self.task_provider.channel = tasks_send_channel
					self.report_handler.channel = status_report_receive_channel
				else:
					master_channels = channel_provider.channels_for_master()
					send_channels = {persona_id: channel_pair[1] for persona_id, channel_pair in master_channels.items()}
					receive_channels = {persona_id: channel_pair[0] for persona_id, channel_pair in master_channels.items()}
					self.task_provider.channels = send_channels
					self.report_handler.channels = receive_channels

				nursery.start_soon(self.task_provider.provide)

				if isinstance(self.report_handler, DedicatedReportHandlerWithCallback):
					self.report_handler.nursery = nursery
				nursery.start_soon(self.report_handler.start_handling)

				await self.control_c_watcher(nursery, trigger_graceful_shutdown)

				# class (provider pattern wrt the Scheduler) that pulls tasks to a len(workers) channel
				# up to the worker that receives it to claim it in the db and update its progress in the task

			logging.info("Waiting for workers to finish...")
			# -- we exit the nursery block here --
		logging.info("All done!")

