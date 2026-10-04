"""Multi-core headless plotting engine process pool and client bridge.

Executes all Matplotlib and Cartopy plotting routines across multiple isolated OS
processes. Supports immediate cancellation of obsolete jobs, multi-core utilization,
and engine status tracking for UI indicators.
"""

from __future__ import annotations

import multiprocessing as mp
from multiprocessing.connection import Connection, wait
import os
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from xotplot.constants import DEFAULT_ENGINE_WORKERS


def _engine_worker_main(conn: Connection) -> None:
    """Entry point for isolated plotting & IO engine child process."""
    import logging
    import warnings
    import matplotlib
    matplotlib.use("Agg")
    import xarray as xr
    xr.set_options(use_new_combine_kwarg_defaults=True)
    warnings.filterwarnings("ignore", category=FutureWarning, module="cfgrib.*")
    warnings.filterwarnings("ignore", category=FutureWarning, module="xarray.*")
    logging.getLogger("cfgrib").setLevel(logging.ERROR)
    logging.getLogger("cfgrib.messages").setLevel(logging.ERROR)

    from xotplot.engine.plotting.renderer import execute_render_job
    from xotplot.engine.io.registry import DatasetRegistry
    from xotplot.engine.io import open_dataset
    from xotplot.spec import OpenDatasetRequest

    registry = DatasetRegistry()

    while True:
        try:
            msg = conn.recv()
        except (EOFError, KeyboardInterrupt):
            break

        if not isinstance(msg, dict):
            continue

        cmd = msg.get("command")
        if cmd == "shutdown":
            registry.close_all()
            break

        job_id = msg.get("job_id", "")

        # Handle IO commands
        if cmd == "io_open":
            try:
                raw_req = msg.get("request", {})
                req = OpenDatasetRequest.model_validate(raw_req)
                _, metadata = open_dataset(req, registry=registry)
                conn.send({
                    "job_id": job_id,
                    "success": True,
                    "metadata": metadata.model_dump(),
                })
            except Exception as exc:
                conn.send({
                    "job_id": job_id,
                    "success": False,
                    "error": str(exc),
                })
            continue

        if cmd == "io_close":
            ds_id = msg.get("dataset_id", "")
            registry.close(ds_id)
            conn.send({"job_id": job_id, "success": True})
            continue

        if cmd == "io_set_active":
            ds_id = msg.get("dataset_id", "")
            try:
                registry.set_active(ds_id)
                conn.send({"job_id": job_id, "success": True})
            except Exception as exc:
                conn.send({"job_id": job_id, "success": False, "error": str(exc)})
            continue

        # Handle Rendering commands
        job_type = msg.get("job_type", "")
        params = msg.get("params", {})
        width = msg.get("width", 8.0)
        height = msg.get("height", 6.0)
        dpi = msg.get("dpi", 100)

        # Inject active dataset if this is a field or slice_histogram render job
        if job_type in ("field", "slice_histogram") and "ds" not in params:
            try:
                target_ds_id = params.get("dataset_id")
                params["ds"] = registry.get(target_ds_id)
            except Exception as exc:
                conn.send({
                    "job_id": job_id,
                    "success": False,
                    "error": f"Failed to retrieve dataset from registry: {exc}",
                })
                continue

        try:
            image_data = execute_render_job(
                job_type=job_type,
                params=params,
                width=width,
                height=height,
                dpi=dpi,
            )
            conn.send({
                "job_id": job_id,
                "success": True,
                "image_data": image_data,
            })
        except Exception as exc:
            conn.send({
                "job_id": job_id,
                "success": False,
                "error": str(exc),
            })


class WorkerSlot:
    """Tracks state and communication channel of a child process worker."""

    def __init__(self, process: mp.Process, conn: Connection) -> None:
        self.process = process
        self.conn = conn
        self.current_job_id: Optional[str] = None
        self.current_channel: Optional[str] = None
        self.is_busy: bool = False


