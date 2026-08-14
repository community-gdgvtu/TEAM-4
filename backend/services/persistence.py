"""Persistence adapters with a durable local default and optional MongoDB."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Callable, Protocol, TypeVar

from backend.core.config import Settings

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class Store(Protocol):
    backend_name: str

    def read(self) -> dict[str, Any]: ...
    def update(self, mutator: Callable[[dict[str, Any]], T]) -> T: ...
    def reset(self) -> dict[str, Any]: ...


class JsonStore:
    backend_name = "json"

    def __init__(self, path: Path, fixture_path: Path):
        self.path = path
        self.fixture_path = fixture_path
        self._thread_lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.reset()

    @contextmanager
    def _process_lock(self):
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+", encoding="utf-8")
        try:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError:
                pass
            yield
        finally:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass
            handle.close()

    def _read_file(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError("SkillPassport store root must be an object")
        return value

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def read(self) -> dict[str, Any]:
        with self._thread_lock, self._process_lock():
            return copy.deepcopy(self._read_file(self.path))

    def update(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        with self._thread_lock, self._process_lock():
            data = self._read_file(self.path)
            result = mutator(data)
            self._write_unlocked(data)
            return result

    def reset(self) -> dict[str, Any]:
        with self._thread_lock, self._process_lock():
            data = self._read_file(self.fixture_path)
            self._write_unlocked(data)
            return copy.deepcopy(data)


class MongoStore:
    """Single-document adapter preserving the same store contract."""

    backend_name = "mongodb"

    def __init__(self, client: Any, database: str, fixture_path: Path):
        self.collection = client[database]["runtime_state"]
        self.fixture_path = fixture_path
        self._lock = threading.RLock()
        if self.collection.find_one({"_id": "skillpassport"}) is None:
            self.reset()

    def read(self) -> dict[str, Any]:
        doc = self.collection.find_one({"_id": "skillpassport"}) or {}
        doc.pop("_id", None)
        return doc

    def update(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        # Sufficient for the single-process MVP; production should use transactions/version CAS.
        with self._lock:
            data = self.read()
            result = mutator(data)
            self.collection.replace_one(
                {"_id": "skillpassport"}, {"_id": "skillpassport", **data}, upsert=True
            )
            return result

    def reset(self) -> dict[str, Any]:
        with self.fixture_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.collection.replace_one(
            {"_id": "skillpassport"}, {"_id": "skillpassport", **data}, upsert=True
        )
        return copy.deepcopy(data)


def create_store(settings: Settings) -> Store:
    if settings.mongodb_uri:
        try:
            from pymongo import MongoClient

            client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=1500)
            client.admin.command("ping")
            return MongoStore(client, settings.mongodb_database, settings.fixture_path)
        except Exception as exc:  # provider failure must not break the demo
            LOGGER.warning(
                "MongoDB unavailable (%s); using local JSON store.",
                type(exc).__name__,
            )
    return JsonStore(settings.store_path, settings.fixture_path)


def find_by_id(data: dict[str, Any], collection: str, item_id: str) -> dict[str, Any] | None:
    return next((item for item in data.get(collection, []) if item.get("id") == item_id), None)


def replace_for_student(
    data: dict[str, Any], collection: str, student_id: str, values: list[dict[str, Any]]
) -> None:
    retained = [
        item for item in data.get(collection, []) if item.get("student_id") != student_id
    ]
    data[collection] = retained + values
