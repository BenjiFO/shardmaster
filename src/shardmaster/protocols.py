from typing import Protocol, TypeVar

class AbstractWorkerPersona(Protocol):
	name: str

class AbstractTask(Protocol):
	pass

PersonaT = TypeVar("PersonaT", bound=AbstractWorkerPersona)
TaskT = TypeVar("TaskT", bound=AbstractTask)