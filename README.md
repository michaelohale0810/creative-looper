# Creative Looper

A multi-agent CLI built on [CrewAI](https://www.crewai.com/) and Gemini. Give it two unrelated domains, and a six-agent pipeline finds an unusual phenomenon in the first, maps its mechanics onto the second, critiques the mapping, distills a target-domain brief, and writes a short novel pitch built on it, ending with a paragraph that reveals the ending. A hostile judge scores that pitch (benchmark), a reviser agent rewrites it from the scoring (pitch2), and the judge scores pitch2 (benchmark2).

See [docs/prd.md](docs/prd.md) for the product definition.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and a [Gemini API key](https://aistudio.google.com/apikey).

```sh
uv sync
cp .env.example .env   # then edit .env
```

`.env` settings:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Required for the Gemini provider. Your Gemini API key. |
| `LLM_PROVIDER` | Optional. `gemini` (online, default) or `local` (Ollama). The `--provider` flag overrides it. |
| `LOCAL_MODEL` | Required for the local provider. Name of the model in Ollama, e.g. `gemma4`. Served as `ollama/<name>`. |
| `OLLAMA_HOST` | Optional. Ollama server URL, default `http://localhost:11434`. |
| `MODEL` | Optional. CrewAI model id, default `gemini/gemini-2.5-flash`. |
| `JUDGE_MODEL` | Optional. Model that scores creativity (see below); defaults to `MODEL`. A separate, stronger model is better. |
| `LLM_TIMEOUT_SECONDS` | Optional. Per-request timeout, default `120`. A request that stalls longer is cancelled and retried (up to 3 attempts per step) instead of hanging. |

## Usage

```sh
uv run creative-looper Biology Politics --provider local   # local Ollama model (LOCAL_MODEL)
uv run creative-looper Biology Politics --provider gemini  # online Gemini (default)
uv run creative-looper                        # prompts for both domains
uv run creative-looper Biology Politics       # skip the prompts
uv run creative-looper "Quantum Physics" Macroeconomics --verbose
```

When prompted, you are asked for the primary and target domains. The phenomenon, mapping and critique are written in a neutral, analytical register so you can examine the ideas critically; the pitch agent chooses whatever voice best fits the concept.

Every run does the whole cycle: pitch, benchmark, pitch2, benchmark2. There are no switches for it. To score an existing run folder without generating anything, use `--score-run` (see below); it scores pitch and, if the run has one, pitch2.

### Looping on random domains

Put your domains in two text files, one per line (blank lines and lines starting with `#` are ignored). Sample lists ship in `domains/primary_domains.txt` and `domains/target_domains.txt`.

```sh
uv run creative-looper --loop                    # run until you stop it
uv run creative-looper --loop --max-runs 10      # or stop after 10 runs
uv run creative-looper --loop --primary-file my_primaries.txt --target-file my_targets.txt
```

Each run draws a random primary and a random target (never the same domain twice), then does the whole cycle. **Press Ctrl+C to stop.** The run in progress is abandoned immediately, its reports so far are kept and indexed in its folder, and it is recorded as `cancelled`. A single failed run is recorded and the loop carries on; three failures in a row end it.

### The run log (`output/runs.csv`)

Every run, single or looped, appends one row to `runs.csv` in the root of the output folder, however it ended:

| Columns | Content |
| --- | --- |
| `started_at`, `finished_at` | ISO date-times |
| `primary_domain`, `target_domain` | the pair |
| `status`, `error` | `complete`, `cancelled` (Ctrl+C) or `failed`, and the error if any |
| `run_folder`, `model`, `judge_model` | where the run's files are, and the models used |
| `pitch_title`, `pitch2_title` | the novel titles |
| `pitch_*`, `pitch2_*` | the index and every score of each pitch: `index`, `semantic_distance`, `metaphorical_density`, `freedom_from_cliche`, `uniqueness`, `core_premise_novelty`, `twist_execution`, `truly_unique`, `red_flags`, `red_flag_penalty` |
| `index_change` | pitch2's index minus pitch's |
| `benchmark_file`, `benchmark2_file` | the full benchmark reports, relative to the output folder |

Anything a run never reached (a cancelled or failed run) is left blank. If an existing `runs.csv` has different columns (after an upgrade), it is renamed aside to `runs_<timestamp>.csv` and a fresh one is started.

Quote domains that contain spaces. By default you see one progress line per agent; `-v` / `--verbose` shows full agent output. A run takes a few minutes. You can also run it with `uv run python -m creative_looper.main`.

## The pipeline

Agents run sequentially. Each report is written as soon as its agent finishes.

**Keeping the two domains apart.** Steps 1-3 work across both domains. The Concept Distiller (3b) then rewrites the mapped concept as a self-contained brief in *target-domain language only*: a native name, every component translated, and the critique's breakdown points restated as real constraints inside the target domain. The pitch writer (4) reads only that brief and never sees the primary domain, the mapping table or the critique. A guardrail checks the draft brief for the primary domain's name and, through a short model review, for technical vocabulary that would sound out of place in the target domain, and sends it back for up to 3 rewrites. A little terminology can still slip through; at the end of each run the number of primary-domain name mentions in the pitch is printed and logged.

| # | Agent | Reads | Writes |
| --- | --- | --- | --- |
| 1 | Phenomenon Explorer | the primary domain | `01_phenomenon.md` |
| 2 | Analogical Mapper | report 1 | `02_mapping.md` |
| 3 | Analytical Critic | report 2 | `03_critique.md` |
| 3b | Concept Distiller | reports 2, 3 | `03b_target_brief.md` |
| 4 | Story Pitch Writer | the brief | `04_pitch.md` (pitch) |
| 5 | Story Pitch Reviser | pitch, benchmark, the brief | `05_pitch2.md` (pitch2) |

## Output

Each run writes to `output/[Primary]_[Target]_[YYYYMMDD_HHMMSS]/`, with domain names reduced to letters, digits and underscores:

```
output/Biology_Politics_20261025_143005/
  README.md            index linking the reports, with token usage
  run.log              timestamped log of the run
  creativity_benchmark.md / .json     benchmark: scores pitch
  creativity_benchmark2.md / .json    benchmark2: scores pitch2
  01_phenomenon.md
  02_mapping.md
  03_critique.md
  03b_target_brief.md
  04_pitch.md
  05_pitch2.md
```

The timestamp means repeated runs of the same domains never overwrite each other. The agents pick a phenomenon fresh each time, so results differ between runs. The `output/` folder is gitignored.

## Creativity benchmark

**The improvement loop.** The Story Pitch Reviser receives the first pitch, the full benchmark (scores, the tropes found, the works it resembles, the red flags, the harsh critique) and the brief. It is told to fix every finding and may depart from the brief and invent beyond it. Benchmark2 then scores pitch2 the same way. Semantic distance rates the phenomenon and mapping, which pitch2 doesn't change, so benchmark2 reuses benchmark's score. The run prints `pitch -> pitch2` with the change in index. A revision can score the same or lower; the reviser is only as good as the model behind it, so a weak model may keep the stock phrasing the critic flagged.

Every pitch now ends with a separate `**The ending:**` paragraph that gives away how the story ends, so the judge can score twist execution on the actual ending.

Every run is scored by an LLM judge twice: benchmark scores the pitch, and benchmark2 scores pitch2 after the reviser has rewritten it. You can also re-score an existing run folder later without generating anything:

```sh
uv run creative-looper --score-run output/Geology_Jazz_20261026_130713
```

Four criteria, each 1-10. The judge is deliberately hostile: it lists the work's weaknesses before it scores, typical AI output is anchored at 3-4, and 8 or more is almost never given.

| Criterion | Judged on | Question |
| --- | --- | --- |
| Semantic Distance | the phenomenon and mapping, once per run | How bold and unexpected is the jump between the two domains, and does the mapping exploit it in a non-obvious way? |
| Metaphorical Density | the story pitch | How deeply are the concept's mechanics built into the piece, rather than name-dropped? |
| Freedom from Cliché | the story pitch | Did it avoid stock AI phrasing, corporate buzzwords and predictable story shapes? |
| Uniqueness | the story pitch | Is it interchangeable with other pitches? A separate adversarial judge names the real works it resembles and caps abstract pitches at 4; rule-based red flags (below) each take a point off. |

The **Creativity Index** (out of 40) is the sum of the four scores.

**Red flags** (`src/creative_looper/redflags.py`) are checks no model can argue with, up to 3 points off Uniqueness: stock pitch phrasing, generic AI-favorite names (Elias, Thorne, Voss...), famous comparable titles that tell an agent nothing, a pitch with almost no named people or places, and a pitch that copies four-word runs from its brief. Edit the lists in that file as you spot new tells.

The uniqueness judge also records extra data that does not enter the index: a **trope checklist** (the Hollywood and book clichés it found), **core premise novelty** and **twist execution** sub-scores (1-10), a **harsh critique**, and `truly_unique`, which is computed in code and is true only when the final uniqueness score is 8.5 or more. All of it is in `creativity_benchmark.md` and `.json`. Results go to `creativity_benchmark.md` (the scores, the judge's notes, the clichés it found), `creativity_benchmark.json` (for comparing runs) and a summary line in the run's `README.md`. Scoring a run takes about a minute and roughly 27k tokens. Judge calls are retried (3 attempts with a short wait) on network errors; if a single criterion still cannot be scored it shows as n/a and the rest carry on, and if the judge stays unreachable scoring stops with a message. Reports are never affected, and you can re-score at any time with `--score-run`.

How far to trust it: the judge runs at temperature 0, scores against written anchors, and must quote clichés that really appear in the text (invented quotes are dropped). It is still an LLM judge: it is noisy by a point or so, it tends to favor its own style (a model scoring its own pitch is the biggest inflater, so set `JUDGE_MODEL` to a stronger, different model), and scores are only comparable between runs scored by the same judge model. After the harsher rubric, a generic political-thriller pitch that scored 26/30 under the old one scored 12/40. With `--provider local` the judge is always the local model.

## Watching a run

- Each step prints its duration when it finishes, for example `[4/5] Distilling target-domain brief complete (7s)`.
- If a step runs longer than 15 seconds, a `... still working on 'Writing story pitch' (30s so far)` line is printed every 15 seconds, so you can tell a slow step from a stuck one.
- Every run writes `run.log` in its folder with timestamped step starts and finishes, token counts, each HTTP request to Gemini, and library warnings such as retries, timeouts and rate limits. Start there when something looks wrong.
- If a step still fails after its retries, the app names the step that failed and exits; reports finished before it are kept.

## Development

```sh
uv run pytest            # tests
uvx ruff check src tests # lint (unused imports, import order)
```

### How the code is organised

Each module has one job, and dependencies point downward: `main` calls `pipeline`, which calls `crew` and `benchmark`, which build on the small modules at the bottom.

```
src/creative_looper/
  main.py            CLI: arguments, prompts, readable error messages
  runner.py          one run (folder, log, CSV row) and the --loop over random domains
  domains.py         reading the domain list files and drawing a random pair
  runlog.py          the runs.csv log: one row per run
  errors.py          one-line messages for known failures
  pipeline.py        the stages of one run: crew -> benchmark -> pitch2 -> benchmark2 -> README
  crew.py            builds and runs the two CrewAI crews (analysis + pitch, then the reviser)
  agents.py          who each agent is (role, goal, backstory)
  tasks.py           what each agent is asked to do and the format it returns
  brief_guardrail.py quality gate that sends a leaky target-domain brief back for a rewrite
  benchmark/         the hostile judge
    prompts.py         the judge's instructions (the main lever for harshness)
    judge.py           calling the judge, retrying, parsing its JSON
    results.py         data model (Criterion, BenchmarkResult) and JSON -> model parsing
    scoring.py         builds each prompt and combines the answers into a result
    render.py          Markdown/JSON reports, README summary, feedback for the reviser
  redflags.py        rule-based pitch checks and the list of defects points are deducted for
  leakage.py         counts primary-domain words in text that should be target-domain only
  report.py          report file names, Markdown cleanup, headers, the run's README index
  observability.py   run.log, progress lines, heartbeat, per-step token usage
  config.py          model provider and LLM construction from the environment
  paths.py           run folder naming and the output location
tests/               one test module per source module, plus helpers.py (fakes and builders)
```

A run's files go to `./output/` in the directory you run the command from, or to `$CREATIVE_LOOPER_OUTPUT` if you set it.

**Where to change things**

| To change... | Edit |
| --- | --- |
| how harsh a score is | `benchmark/prompts.py`, or the lists in `redflags.py` |
| what a pitch must contain | `PITCH_FORMAT` in `tasks.py` |
| an agent's personality | `agents.py` |
| which files a run writes | the constants at the top of `report.py` |
| the order of stages | `pipeline.py` |
| the CSV's columns | `runlog.py` |
| what the loop does on failure | `runner.py` |
