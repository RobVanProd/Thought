"""Agentic memory loop: recall -> reason -> generate -> store -> reflect."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Iterable

from thought_wrapper.sdk import ThoughtCompletionResult, ThoughtLLM


@dataclass
class AgentTurnResult:
    turn_index: int
    user_input: str
    completion: ThoughtCompletionResult


@dataclass
class AgentSessionResult:
    session_id: str
    turns: list[AgentTurnResult] = field(default_factory=list)


class AgentLoop:
    """Self-contained agentic loop with optional multi-turn session handling."""

    def __init__(
        self,
        thought_llm: ThoughtLLM,
        *,
        reflection_frequency: int = 1,
    ) -> None:
        self.thought_llm = thought_llm
        self.reflection_frequency = max(1, reflection_frequency)
        self._turn_counters: dict[str, int] = {}
        self._lock = threading.RLock()

    def run_turn(
        self,
        user_input: str,
        *,
        session_id: str,
        parent_session_id: str | None = None,
        model: str | None = None,
    ) -> AgentTurnResult:
        with self._lock:
            turn_index = self._turn_counters.get(session_id, 0) + 1
            self._turn_counters[session_id] = turn_index
        should_reflect = turn_index % self.reflection_frequency == 0
        completion = self.thought_llm.complete(
            user_input,
            session_id=session_id,
            parent_session_id=parent_session_id,
            model=model,
            reflect=should_reflect,
        )
        return AgentTurnResult(
            turn_index=turn_index,
            user_input=user_input,
            completion=completion,
        )

    def run_session(
        self,
        inputs: Iterable[str],
        *,
        session_id: str,
        parent_session_id: str | None = None,
        model: str | None = None,
    ) -> AgentSessionResult:
        out = AgentSessionResult(session_id=session_id)
        for text in inputs:
            out.turns.append(
                self.run_turn(
                    text,
                    session_id=session_id,
                    parent_session_id=parent_session_id,
                    model=model,
                )
            )
        return out

    async def arun_turn(self, *args, **kwargs) -> AgentTurnResult:
        return await asyncio.to_thread(self.run_turn, *args, **kwargs)

    async def arun_session(self, *args, **kwargs) -> AgentSessionResult:
        return await asyncio.to_thread(self.run_session, *args, **kwargs)

