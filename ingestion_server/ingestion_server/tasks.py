"""
Simple in-memory tracking of executed tasks.
"""

import datetime
import logging
from enum import Enum, auto
from multiprocessing import Process, Value
from typing import Literal, Optional

from ingestion_server import slack
from ingestion_server.indexer import TableIndexer, elasticsearch_connect
from ingestion_server.ingest import reload_upstream


class TaskTypes(Enum):
    @staticmethod
    def _generate_next_value_(name: str, *args, **kwargs) -> str:
        """
        Generates the value for ``auto()`` given the name of the enum item. Therefore,
        this function must be defined before any of the enum items.

        :param name: the enum variable name
        :return: the enum value
        """

        return name.lower()

    REINDEX = auto()
    """completely reindex all data for a given model"""

    INGEST_UPSTREAM = auto()
    """download the latest copy of the data from the upstream database, then completely
    reindex the newly imported data"""

    UPDATE_INDEX = auto()  # TODO: delete eventually, rarely used
    """reindex updates to a model from the database since the given date"""

    POINT_ALIAS = auto()
    """map a given index to a given alias, used when going live with an index"""

    LOAD_TEST_DATA = auto()
    """create indices in ES for QA tests; this is not intended to run in production but
    can be run without negative consequences"""

    def __str__(self):
        """
        Get the string representation of this enum. Unlike other objects, this
        does not default to ``__repr__``.

        :return: the string representation
        """

        return self.name


class TaskTracker:
    def __init__(self):
        self.tasks = {}

    def _prune_old_tasks(self):
        # TODO: Populate, document or delete function stub
        pass

    def add_task(self, task: Process, task_id: str, **kwargs):
        """
        Store information about a new task in memory.
        :param task: the task being performed
        :param task_id: the UUID of the task
        """

        self._prune_old_tasks()

        self.tasks[task_id] = {
            "task": task,
            "start_time": datetime.datetime.utcnow().timestamp(),
        } | kwargs

    @staticmethod
    def serialize_task_info(task_info: dict) -> dict:
        """
        Generate a response dictionary containing all relevant information about a task.
        :param task_info: the stored information about the task
        :return: the details of the task to show to the user
        """

        def _time_fmt(timestamp: int) -> Optional[str]:
            """
            Format the timestamp into a human-readable date and time notation.
            :param timestamp: the timestamp to format
            :return: the human-readable form of the timestamp
            """

            if not timestamp:
                return None
            return str(datetime.datetime.utcfromtimestamp(timestamp))

        active = task_info["task"].is_alive()
        start_time = task_info["start_time"]
        finish_time = task_info["finish_time"].value
        progress = task_info["progress"].value
        active_workers = task_info["active_workers"].value
        return {
            "active": active,
            "model": task_info["model"],
            "action": str(task_info["action"]),
            "progress": progress,
            "start_timestamp": start_time,
            "start_time": _time_fmt(start_time),
            "finish_timestamp": finish_time,
            "finish_time": _time_fmt(finish_time),
            "active_workers": bool(active_workers),
            "error": progress < 100 and not active,
        }

    def list_task_statuses(self) -> list:
        """
        Get the statuses of all tasks.
        :return: the statuses of all tasks
        """

        results = [self.get_task_status(task_id) for task_id in self.tasks.keys()]
        results.sort(key=lambda task: task["finish_timestamp"])
        return results

    def get_task_status(self, task_id) -> dict:
        """
        Get the status of a single task with the given task ID.
        :param task_id: the ID of the task to get the status for
        :return: the status of the task
        """

        self._prune_old_tasks()

        task_info = self.tasks[task_id]
        return {"task_id": task_id} | self.serialize_task_info(task_info)


def perform_task(
    task_id: str,
    model: Literal["image", "audio", "model_3d"],
    action: TaskTypes,
    callback_url: Optional[str],
    progress: Value,
    finish_time: Value,
    active_workers: Value,
    **kwargs,
):
    """
    Perform the task defined by the API request by invoking the task function with the
    correct arguments. Any additional keyword arguments will be forwarded to the
    appropriate task functions.

    :param task_id: the UUID assigned to the task for tracking
    :param model: the media type for which the action is being performed
    :param action: the name of the action being performed
    :param callback_url: the URL to which to make a request after the task is completed
    :param progress: shared memory for tracking the task's progress
    :param finish_time: shared memory for tracking the finish time of the task
    :param active_workers: shared memory for counting workers assigned to the task
    """

    elasticsearch = elasticsearch_connect()
    indexer = TableIndexer(
        elasticsearch,
        task_id,
        callback_url,
        progress,
        finish_time,
        active_workers,
    )

    # Task functions
    # ==============

    def ingest_upstream():  # includes ``reindex``
        reload_upstream(model)
        if model == "audio":
            reload_upstream("audioset", approach="basic")
        indexer.reindex(model, **kwargs)

    try:
        locs = locals()
        if func := locs.get(action.value):
            func()  # Run the corresponding task function
        elif func := getattr(indexer, action.value):
            func(model, **kwargs)
    except Exception as err:
        exception_type = f"{err.__class__.__module__}.{err.__class__.__name__}"
        logging.error(f"Error processing task `{action}` for `{model}`: {err}")
        slack.error(
            f":x_red: Error processing task `{action}` for `{model}` "
            f"(`{exception_type}`): \n"
            f"```\n{err}\n```"
        )
        raise

    logging.info(f"Task {task_id} completed.")
