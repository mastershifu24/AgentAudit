import json
from dataclasses import dataclass, field


@dataclass
class PipelineState:
    task: str
    plan: dict | None = None
    current_step: str | None = None
    current_step_index: int = 0
    worker_output: str | None = None
    verdict: dict | None = None
    worker_attempts: int = 0
    max_worker_attempts: int = 2
    last_orchestrator_reason: str = ""
    finished: bool = False
    step_outputs: dict[int, str] = field(default_factory=dict)
    search_context: str = ""

    def total_steps(self) -> int:
        if not self.plan:
            return 0
        return len(self.plan.get("steps", []))

    def has_more_steps(self) -> bool:
        return self.current_step_index + 1 < self.total_steps()

    def all_steps_passed(self) -> bool:
        return self.total_steps() > 0 and len(self.step_outputs) >= self.total_steps()

    def sync_current_step(self) -> None:
        if not self.plan:
            self.current_step = None
            return
        steps = self.plan["steps"]
        if self.current_step_index < len(steps):
            self.current_step = steps[self.current_step_index]["action"]
        else:
            self.current_step = None

    def record_step_pass(self) -> None:
        if self.worker_output is not None:
            self.step_outputs[self.current_step_index] = self.worker_output

    def advance_to_next_step(self) -> None:
        self.current_step_index += 1
        self.worker_output = None
        self.verdict = None
        self.worker_attempts = 0
        self.sync_current_step()

    def summary(self) -> str:
        return json.dumps(
            {
                "current_step_index": self.current_step_index,
                "total_steps": self.total_steps(),
                "steps_passed": len(self.step_outputs),
                "all_steps_passed": self.all_steps_passed(),
                "current_step": self.current_step,
                "has_plan": self.plan is not None,
                "has_worker_output": self.worker_output is not None,
                "worker_attempts": self.worker_attempts,
                "max_worker_attempts": self.max_worker_attempts,
                "last_verdict_pass": self.verdict.get("pass") if self.verdict else None,
                "last_verdict_score": self.verdict.get("score") if self.verdict else None,
                "finished": self.finished,
            },
            indent=2,
        )
