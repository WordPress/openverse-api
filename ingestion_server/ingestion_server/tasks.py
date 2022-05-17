"""
Simple in-memory tracking of executed tasks.
"""

import datetime as dt
import logging
from enum import Enum, auto
from multiprocessing import Value
from typing import Literal, Optional

import requests

from ingestion_server import slack
from ingestion_server.indexer import TableIndexer, elasticsearch_connect
from ingestion_server.ingest import reload_upstream


class TaskTypes(str, Enum):
    """
    Each type has a value equal to the name of the task in lowercase.
    """

    @staticmethod
    def _generate_next_value_(name: str, *args) -> str:
        return name.lower()

    # Completely reindex all data for a given model.
    REINDEX = auto()
    # Reindex updates to a model from the database since a certain date.
    UPDATE_INDEX = auto()
    # Download the latest copy of the data from the upstream database, then
    # completely reindex the newly imported data.
    INGEST_UPSTREAM = auto()
    # Create indices in Elasticsearch for QA tests.
    # This is not intended for production use, but can be safely executed in a
    # production environment without consequence.
    LOAD_TEST_DATA = auto()

    def __str__(self):
        """
        Get the string representation of this enum. Unlike other objects, this
        does not default to ``__repr__``.
        :return: the string representation
        """
        return self.value


class TaskTracker:
    def __init__(self):
        self.id_task = {}
        self.id_action = {}
        self.id_progress = {}
        self.id_start_time = {}
        self.id_finish_time = {}
        self.id_active_workers = {}

    def add_task(self, task, task_id, action, progress, finish_time, active_workers):
        self._prune_old_tasks()
        self.id_task[task_id] = task
        self.id_action[task_id] = action
        self.id_progress[task_id] = progress
        self.id_start_time[task_id] = dt.datetime.utcnow().timestamp()
        self.id_finish_time[task_id] = finish_time
        self.id_active_workers[task_id] = active_workers
        return task_id

    def _prune_old_tasks(self):
        pass

    def list_task_statuses(self):
        self._prune_old_tasks()
        results = []
        for _id, task in self.id_task.items():
            percent_completed = self.id_progress[_id].value
            active = task.is_alive()
            start_time = self.id_start_time[_id]
            finish_time = self.id_finish_time[_id].value
            active_workers = self.id_active_workers[_id].value
            results.append(
                {
                    "task_id": _id,
                    "active": active,
                    "action": self.id_action[_id],
                    "progress": percent_completed,
                    "error": percent_completed < 100 and not active,
                    "start_time": start_time,
                    "finish_time": finish_time,
                    "active_workers": bool(active_workers),
                }
            )
        sorted_results = sorted(results, key=lambda x: x["finish_time"])

        to_utc = dt.datetime.utcfromtimestamp

        def render_date(x):
            return to_utc(x) if x != 0.0 else None

        # Convert date to a readable format
        for idx, task in enumerate(sorted_results):
            start_time = task["start_time"]
            finish_time = task["finish_time"]
            sorted_results[idx]["start_time"] = str(render_date(start_time))
            sorted_results[idx]["finish_time"] = str(render_date(finish_time))

        return sorted_results


def perform_task(
    task_id: str,
    model: Literal["image", "audio", "model_3d"],
    action: TaskTypes,
    callback_url: Optional[str],
    since_date: Optional[str],
    progress: Value,
    finish_time: Value,
    active_workers: Value,
):
    """
    Perform the task defined by the API request by invoking the task function with the
    correct arguments.

    :param task_id: the UUID assigned to the task for tracking
    :param model: the media type for which the action is being performed
    :param action: the name of the action being performed
    :param callback_url: the URL to which to make a request after the task is completed
    :param since_date: the date after which to update indices
    :param progress: shared memory for tracking the task's progress
    :param finish_time: shared memory for tracking the finish time of the task
    :param active_workers: shared memory for counting workers assigned to the task
    """

    elasticsearch = elasticsearch_connect()
    indexer = TableIndexer(
        elasticsearch,
        model,
        task_id,
        progress,
        finish_time,
        active_workers,
    )

    # Task functions
    # ==============

    def reindex():
        slack.verbose(f"`{model}`: Beginning Elasticsearch reindex")
        indexer.reindex(model)

    def update_index():
        indexer.update(model, since_date)

    def ingest_upstream():
        reload_upstream(model)
        if model == "audio":
            reload_upstream("audioset", approach="basic")
        indexer.reindex(model)

    def load_test_data():
        indexer.load_test_data(model)

    try:
        locs = locals()
        func = locs[action.value]
        func()  # Run the corresponding task function
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
    if callback_url:
        try:
            logging.info("Sending callback request")
            res = requests.post(callback_url)
            logging.info(f"Response: {res.text}")
        except requests.exceptions.RequestException as err:
            logging.error("Failed to send callback!")
            logging.error(err)
