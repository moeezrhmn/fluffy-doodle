import asyncio
import json
from dataclasses import asdict
from functools import partial
from typing import Awaitable, Callable, Optional, Type, TypeVar

from starlette.concurrency import run_in_threadpool

from app import config as app_config

JOB_TTL_SECONDS = 2 * 60 * 60  # keep job metadata around well past the ~1h file purge window

T = TypeVar("T")


class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class QueueFullError(Exception):
    """Raised by enqueue() when max_queue_depth is set and reached — callers should return HTTP 429."""


class RedisJobQueue:
    """
    Shared job-queue base for Lane B (heavy) tools.

    Storage and the queue itself live in Redis (a list, via LPUSH/BRPOP) using
    this app's existing sync redis client — not a new async client — so
    get_job()/queue_position()/remove_job() stay plain synchronous functions,
    matching every existing call site. Job status is therefore consistent no
    matter which gunicorn worker process a status-poll request lands on,
    which an in-process dict (the old per-service pattern) cannot guarantee.

    `job_class` must be a JSON-serializable @dataclass (str/int/float/bool/None
    fields only). `process(job)` is supplied by the service module and does
    the actual work, mutating extra fields onto `job` as needed (e.g.
    size_before/size_after) — this class handles the QUEUED -> PROCESSING ->
    DONE/ERROR transition and persistence around it.
    """

    def __init__(
        self,
        name: str,
        job_class: Type[T],
        process: Callable[[T], Awaitable[None]],
        num_workers: int = 2,
        max_queue_depth: Optional[int] = None,
    ):
        self.name = name
        self.job_class = job_class
        self.process = process
        self.num_workers = num_workers
        self.max_queue_depth = max_queue_depth

    def _queue_key(self) -> str:
        return f"jobqueue:{self.name}:queue"

    def _job_key(self, job_id: str) -> str:
        return f"jobqueue:{self.name}:job:{job_id}"

    def _save(self, job: T) -> None:
        app_config.redis_client.set(self._job_key(job.job_id), json.dumps(asdict(job)), ex=JOB_TTL_SECONDS)

    async def enqueue(self, job: T) -> T:
        if self.max_queue_depth is not None:
            depth = app_config.redis_client.llen(self._queue_key())
            if depth >= self.max_queue_depth:
                raise QueueFullError(f"'{self.name}' queue is full ({depth} jobs pending). Try again shortly.")

        self._save(job)
        app_config.redis_client.lpush(self._queue_key(), job.job_id)
        return job

    def get_job(self, job_id: str) -> Optional[T]:
        raw = app_config.redis_client.get(self._job_key(job_id))
        return self.job_class(**json.loads(raw)) if raw else None

    def queue_position(self, job_id: str) -> int:
        idx = app_config.redis_client.lpos(self._queue_key(), job_id)
        if idx is None:
            return 0
        length = app_config.redis_client.llen(self._queue_key())
        return length - idx

    def remove_job(self, job_id: str) -> None:
        app_config.redis_client.lrem(self._queue_key(), 0, job_id)
        app_config.redis_client.delete(self._job_key(job_id))

    def start_workers(self) -> None:
        for _ in range(self.num_workers):
            asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while True:
            try:
                item = await run_in_threadpool(partial(app_config.redis_client.brpop, [self._queue_key()], timeout=5))
            except Exception as e:
                print(f"[job_queue:{self.name}] Redis error in worker loop: {e}")
                await asyncio.sleep(1)
                continue

            if item is None:
                continue

            _, job_id = item
            job_id = job_id.decode() if isinstance(job_id, bytes) else job_id
            job = self.get_job(job_id)
            if job is None:
                continue

            job.status = JobStatus.PROCESSING
            self._save(job)
            try:
                await self.process(job)
                job.status = JobStatus.DONE
            except Exception as e:
                job.status = JobStatus.ERROR
                job.error = str(e)
                print(f"[job_queue:{self.name}] Job {job_id} failed: {e}")
            self._save(job)
