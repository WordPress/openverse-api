"""
A small RPC API server for scheduling ingestion of upstream data and
Elasticsearch indexing tasks.
"""

import logging
import sys
import time
import uuid
from multiprocessing import Process, Value
from urllib.parse import urlparse

import falcon
from falcon.media.validators import jsonschema

from ingestion_server import slack
from ingestion_server.constants.media_types import MEDIA_TYPES, MediaType
from ingestion_server.es_helpers import elasticsearch_connect, get_stat
from ingestion_server.indexer import TableIndexer
from ingestion_server.state import clear_state, worker_finished
from ingestion_server.tasks import TaskTracker, TaskTypes, perform_task


MODEL = "model"
ACTION = "action"
CALLBACK_URL = "callback_url"
SINCE_DATE = "since_date"


class HealthResource:
    @staticmethod
    def on_get(_, resp):
        resp.status = falcon.HTTP_200
        resp.media = {"status": "200 OK"}


class StatResource:
    @staticmethod
    def on_get(_, res, name):
        """
        Handles an incoming GET request. Provides information about the given index or
        alias.

        :param _: the incoming request
        :param res: the appropriate response
        :param name: the name of the index or alias
        :return: the information about the index or alias
        """

        elasticsearch = elasticsearch_connect()
        stat = get_stat(elasticsearch, name)
        res.status = falcon.HTTP_200
        res.media = stat._asdict()


class BaseTaskResource:
    """Base class for all resource that need access to a task tracker"""

    def __init__(self, tracker: TaskTracker, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracker = tracker


class TaskResource(BaseTaskResource):
    @staticmethod
    def _get_base_url(req):
        parsed = urlparse(req.url)
        return parsed.scheme + "://" + parsed.netloc

    @jsonschema.validate(
        req_schema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "enum": MEDIA_TYPES},
                "action": {
                    "type": "string",
                    "enum": list(task_type.name for task_type in TaskTypes),
                },
                # Accepts all forms described in the PostgreSQL documentation:
                # https://www.postgresql.org/docs/current/datatype-datetime.html
                "since_date": {"type": "string"},
                "index_suffix": {"type": "string"},
                "alias": {"type": "string"},
                "force_delete": {"type": "boolean"},
            },
            "required": ["model", "action"],
            "allOf": [
                {
                    "if": {
                        "properties": {"action": {"const": TaskTypes.POINT_ALIAS.name}}
                    },
                    "then": {"required": ["index_suffix", "alias"]},
                },
                {
                    "if": {"properties": {"action": {"const": TaskTypes.PROMOTE.name}}},
                    "then": {"required": ["index_suffix", "alias"]},
                },
                # TODO: delete eventually, rarely used
                {
                    "if": {
                        "properties": {"action": {"const": TaskTypes.UPDATE_INDEX.name}}
                    },
                    "then": {"required": ["index_suffix", "since_date"]},
                },
                {
                    "if": {
                        "properties": {"action": {"const": TaskTypes.DELETE_INDEX.name}}
                    },
                    "then": {
                        "oneOf": [
                            {"required": ["alias"]},
                            {"required": ["index_suffix"]},
                        ]
                    },
                },
            ],
        }
    )
    def on_post(self, req, res):
        """
        Handles an incoming POST request. Schedules the specified task.

        :param req: the incoming request
        :param res: the appropriate response
        """

        body = req.get_media()

        # Generated fields
        task_id = uuid.uuid4().hex  # no hyphens

        # Required fields

        model: MediaType = body[MODEL]
        action = TaskTypes[body[ACTION]]

        # Optional fields
        callback_url = body.get("callback_url")
        since_date = body.get("since_date")
        index_suffix = body.get("index_suffix", task_id)
        alias = body.get("alias")
        force_delete = body.get("force_delete", False)

        # Shared memory
        progress = Value("d", 0.0)
        finish_time = Value("d", 0.0)
        active_workers = Value("i", int(False))
        is_bad_request = Value("i", 0)

        task = Process(
            target=perform_task,
            kwargs={
                "task_id": task_id,
                "model": model,
                "action": action,
                "callback_url": callback_url,
                "progress": progress,
                "finish_time": finish_time,
                "active_workers": active_workers,
                "is_bad_request": is_bad_request,
                # Task-specific keyword arguments
                "since_date": since_date,
                "index_suffix": index_suffix,
                "alias": alias,
                "force_delete": force_delete,
            },
        )
        task.start()

        self.tracker.add_task(
            task_id,
            task=task,
            model=model,
            action=action,
            callback_url=callback_url,
            progress=progress,
            finish_time=finish_time,
            active_workers=active_workers,
            is_bad_request=is_bad_request,
        )

        base_url = self._get_base_url(req)
        status_url = f"{base_url}/task/{task_id}"

        # Give the task a moment to start so we can detect immediate failure.
        # TODO: Use IPC to detect if the job launched successfully instead
        # of giving it 100ms to crash. This is prone to race conditions.
        time.sleep(0.1)
        if task.is_alive():
            res.status = falcon.HTTP_202
            res.media = {
                "message": "Successfully scheduled task",
                "task_id": task_id,
                "status_check": status_url,
            }
        elif progress.value == 100:
            res.status = falcon.HTTP_202
            res.media = {
                "message": "Successfully completed task",
                "task_id": task_id,
                "status_check": status_url,
            }
        elif is_bad_request.value:  # set to 1 for bad tasks
            res.status = falcon.HTTP_400
            res.media = {
                "message": "Failed during task execution due to bad request. Check "
                "scheduler logs."
            }
        else:
            res.status = falcon.HTTP_500
            res.media = {
                "message": "Failed to schedule task due to an internal server "
                "error. Check scheduler logs."
            }

    def on_get(self, _, res):
        """
        Handles an incoming GET request. Provides information about all past tasks.

        :param _: the incoming request
        :param res: the appropriate response
        """

        res.media = self.tracker.list_task_statuses()


