"""
A small RPC API server for scheduling ingestion of upstream data and
Elasticsearch indexing tasks.
"""

import json
import logging
import sys
import time
import uuid
from multiprocessing import Process, Value
from urllib.parse import urlparse

import falcon

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

    @staticmethod
    def _validate_create_task(request):
        """
        Validate an index creation task.
        :return: None if valid else a string containing an error message.
        """
        if request == b"":
            return "Expected JSON request body but found nothing."
        request = json.loads(request.decode("utf-8"))
        if MODEL not in request:
            return "No model supplied in request body."
        if ACTION not in request:
            return "No action supplied in request body."
        if request[ACTION] not in [x.name for x in TaskTypes]:
            return "Invalid action."
        if request[ACTION] == TaskTypes.UPDATE_INDEX.name and SINCE_DATE not in request:
            return "Received UPDATE request but no since_date."

        return None

    def on_post(self, req, resp):
        """Create a task."""
        raw_body = req.stream.read()
        request_error = self._validate_create_task(raw_body)
        if request_error:
            logging.warning(f"Invalid request made. Reason: {request_error}")
            resp.status = falcon.HTTP_400
            resp.media = {"message": request_error}
            return
        body = json.loads(raw_body.decode("utf-8"))
        model = body[MODEL]
        action = body[ACTION]
        callback_url = None
        if CALLBACK_URL in body:
            callback_url = body[CALLBACK_URL]
        since_date = body[SINCE_DATE] if SINCE_DATE in body else None
        task_id = str(uuid.uuid4())
        # Inject shared memory
        progress = Value("d", 0.0)
        finish_time = Value("d", 0.0)
        active_workers = Value(
            "i", int(False)
        )  # Tracks whether the task has any active distributed workers
        task = Task(
            model=model,
            task_type=TaskTypes[action],
            since_date=since_date,
            progress=progress,
            task_id=task_id,
            finish_time=finish_time,
            active_workers=active_workers,
            callback_url=callback_url,
        )
        task.start()
        task_id = self.tracker.add_task(
            task, task_id, action, progress, finish_time, active_workers
        )
        base_url = self._get_base_url(req)
        status_url = f"{base_url}/task/{task_id}"
        # Give the task a moment to start so we can detect immediate failure.
        # TODO: Use IPC to detect if the job launched successfully instead
        # of giving it 100ms to crash. This is prone to race conditions.
        time.sleep(0.1)
        if task.is_alive():
            resp.status = falcon.HTTP_202
            resp.media = {
                "message": "Successfully scheduled task",
                "task_id": task_id,
                "status_check": status_url,
            }
            return
        else:
            resp.status = falcon.HTTP_500
            resp.media = {
                "message": "Failed to schedule task due to an internal server "
                "error. Check scheduler logs."
            }
            return

    def on_get(self, req, resp):
        """List all indexing tasks."""
        resp.media = self.tracker.list_task_statuses()


class TaskStatus(BaseTaskResource):
    def on_get(self, req, resp, task_id):
        """Check the status of a single task."""
        task = self.tracker.id_task[task_id]

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
        task_data = worker_finished(str(req.remote_addr))
        task_id = task_data["task_id"]
        # Update progress
        self.tracker.id_progress[task_id] = task_data['percent_completed']

        if task_data['percent_completed'] == 100:
            logging.info(
                "All indexer workers finished! Attempting to promote index "
                f"{task_data['target_index']}"
            )
            index_type = task_data["target_index"].split("-")[0]
            if index_type not in MEDIA_TYPES:
                index_type = "image"
            slack.verbose(
                f"`{index_type}`: Elasticsearch reindex complete | "
                f"_Next: promote index as primary_"
            )
            active_workers = self.tracker.id_active_workers[task_id]
            f = indexer.TableIndexer.go_live
            p = Process(
                target=f, args=(task_data["target_index"], index_type, active_workers)
            )
            p.start()


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
