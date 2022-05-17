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

import ingestion_server.indexer as indexer
from ingestion_server import slack
from ingestion_server.constants.media_types import MEDIA_TYPES
from ingestion_server.state import clear_state, worker_finished
from ingestion_server.tasks import Task, TaskTracker, TaskTypes


MODEL = "model"
ACTION = "action"
CALLBACK_URL = "callback_url"
SINCE_DATE = "since_date"


class HealthResource:
    @staticmethod
    def on_get(_, resp):
        resp.status = falcon.HTTP_200
        resp.media = {"status": "200 OK"}


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
                    "enum": list(type.name for type in TaskTypes),
                },
                # Accepts all forms described in the PostgreSQL documentation:
                # https://www.postgresql.org/docs/current/datatype-datetime.html
                "since_date": {
                    "type": "string",
                },
            },
            "required": ["model", "action"],
            "if": {"properties": {"action": {"const": TaskTypes.UPDATE_INDEX.name}}},
            "then": {"required": ["since_date"]},
        }
    )
    def on_post(self, req: falcon.Request, res: falcon.Response):
        """
        Handles an incoming POST request.

        :param req: the incoming request
        :param res: the appropriate response
        """

        body = req.get_media()

        # Required fields
        model = body["model"]
        action = TaskTypes[body["action"]]

        # Optional fields
        callback_url = body.get("callback_url")
        since_date = body.get("since_date")

        # Generated fields
        task_id = str(uuid.uuid4())

        # Inject shared memory
        progress = Value("d", 0.0)
        finish_time = Value("d", 0.0)
        active_workers = Value("i", int(False))
        """whether task has any active distributed workers"""

        # Create ``Task`` instance
        task = Task(
            task_id=task_id,
            model=model,
            task_type=action,
            callback_url=callback_url,
            since_date=since_date,
            progress=progress,
            finish_time=finish_time,
            active_workers=active_workers,
        )
        task.start()

        task_id = self.tracker.add_task(
            task,
            task_id,
            action,
            progress,
            finish_time,
            active_workers,
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
                "message": "Successfully scheduled task.",
                "task_id": task_id,
                "status_check": status_url,
            }
        else:
            res.status = falcon.HTTP_500
            res.media = {
                "message": (
                    "Failed to schedule task due to an internal server error. "
                    "Check scheduler logs."
                )
            }

    def on_get(self, req, resp):
        """List all indexing tasks."""
        resp.media = self.tracker.list_task_statuses()


class TaskStatus(BaseTaskResource):
    def on_get(self, req, resp, task_id):
        """Check the status of a single task."""
        task = self.tracker.id_task.get(task_id)
        if task is None:
            resp.status = falcon.HTTP_404
            resp.media = {"message": f"No task found with id {task_id}"}
            return

        percent_completed = self.tracker.id_progress[task_id].value
        active_workers = bool(self.tracker.id_active_workers[task_id].value)
        active = task.is_alive() or active_workers

        resp.media = {
            "active": active,
            "percent_completed": percent_completed,
            "error": percent_completed < 100 and not active,
        }


class WorkerFinishedResource(BaseTaskResource):
    """
    For notifying ingestion server that an indexing worker has finished its
    task.
    """

    def on_post(self, req, _):
        task_data = worker_finished(str(req.remote_addr), req.media["error"])
        task_id = task_data.task_id
        target_index = task_data.target_index
        active_workers = self.tracker.id_active_workers[task_id]

        # Update global task progress based on worker results
        self.tracker.id_progress[task_id].value = task_data.percent_successful

        if task_data.percent_successful == 100:
            logging.info(
                "All indexer workers succeeded! Attempting to promote index "
                f"{target_index}"
            )
            index_type = target_index.split("-")[0]
            if index_type not in MEDIA_TYPES:
                index_type = "image"
            slack.verbose(
                f"`{index_type}`: Elasticsearch reindex complete | "
                f"_Next: promote index as primary_"
            )
            f = indexer.TableIndexer.go_live
            p = Process(target=f, args=(target_index, index_type, active_workers))
            p.start()
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
    _api.add_route("/task", TaskResource(task_tracker))
    _api.add_route("/task/{task_id}", TaskStatus(task_tracker))
    _api.add_route("/worker_finished", WorkerFinishedResource(task_tracker))
    _api.add_route("/state", StateResource())

    return _api


api = create_api()
