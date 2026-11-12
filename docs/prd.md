Product Name: Creative-Looper

Platform: Command Line Interface (CLI) / VSCode Environment

Core Framework: CrewAI

LLM Backend: Gemini

1. Product Overview
Creative-Looper is a multi-agent CLI application for lateral thinking and concept mapping. Given two unrelated domains, it finds an obscure or highly unusual phenomenon in the primary domain and translates its underlying mechanics into the target domain. A sequential pipeline of CrewAI agents then produces Markdown output: analytical reports (the phenomenon, the mapping and a critique of its feasibility), a target-domain-only brief, and a novel pitch built on that brief (2-3 paragraphs plus a separate paragraph revealing the ending). A hostile LLM judge scores that pitch (benchmark), a reviser agent rewrites the pitch from the scoring (pitch2), and the judge scores pitch2 (benchmark2).

2. User Flow & System Execution
Initialization: The user runs `uv run creative-looper` (or `python -m creative_looper.main`) from the terminal.

Data Input: The two domains are given as positional arguments, or the CLI prompts for them:

Primary Domain (e.g., Biology, Quantum Physics)

Target Domain (e.g., Politics, Macroeconomics)

Options:

- `--loop`: instead of one run, run repeatedly on a random (primary, target) pair drawn from two list files (`--primary-file`, `--target-file`; defaults `domains/primary_domains.txt` and `domains/target_domains.txt`; one domain per line, `#` comments). `--max-runs N` limits the number of runs. Ctrl+C leaves the loop: the run in progress is abandoned (reports kept and indexed) and recorded as `cancelled`. A failed run is recorded and the loop continues; three failures in a row end it.

- `-v` / `--verbose`: show full agent output.
- `--score-run RUN_DIR`: score an existing run folder without generating anything. Cannot be combined with domains.

Environment Setup: The script creates a timestamped run directory, output/[Primary]_[Target]_[YYYYMMDD_HHMMSS]/, so repeated runs never overwrite each other. Domain names are reduced to letters, digits and underscores. A run.log is written there.

Agent Handoff: The CrewAI sequential process runs the pipeline in section 4. Every agent shares one LLM. Per-step progress and duration are printed, and a heartbeat line appears every 15 seconds during a long step.

Output Generation: Each report is written as formatted Markdown as soon as its agent finishes. At the end, an index README.md is written with links to the reports and a per-step token table (input, output and reasoning tokens).

Benchmark: When the pitch is written, the judge scores the run and writes creativity_benchmark.md and creativity_benchmark.json, plus a summary line in the run's README.md.

3. Architecture & Technical Stack
Language: Python 3.12+, managed with uv (hatchling build; console script `creative-looper`).

Orchestration: CrewAI (Sequential Process model).

LLM Integration: Gemini via crewai[google-genai]. Configured in .env:

- GEMINI_API_KEY (required)
- MODEL (default gemini/gemini-2.5-flash)
- JUDGE_MODEL (optional; defaults to MODEL; a separate, stronger model is recommended)
- LLM_TIMEOUT_SECONDS (default 120)

File System: Python pathlib for directory creation and file writing. Reports are saved by a custom task callback, because CrewAI's output_file strips absolute paths.

Reliability and Observability:

- A per-request timeout on the Google client, with up to 3 HTTP attempts, and agent-level retries of timed-out calls.
- run.log with step timings, token counts and library warnings.
- A heartbeat during long steps.
- Readable messages for a missing or invalid key, network failure, and Ctrl+C.
- If a step fails, the failed step is named and reports already written are kept.

4. Agent Definitions & Task Specifications
Steps 1-3 are analytical. Their register is neutral and critical so the user can examine the ideas. Step 4 chooses whatever voice and tone best serves the concept; there is no user-set tone option.

Agent 1: The Phenomenon Explorer
Reads: the primary domain. Writes: 01_phenomenon.md.
Goal: Select a singular, specific and unexpected phenomenon and explain its rules, causes and effects.

Agent 2: The Analogical Mapper
Reads: report 1. Writes: 02_mapping.md.
Goal: Map the phenomenon's mechanics onto the target domain as a 1:1 structural analogy (a table), defining the target-domain equivalent of every component.

Agent 3: The Analytical Critic
Reads: report 2. Writes: 03_critique.md.
Goal: Critique the mapping as a hostile reviewer (row by row, relabeling vs. true structural match; at least four problems; strict score anchors where typical mappings get 4-5): where it breaks down, what practical insights it reveals, and whether the concept could exist in the real world.