class EngineProcessPool:
    """Multi-core process pool managing isolated rendering workers with instant cancellation."""

    def __init__(self, num_workers: int = DEFAULT_ENGINE_WORKERS) -> None:
        self._ctx = mp.get_context("spawn")
        self._num_workers = max(1, num_workers)
        self._workers: List[WorkerSlot] = []
        self._queue: List[dict] = []
        self._cancelled_jobs: set[str] = set()
        self._lock = threading.RLock()
        self._running = True
        self._loaded_datasets: List[dict] = []

        for _ in range(self._num_workers):
            self._workers.append(self._spawn_worker())

    def _spawn_worker(self) -> WorkerSlot:
        p_conn, c_conn = self._ctx.Pipe()
        p = self._ctx.Process(target=_engine_worker_main, args=(c_conn,), daemon=True)
        p.start()
        return WorkerSlot(process=p, conn=p_conn)

    def _terminate_and_respawn(self, slot: WorkerSlot) -> None:
        """Kill dead worker and launch replacement without blocking caller thread."""
        try:
            slot.process.terminate()
            slot.process.join(timeout=0.05)
        except Exception:
            pass
        try:
            slot.conn.close()
        except Exception:
            pass

        new_slot = self._spawn_worker()
        slot.process = new_slot.process
        slot.conn = new_slot.conn
        slot.current_job_id = None
        slot.current_channel = None
        slot.is_busy = False

        # Replay dataset ingestion in a background thread to prevent GUI lockup
        if self._loaded_datasets:
            datasets_to_replay = list(self._loaded_datasets)
            target_conn = slot.conn

            def _replay() -> None:
                for ds_req in datasets_to_replay:
                    try:
                        target_conn.send({
                            "command": "io_open",
                            "job_id": str(uuid.uuid4()),
                            "request": ds_req,
                        })
                        target_conn.recv()
                    except Exception:
                        pass

            threading.Thread(target=_replay, daemon=True).start()

    def cancel_channel(self, channel: str) -> None:
        """Cancel and drop all pending and active jobs on a channel immediately without blocking."""
        with self._lock:
            # Mark running jobs on this channel as cancelled so their output is discarded
            for slot in self._workers:
                if slot.is_busy and slot.current_channel == channel and slot.current_job_id:
                    self._cancelled_jobs.add(slot.current_job_id)
            # Mark and drop unstarted queued jobs
            for j in self._queue:
                if j.get("channel") == channel and j.get("job_id"):
                    self._cancelled_jobs.add(j["job_id"])
            self._queue = [j for j in self._queue if j.get("channel") != channel]

    def submit_job(
        self,
        job_id: str,
        job_type: str,
        params: dict,
        channel: str = "default",
        width: float = 8.0,
        height: float = 6.0,
        dpi: int = 100,
        cancel_previous: bool = True,
    ) -> None:
        """Submit job to pool, canceling any previous jobs on the same channel if requested."""
        with self._lock:
            if cancel_previous and channel:
                self.cancel_channel(channel)

            job = {
                "command": "render",
                "job_id": job_id,
                "job_type": job_type,
                "params": params,
                "channel": channel,
                "width": width,
                "height": height,
                "dpi": dpi,
            }
            self._dispatch_or_queue(job)

    def _dispatch_or_queue(self, job: dict) -> None:
        """Find an idle worker or queue the job."""
        idle_slot = next((s for s in self._workers if not s.is_busy), None)
        if idle_slot:
            idle_slot.is_busy = True
            idle_slot.current_job_id = job["job_id"]
            idle_slot.current_channel = job.get("channel")
            idle_slot.conn.send(job)
        else:
            self._queue.append(job)

    def dispatch_next(self, slot: WorkerSlot) -> None:
        """Dispatch next pending non-cancelled job to a newly idle worker."""
        with self._lock:
            slot.is_busy = False
            slot.current_job_id = None
            slot.current_channel = None
            while self._queue:
                next_job = self._queue.pop(0)
                if next_job.get("job_id") in self._cancelled_jobs:
                    self._cancelled_jobs.discard(next_job["job_id"])
                    continue
                slot.is_busy = True
                slot.current_job_id = next_job["job_id"]
                slot.current_channel = next_job.get("channel")
                slot.conn.send(next_job)
                break

    @property
    def _process(self) -> Optional[mp.Process]:
        """Backward compatibility handle to primary child process."""
        return self._workers[0].process if self._workers else None

    @property
    def is_alive(self) -> bool:
        with self._lock:
            return any(s.process.is_alive() for s in self._workers)

    def render_sync(
        self,
        job_type: str,
        params: dict,
        channel: str = "sync",
        width: float = 8.0,
        height: float = 6.0,
        dpi: int = 100,
    ) -> bytes:
        """Synchronously render a plot on an idle worker and return PNG image bytes."""
        job_id = str(uuid.uuid4())
        job = {
            "command": "render",
            "job_id": job_id,
            "job_type": job_type,
            "params": params,
            "channel": channel,
            "width": width,
            "height": height,
            "dpi": dpi,
        }
        with self._lock:
            idle_slot = next((s for s in self._workers if not s.is_busy), self._workers[0])
            idle_slot.is_busy = True
            idle_slot.current_job_id = job_id
            idle_slot.current_channel = channel
            idle_slot.conn.send(job)
            resp = idle_slot.conn.recv()
            idle_slot.is_busy = False
            idle_slot.current_job_id = None
            idle_slot.current_channel = None

        if resp.get("success"):
            return resp["image_data"]
        raise RuntimeError(resp.get("error", "Plot engine render failed"))

    def open_dataset_sync(
        self,
        file_path: str,
        format_override: str = "auto",
        dataset_id: Optional[str] = None,
    ) -> Any:
        """Synchronously open and ingest a dataset across the engine workers.

        Returns:
            DatasetMetadata instance describing loaded dataset.
        """
        from xotplot.spec import DatasetMetadata, OpenDatasetRequest

        assigned_id = dataset_id or str(uuid.uuid4())
        req = OpenDatasetRequest(
            file_path=file_path,
            format_override=format_override,  # type: ignore[arg-type]
            dataset_id=assigned_id,
        )
        job_id = str(uuid.uuid4())
        msg = {
            "command": "io_open",
            "job_id": job_id,
            "request": req.model_dump(),
        }

        # Dispatch open to all workers so each process in pool has dataset registered
        with self._lock:
            meta = None
            for slot in self._workers:
                slot.is_busy = True
                slot.current_channel = "sync"
                slot.conn.send(msg)
                resp = slot.conn.recv()
                slot.is_busy = False
                slot.current_channel = None
                if not resp.get("success"):
                    raise RuntimeError(resp.get("error", "Failed to open dataset in engine worker"))
                if meta is None:
                    meta = DatasetMetadata.model_validate(resp["metadata"])
            self._loaded_datasets.append(req.model_dump())
            return meta

    @property
    def busy_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._workers if s.is_busy) + len(self._queue)

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._queue.clear()
            for slot in self._workers:
                try:
                    slot.conn.send({"command": "shutdown"})
                    slot.process.join(timeout=0.1)
                except Exception:
                    pass
                if slot.process.is_alive():
                    slot.process.terminate()


