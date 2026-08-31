# DOF-ICM — Task Routing

This workspace answers questions about Mexican federal law using the DOF corpus (2024–2026).

## Tasks

| Task | What you do | Start here |
|---|---|---|
| **Query** | Given a question, locate the relevant DOF documents and produce a cited answer | `stages/01-locate/CONTEXT.md` |
| **Audit** | Given a previous answer, verify its citations and completeness | `stages/02-verify/CONTEXT.md` |
| **Setup** | Configure the workspace (year range, citation style, language) | `setup/questionnaire.md` |

## Typical flow

1. **User asks a question.**
2. **Stage 01 (locate):** read `stages/01-locate/CONTEXT.md`, use the `dof-retrieval` skill + `corpus/index/` maps to find 3–10 candidate docs, write `stages/01-locate/output/[slug]-candidates.md`.
3. **Stage 02 (verify):** read `stages/02-verify/CONTEXT.md`, read the candidate docs, extract the answer, write `stages/02-verify/output/[slug]-answer.md`.
4. **Deliver** the final answer with citations to the user.

## Rules

- **One stage, one job.** Never mix locate and verify in the same step.
- **Citations are mandatory.** Every factual claim in the final answer must cite a specific DOF document (relpath + line range + publication date).
- **If you can't find it, say so.** Do not fabricate. If the corpus doesn't contain the answer, report that with the search you tried.
- **Language.** The corpus is in Spanish. Answer in the language of the question (default: Spanish).
