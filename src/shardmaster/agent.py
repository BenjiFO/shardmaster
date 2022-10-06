from abc import ABC, abstractmethod

class Agent(ABC):
	@abstractmethod
	async def routine(self):
		pass

	@abstractmethod
	def pre_routine(self):
		"""
		The pre-routine should initialise the agent's context (as in, contextvars).
		"""
		pass
