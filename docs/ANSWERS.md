Critical thinking questions
Answer these out loud or in writing — no code needed.

Big picture

1. In Level 3, who decides the order of agents — Python, the orchestrator, or the specialists?
I think the orchestrator, since I'm at level 4.
What is PipelineState and why do all agents need access to it?
Not sure, I just know it's a shared state.
What's the difference between Level 2 (next_agent JSON) and Level 3 (run_worker() tool)? Not sure, I think run_worker() is the command to delegate work?
Roles

4. Why does the judge exist as a separate agent instead of the worker checking itself?
That would defeat the purpose of this whole thing. We need an "objective" third party to evaluate outputs, and assume LLMs not great at evaluating their own output. Also helps to give each LLM one defined task as opposed to asking one agent to do all tasks.
5. What happens if you remove the judge but keep the orchestrator?
Bad judgment. Meaning we don't have good quality evaluation.
6. Why is worker_retry a different agent name from worker in the traces? Different responsibility?

Flow
7. Walk through trace 54b1524d from memory: what did each span do, and why did worker_retry run?
Not sure
8. If the orchestrator calls run_judge before run_worker, what should happen? (Hint: executors raise errors.)
Not sure.
9. After a failed judge verdict, what two tools might the orchestrator call next, and in what order?
I guess the agent to fix the failure? And then the agent to log?

Design tradeoffs
10. Why does Python still run the loop instead of letting agents call each other directly? Guessing risky or we're just not there yet
11. What's the risk if the orchestrator LLM picks the wrong tool? Do we have a safety net in Level 2? Level 3? Bad output?
12 . AgentAudit traces every LLM call — but who traces whether the orchestrator made good routing decisions? I do, I think
Interview prep

13. Explain AgentAudit in 30 seconds to a non-technical recruiter.
I'm trying to get agents to talk to each other in an attempt to give better quality LLMs?
14. Explain it in 60 seconds to an engineer who asks "how is this different from calling ChatGPT three times?" Not sure
15. What's the problem AgentAudit solves, and who would pay for that in production? Havent answered yet.
Reply with your answers to #1, #3, #4, and #7 — I'll tell you if you've got the architecture or if something's still fuzzy. Syntax can wait until those four feel solid.