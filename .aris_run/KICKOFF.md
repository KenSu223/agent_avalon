You are running the ARIS research pipeline unattended overnight in this worktree. No human is available until morning: never stop to ask questions. Make reasonable decisions, record them in PIPELINE_STATUS.md, and keep going.

1. Read CLAUDE.md first. It holds the PI's directives (which override the idea doc where they conflict), the hard Bedrock budget rules, the model price table and the pipeline order. Then read docs/idea/idea1_memory_converges_to_prior.md and docs/idea/idea1_pilot/PILOT_PLAN.md.
2. Check that the infrastructure is up: `curl -s 127.0.0.1:8787/v1/budget` and `/home/ubuntu/llm_infra/vllmctl.sh status`. Use infra/llm.py for every model call.
3. Run the pipeline end to end, with effort: balanced, assurance: conference-ready, AUTO_PROCEED: true, human checkpoint: false, venue: ACL:
   /research-refine (input: docs/idea/idea1_memory_converges_to_prior.md; do NOT run /idea-discovery)
   → /experiment-plan (build on PILOT_PLAN.md)
   → /experiment-bridge (pilot with a strong compactor first, then the go/no-go per PILOT_PLAN §5 and PI directive 2, then the full experiments)
   → /auto-review-loop
   → /paper-writing — venue: ACL
4. Keep PIPELINE_STATUS.md and COST_LOG.md current. Commit locally at stage boundaries (never push).
5. Finish by writing PIPELINE_DONE containing the path to the final PDF.
