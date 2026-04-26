The exercise is to build a small compensation analyst agent: an LLM-powered system that answers natural language questions about employee comp by reasoning over structured data. This is directly modeled after Compensation Agent, the agentic product we're building at Pave.

We provide fixture data (employees, market benchmarks, comp bands). You design and build everything else, the tool layer, the agent architecture, and an evaluation approach. The README has the full details.

A few things to know:
Time budget is 120 minutes. We're evaluating design decisions, not polish. Cut scope deliberately and tell us what you cut.
An Anthropic API key is included in the .env.example file.
We expect you to use AI-assisted tooling (Claude Code, etc.). Be transparent in your DECISIONS.md about what you used and where.