class TaskStatus(BaseTaskResource):
    def on_get(self, _, res, task_id):
        """
        Handles an incoming GET request. Provides information about a single task.

        :param _: the incoming request
        :param res: the appropriate response
        :param task_id: the ID of the task for which to get the information
        """

        try:
            result = self.tracker.get_task_status(task_id)
            res.media = result
        except KeyError:
            res.status = falcon.HTTP_404
            res.media = {"message": f"No task found with id {task_id}."}


class WorkerFinishedResource(BaseTaskResource):
    def on_post(self, req, _):
        """
        Handles an incoming POST request. Records messages sent from indexer workers.

        :param req: the incoming request
        :param _: the appropriate response
        """

        task_data = worker_finished(str(req.remote_addr), req.media["error"])
        task_id = task_data.task_id
        target_index = task_data.target_index
        task_info = self.tracker.tasks[task_id]
        active_workers = task_info["active_workers"]

        # Update global task progress based on worker results
        task_info["progress"].value = task_data.percent_successful

        if task_data.percent_successful == 100:
            logging.info(f"All indexer workers succeeded! New index: {target_index}")
            index_type = target_index.split("-")[0]
            if index_type not in MEDIA_TYPES:
                index_type = "image"
            slack.verbose(f"`{index_type}`: Elasticsearch reindex complete")

            elasticsearch = elasticsearch_connect()
            indexer = TableIndexer(
                elasticsearch,
                task_id,
                task_info["callback_url"],
                task_info["progress"],
                task_info["active_workers"],
            )
            task = Process(
                target=indexer.refresh,
                kwargs={
                    "index_name": target_index,
                    "change_settings": True,
                },
            )
            task.start()
            indexer.ping_callback()
        elif task_data.percent_completed == 100:
            # All workers finished, but not all were successful. Mark
            # workers as complete and do not attempt to go live with the new
            # indices.
            active_workers.value = int(False)


class StateResource:
    @staticmethod
    def on_delete(_, __):
        """
        Forget about the last scheduled indexing job.
        """
        clear_state()


def create_api(log=True):
    """Create an instance of the Falcon API server."""

    if log:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(filename)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)

    _api = falcon.App()

    task_tracker = TaskTracker()

    _api.add_route("/", HealthResource())
    _api.add_route("/stat/{name}", StatResource())
    _api.add_route("/task", TaskResource(task_tracker))
    _api.add_route("/task/{task_id}", TaskStatus(task_tracker))
    _api.add_route("/worker_finished", WorkerFinishedResource(task_tracker))
    _api.add_route("/state", StateResource())

    return _api


api = create_api()
