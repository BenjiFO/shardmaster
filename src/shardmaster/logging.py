import logging
import contextvars

agent_logging_persona = contextvars.ContextVar("agent_logging_persona")
inside_worker_logger = logging.getLogger()

class InsideWorkerFilter(logging.Filter):
	"""
	A filter which injects context-specific information into logs and ensures
	that only information for a specific webapp is included in its log
	"""
	def __init__(self):
		pass

	def filter(self, record):
		persona = agent_logging_persona.get()
		persona = persona.name or ""
		record.persona = persona

		return True

def debug(msg):
	# Read from task-local storage:
	inside_worker_logger.debug(msg)

def info(msg):
	# Read from task-local storage:
	inside_worker_logger.info(msg)

def warn(msg):
	# Read from task-local storage:
	inside_worker_logger.info(msg)

def error(msg):
	# Read from task-local storage:
	inside_worker_logger.info(msg)
