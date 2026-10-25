# AI Disclosure (DA3408 A4: Fair Use of AI)

**AI tool used:** Claude (Anthropic), 24 and 25 October 2026.

## Where AI was used
- **PromQL queries:** the PromQL queries on the Grafana dashboard were generated with the help of the AI assistant.
- **Regex:** one regex was generated with the AI assistant, `fstype!~"tmpfs|overlay"`, used in the disk usage query. It means "filesystem type is not tmpfs or overlay", so only the real disk is measured.
- **General help:** the AI assistant was also consulted for general coding and setup help.

## Attribution
The prompt used for every AI-generated PromQL query and for the regex is written as a comment in the configuration file `prometheus.yml`. The same prompts, with each query, are listed in `queries.md`.
