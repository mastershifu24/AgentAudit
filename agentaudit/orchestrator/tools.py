"""OpenAI tool definitions for the orchestrator."""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_planner",
            "description": "Create a 2-step plan for the task. Use when no plan exists yet.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_worker",
            "description": (
                "Execute the current plan step. Use when plan exists and "
                "there is no worker output for the current step yet."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_judge",
            "description": "Quality-check the worker output against the assigned step.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_worker_retry",
            "description": "Revise worker output after a failed judge verdict. Only if retries remain.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_pipeline",
            "description": (
                "Mark complete when all_steps_passed is true, "
                "or judge failed with no retries left."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TOOL_TO_SPECIALIST = {
    "run_planner": "planner",
    "run_worker": "worker",
    "run_judge": "judge",
    "run_worker_retry": "worker_retry",
}