_GLOBAL_ENGINE_POOL: Optional[EngineProcessPool] = None


def get_engine_pool() -> EngineProcessPool:
    """Return the singleton multi-core EngineProcessPool instance."""
    global _GLOBAL_ENGINE_POOL
    if _GLOBAL_ENGINE_POOL is None or not _GLOBAL_ENGINE_POOL._running:
        _GLOBAL_ENGINE_POOL = EngineProcessPool()
    return _GLOBAL_ENGINE_POOL


# Backward-compatible alias
EngineClient = EngineProcessPool
get_engine_client = get_engine_pool


try:
    from PyQt6.QtCore import QObject, pyqtSignal

    class QtEngineBridge(QObject):
        """PyQt6 QObject bridge with multi-core dispatch, instant cancellation, and status tracking."""

        job_completed = pyqtSignal(str, bytes)
        job_failed = pyqtSignal(str, str)
        status_changed = pyqtSignal(bool, int)  # is_busy: bool, active_jobs: int

        def __init__(self, parent: Optional[QObject] = None) -> None:
            super().__init__(parent)
            self._pool = get_engine_pool()
            self._running = True
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

        def _reader_loop(self) -> None:
            while self._running:
                conns: list[Connection] = []
                with self._pool._lock:
                    conns = [
                        s.conn for s in self._pool._workers
                        if not s.conn.closed and s.current_channel != "sync"
                    ]

                if not conns:
                    threading.Event().wait(0.05)
                    continue

                try:
                    ready = wait(conns, timeout=0.05)
                except Exception:
                    continue

                for ready_conn in ready:
                    with self._pool._lock:
                        slot = next((s for s in self._pool._workers if s.conn is ready_conn), None)
                        if not slot or slot.current_channel == "sync":
                            continue

                        try:
                            resp = ready_conn.recv()
                        except (EOFError, OSError):
                            self._pool._terminate_and_respawn(slot)
                            continue

                        job_id = resp.get("job_id", "")
                        is_success = resp.get("success", False)
                        img_data = resp.get("image_data", b"")
                        err_msg = resp.get("error", "Engine error")

                        was_cancelled = job_id in self._pool._cancelled_jobs
                        if was_cancelled:
                            self._pool._cancelled_jobs.discard(job_id)

                        self._pool.dispatch_next(slot)
                        active = self._pool.busy_count

                    if was_cancelled:
                        self.status_changed.emit(active > 0, active)
                        continue

                    # Emit Qt signals outside lock
                    if is_success:
                        self.job_completed.emit(job_id, img_data)
                    else:
                        self.job_failed.emit(job_id, err_msg)

                    self.status_changed.emit(active > 0, active)

        def submit(
            self,
            job_type: str,
            params: dict,
            channel: str = "default",
            width: float = 8.0,
            height: float = 6.0,
            dpi: int = 100,
            cancel_previous: bool = True,
        ) -> str:
            """Submit a render job with channel-based cancellation and status notification."""
            job_id = str(uuid.uuid4())
            self._pool.submit_job(
                job_id=job_id,
                job_type=job_type,
                params=params,
                channel=channel,
                width=width,
                height=height,
                dpi=dpi,
                cancel_previous=cancel_previous,
            )
            self.status_changed.emit(True, self._pool.busy_count)
            return job_id

        def cancel(self, channel: str) -> None:
            """Explicitly cancel all jobs on a channel and notify status change."""
            self._pool.cancel_channel(channel)
            self.status_changed.emit(self._pool.busy_count > 0, self._pool.busy_count)

        def shutdown(self) -> None:
            self._running = False
            self._pool.shutdown()

    _GLOBAL_QT_BRIDGE: Optional[QtEngineBridge] = None

    def get_qt_engine_bridge() -> QtEngineBridge:
        """Return the singleton QtEngineBridge instance for PyQt6 UI components."""
        global _GLOBAL_QT_BRIDGE
        if _GLOBAL_QT_BRIDGE is None:
            _GLOBAL_QT_BRIDGE = QtEngineBridge()
        return _GLOBAL_QT_BRIDGE

except ImportError:
    pass
