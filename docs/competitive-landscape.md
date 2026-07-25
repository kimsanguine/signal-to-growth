# Competitive landscape

Research snapshot: 2026-07-25.

This review compares packaging, skill structure, domain coverage, evaluation, and safety patterns. It does not rank repositories by stars or copy their content.

| Repository | Useful pattern | Signal to Growth decision |
|---|---|---|
| [openai/plugins](https://github.com/openai/plugins) | Current Codex plugin manifest and marketplace | Use a native Codex adapter |
| [openai/skills](https://github.com/openai/skills) | Historical official examples | Do not use its deprecated distribution path |
| [anthropics/skills](https://github.com/anthropics/skills) | Concise skills and progressive disclosure | Keep `SKILL.md` focused |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Claude plugin marketplace and immutable slug | Use a native Claude adapter and stable name |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) | Portable `SKILL.md` specification | Use the common frontmatter subset |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | Multi-agent installer | Offer a fallback install path |
| [numman-ali/openskills](https://github.com/numman-ali/openskills) | Universal loading and context sync | Treat as an optional manual path |
| [MicrosoftDocs/Agent-Skills](https://github.com/MicrosoftDocs/Agent-Skills) | One skill tree with Claude and Codex manifests | Use as the closest packaging benchmark |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | Product context and broad marketing workflows | Adopt context-first work, not fixed benchmarks |
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) | PM task taxonomy and workflows | Keep our artifacts and evaluations stricter |
| [product-on-purpose/pm-skills](https://github.com/product-on-purpose/pm-skills) | Contract, trigger, router, and output evaluation | Use controlled router and committed fixtures |
| [ncklrs/startup-os-skills](https://github.com/ncklrs/startup-os-skills) | Broad growth and customer health coverage | Keep thresholds configurable |
| [sales-skills/sales](https://github.com/sales-skills/sales) | Large catalog with a strategy router | Keep the router narrow and the suite small |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | Deterministic tools and decision layers | Use scripts without platform-specific core metadata |
| [wshobson/agents](https://github.com/wshobson/agents) | Dual manifests and layered evaluation concepts | Adopt evaluation layers, not arbitrary scores |
| [obra/superpowers](https://github.com/obra/superpowers) | Strong design, plan, implementation, and approval stages | Apply hard gates to high-risk transitions |
| [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | Large catalog and provenance metadata | Keep provenance, avoid unreviewed bulk import |
| [OneWave-AI/claude-skills](https://github.com/OneWave-AI/claude-skills) | Small customer-signal tasks | Use unsupported-score claims as negative tests |

## Market gap

Large repositories compete on breadth. Domain repositories often stop at a generated report. The underserved workflow is:

```text
quote → evidence → decision → action → metric → outcome
```

Signal to Growth therefore prioritizes:

- reference integrity;
- human approval;
- project-specific policy;
- external-write boundaries;
- cross-runtime validation;
- Korean public dummy cases.

## License discipline

This repository links to the projects above as design references. It does not include their text, proprietary scoring formulas, or source files. Before adapting any future code or content, record repository, file, commit, license, adaptation type, author, and date.