Agent 3b: The Concept Distiller
Reads: reports 2 and 3. Writes: 03b_target_brief.md.
Goal: Rewrite the mapped concept as a self-contained brief in target-domain language only: a native name, every component translated, and the critique's breakdown points restated as constraints inside the target domain.
Guardrail: the draft is checked for the primary domain's name and, by a short LLM review, for technical vocabulary that would sound out of place in the target domain. It is sent back for up to 3 rewrites, then accepted with a warning.

Decoupling requirement: Agent 4 reads only the brief. It never sees the primary domain, the mapping table or the critique, so the pitch carries target-domain context only. Some terminology may slip through and that is acceptable. At the end of a run, the count of primary-domain name mentions in the pitch is printed and logged.

Agent 4: The Story Pitch Writer
Reads: the brief. Writes: 04_pitch.md.
Goal: A 2-3 paragraph pitch for one original novel built on the concept, written to win over an agent or publisher, followed by a separate paragraph (`**The ending:**`) that reveals how the story ends, so twist execution can be judged.

Agent 5: The Story Pitch Reviser
Reads: pitch, its benchmark (scores, tropes, resemblances, red flags, harsh critique) and the brief. Writes: 05_pitch2.md.
Goal: Rewrite the pitch to fix every finding. It may depart from the brief and invent beyond it. It runs after benchmark, as its own one-task crew, because it needs the judge's output. Benchmark2 scores pitch2 and reuses benchmark's semantic distance, since the phenomenon and mapping are unchanged.

5. Creativity Benchmark
An LLM-as-judge scores a run on four criteria, each 1-10. The judge is hostile by design: weaknesses are listed before scoring, typical AI output is anchored at 3-4 and 8+ is almost never given:

- Semantic Distance: how bold and unexpected the jump between the two domains is, and whether the mapping exploits it non-obviously. Judged on the phenomenon and mapping.
- Metaphorical Density: how deeply the concept's mechanics are built into a piece rather than name-dropped. Judged on the pitch.
- Freedom from Cliché: whether the piece avoids stock AI phrasing, corporate buzzwords and predictable story shapes. Judged on the pitch.
- Uniqueness: how interchangeable the pitch is with others. A separate adversarial judge names the real works it resembles and applies hard caps (no particulars: max 4; matches a known work: max 5). Rule-based red flags (stock phrasing, generic names, overused comparable titles, abstraction, copying the brief) each subtract a point, up to 3. The uniqueness judge also records, outside the index: a trope checklist, core premise novelty (1-10), twist execution (1-10), a harsh critique, and `truly_unique` (computed in code: final uniqueness >= 8.5).

Creativity Index (out of 40) = Semantic Distance + Metaphorical Density + Freedom from Cliché + Uniqueness.

Judge design: temperature 0, written anchors for each score level, and any cliché the judge quotes must appear in the text (invented quotes are dropped). Judge calls are retried on network errors; a criterion that still cannot be scored shows as n/a, and scoring stops with a message if the judge stays unreachable. Scoring never alters the reports and can be repeated with `--score-run`.

6. Output Specifications
All deliverables are Markdown files in the run directory:

```
output/[Primary]_[Target]_[YYYYMMDD_HHMMSS]/
  README.md            index, token usage, benchmark summary
  run.log
  01_phenomenon.md
  02_mapping.md
  03_critique.md
  03b_target_brief.md
  04_pitch.md
  05_pitch2.md
  creativity_benchmark.md / .json   (scores pitch)
  creativity_benchmark2.md / .json  (scores pitch2)

output/runs.csv   (root of the output folder; one row per run: timestamps, domains, status, run folder, models, titles, every score of pitch and pitch2, index change, benchmark file paths)
```

Reports are post-processed for consistent formatting: whole-document code fences are removed, consecutive bold fields are separated into paragraphs. Each file gets a header with the domains and date.

7. Known Limitations
- The judge defaults to the same model as the generator, which tends to score its own style generously. Set JUDGE_MODEL to a different model for fairer scores.
- The brief guardrail can use all 3 rewrite rounds on hard domain pairs and can over-flag ordinary target-domain words, which can make the brief the most expensive step.
- The decoupling count matches the primary domain's name only, not its jargon.
- There is no resume option.
- Web search tools are not used. Agent 1 relies on the model's own knowledge.
