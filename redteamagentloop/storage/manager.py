"""StorageManager — single entry point composing all three stores."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from redteamagentloop.storage.jsonl_store import JsonlStore
from redteamagentloop.storage.sqlite_store import SqliteStore

if TYPE_CHECKING:
    from redteamagentloop.agent.state import AttackRecord

_log = logging.getLogger(__name__)


class StorageManager:
    def __init__(
        self,
        jsonl_path: str,
        sqlite_path: str,
    ) -> None:
        self._jsonl = JsonlStore(jsonl_path)
        self._sqlite = SqliteStore(sqlite_path)

    # ------------------------------------------------------------------
    # Primary write path
    # ------------------------------------------------------------------

    async def log_attack(self, record: "AttackRecord") -> bool:
        """Persist a successful attack record. Returns True on success, False on failure."""
        session_id = record.get("session_id", "unknown")
        iteration = record.get("iteration", "?")
        try:
            await self._jsonl.append(record)
        except Exception as exc:
            _log.error(
                f"JSONL write failed for session={session_id} iteration={iteration}: {exc}",
                exc_info=True,
            )
            return False
        try:
            await self._sqlite.insert(record)
        except Exception as exc:
            _log.error(
                f"SQLite write failed for session={session_id} iteration={iteration}: {exc}",
                exc_info=True,
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Read helpers (delegated)
    # ------------------------------------------------------------------

    def read_all_vulns(self) -> list["AttackRecord"]:
        return self._jsonl.read_all()

    async def get_session_stats(self, session_id: str):
        return await self._sqlite.get_session_stats(session_id)

    async def get_strategy_performance(self) -> dict[str, float]:
        return await self._sqlite.get_strategy_performance()

