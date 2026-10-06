You are resuming an unattended ARIS research pipeline in this worktree; a previous session ended. No human is available: never stop to ask questions.

1. Re-read CLAUDE.md (PI directives, hard budget rules, pipeline order).
2. Work out where things stand from PIPELINE_STATUS.md, COST_LOG.md, .aris/runs/*.json, REVIEW_STATE.json (if present), git log, and the latest experiment logs. Check `curl -s 127.0.0.1:8787/v1/budget` and `/home/ubuntu/llm_infra/vllmctl.sh status`; restart vLLM with `vllmctl.sh start` or the proxy with `/home/ubuntu/llm_infra/proxyctl.sh start` if either is down.
3. Continue from the first unfinished stage of: /research-refine → /experiment-plan → /experiment-bridge → /auto-review-loop → /paper-writing — venue: ACL (effort: balanced, assurance: conference-ready, AUTO_PROCEED: true). If a long experiment process is still running, monitor it rather than restarting it.
4. Keep PIPELINE_STATUS.md and COST_LOG.md current, commit locally at stage boundaries (never push), and write PIPELINE_DONE (path to the final PDF) when the paper is finished.
