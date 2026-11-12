"""Task definitions: what each agent is asked to do and the shape of what it returns.

Each factory returns a CrewAI Task wired to write its report into the run folder.
"""

from pathlib import Path

from crewai import LLM, Agent, Task
from crewai.tasks.task_output import TaskOutput

from creative_looper.brief_guardrail import MAX_BRIEF_REWRITES, make_guardrail
from creative_looper.leakage import count_domain_mentions
from creative_looper.observability import logger
from creative_looper.redflags import defects_list
from creative_looper.report import (
    BRIEF_REPORT,
    CRITIQUE_REPORT,
    MAPPING_REPORT,
    PHENOMENON_REPORT,
    PITCH2_REPORT,
    PITCH_REPORT,
    clean_markdown,
)

FORMAT_RULES = (
    " Use the section and field names exactly as written, leaving out any "
    "parenthetical hints. Return plain Markdown and do not wrap the document in a "
    "code fence."
)

ANALYTIC_RULE = " Write in a neutral, analytical register with no humor or stylistic flourish."
CREATIVE_RULE = (
    " Choose the voice and tone that best fits each concept; do not force a single style."
)


def save_to(path: Path):
    """Callback that writes a task's output to `path`.

    CrewAI's `output_file` strips the leading slash from absolute paths, which
    would write relative to the current directory, so we save the file ourselves.
    """

    def _save(output: TaskOutput) -> None:
        text = clean_markdown(output.raw)
        path.write_text(text, encoding="utf-8")

    return _save


def explore_phenomenon(agent: Agent, run_dir: Path) -> Task:
    return Task(
        description=(
            "Research the domain of {primary_domain}. Select one singular, specific, "
            "and unexpected phenomenon. Avoid famous textbook examples. Write a detailed "
            "summary of its rules, causes, and effects, naming each distinct component "
            "(actors, forces, conditions, outcomes) so it can later be mapped onto "
            "another domain."
        ),
        expected_output=(
            "A Markdown report with a title naming the phenomenon and these sections: "
            "Overview, Rules, Causes, Effects, Key Components (a list of every actor, "
            "force, condition and outcome with a one-line description each)."
            + FORMAT_RULES
            + ANALYTIC_RULE
        ),
        agent=agent,
        callback=save_to(run_dir / PHENOMENON_REPORT),
    )


def map_to_target(agent: Agent, run_dir: Path, phenomenon: Task) -> Task:
    return Task(
        description=(
            "Using the phenomenon report, map its specific mechanics onto the domain of "
            "{target_domain}. Produce a 1:1 structural analogy: every component, rule, "
            "cause, and effect of the original phenomenon needs a clearly defined "
            "{target_domain} equivalent. Do not skip components, and keep the mapping "
            "concrete (real institutions, actors, instruments, or processes)."
        ),
        expected_output=(
            "A Markdown report with a title and these sections: Summary of the "
            "Phenomenon, Mapping Table (a Markdown table with columns "
            "'Original Component', 'Role in Phenomenon', '{target_domain} Equivalent', "
            "'Why It Fits', covering every Key Component), How the Mapped System "
            "Behaves (the full mechanism told in {target_domain} terms)."
            + FORMAT_RULES
            + ANALYTIC_RULE
        ),
        agent=agent,
        context=[phenomenon],
        callback=save_to(run_dir / MAPPING_REPORT),
    )


def critique_mapping(agent: Agent, run_dir: Path, mapping: Task) -> Task:
    return Task(
        description=(
            "Critique the analogy between {primary_domain} and {target_domain} as a "
            "hostile reviewer would. Go through the mapping row by row and say whether "
            "each row is a true structural match or only a relabeling. Identify every "
            "place the mapping breaks down, is logically inconsistent or leaves out "
            "something important from the phenomenon. Name only the surprising practical "
            "insights that survive scrutiny, and say plainly if there are none. Evaluate "
            "whether the mapped concept could exist or be implemented in the real world. "
            "Refer to specific rows of the mapping by name."
        ),
        expected_output=(
            "A Markdown report with a title and these sections: Where the Mapping Holds, "
            "Where It Breaks Down, Surprising Insights, Real-World Feasibility "
            "(obstacles, requirements, and a verdict), Overall Assessment (a score out "
            "of 10 with a one-paragraph justification). Where It Breaks Down must list at "
            "least four distinct problems. Score strictly: 1-3 mostly relabeling or "
            "contradictory, 4-5 plausible but shallow or partly forced, 6 solid with "
            "real flaws, 7 strong, 8 or more only if you cannot find a serious flaw "
            "(rare). Typical mappings deserve 4-5, and the score must agree with the "
            "problems you listed."
            + FORMAT_RULES
            + ANALYTIC_RULE
        ),
        agent=agent,
        context=[mapping],
        callback=save_to(run_dir / CRITIQUE_REPORT),
    )


def distill_brief(
    agent: Agent,
    run_dir: Path,
    mapping: Task,
    critique: Task,
    primary: str,
    target: str,
    llm: LLM,
) -> Task:
    """Rewrite the mapped concept in target-domain terms only.

    The pitch tasks read this brief and nothing upstream of it, which keeps the two
    domains decoupled. A guardrail sends drafts that still lean on `primary` back for
    a rewrite; `save_and_check` then logs any mention that survived.
    """
    path = run_dir / BRIEF_REPORT
    save = save_to(path)

    def save_and_check(output: TaskOutput) -> None:
        save(output)
        leaked = count_domain_mentions(run_dir, primary, [path.name]).get(path.name, 0)
        if leaked:
            logger.warning("brief still mentions %r %d time(s)", primary, leaked)

    return Task(
        description=(
            "Using the mapping and the critique, write a self-contained brief about the "
            "concept as if it had always belonged to {target_domain}. The writers who "
            "read your brief will never see the original {primary_domain} phenomenon, "
            "the mapping table or the critique, so everything they need must be in your "
            "brief, in {target_domain} language. Give the concept a name native to "
            "{target_domain}. Replace every original component with its {target_domain} "
            "equivalent. Never use {primary_domain} terminology, organisms, materials, physical or "
            "scientific laws or jargon, and never describe the concept as an analogy, "
            "mapping or metaphor for anything. If a word would sound out of place in an "
            "ordinary conversation among {target_domain} practitioners, replace it. "
            "The critique's breakdown points are mismatches between two domains; do not "
            "repeat them as such. Instead restate each one as a real constraint inside "
            "{target_domain} itself: what practical, human, organizational or "
            "technical factor in {target_domain} limits the concept, makes it fail, or "
            "makes it surprising. Do the same for the feasibility verdict. Before you "
            "finish, reread the brief and rewrite any sentence that still leans on "
            "{primary_domain}."
        ),
        expected_output=(
            "A Markdown report that opens with a '# <concept name>' heading, then these "
            "sections: The Concept (a short plain description), How It Works (its "
            "components, forces, sequence of events and outcomes), Where It Strains "
            "(limits, tensions and failure modes), Surprising Insights, Real-World "
            "Feasibility (obstacles and a verdict), Vocabulary (8-12 {target_domain} "
            "terms or invented names with a one-line meaning each, for writers to reuse)."
            + FORMAT_RULES
            + ANALYTIC_RULE
        ),
        agent=agent,
        context=[mapping, critique],
        guardrail=make_guardrail(primary, target, llm),
        guardrail_max_retries=MAX_BRIEF_REWRITES,
        callback=save_and_check,
    )


PITCH_FORMAT = (
    "A Markdown report that opens with a '# <novel title>' heading, then an "
    "italic line giving genre, target readership and approximate word count, "
    "then exactly two or three paragraphs of pitch prose (no headings, bullets "
    "or bold fields between them) that do not reveal the ending, then one separate "
    "final paragraph that begins with the bold label '**The ending:**' and "
    "reveals exactly how the story ends, including any twist, in under 120 words, "
    "then a final italic line with two or three comparable titles in the form "
    "'For readers of ...'. The pitch paragraphs total under 300 words."
)


def write_pitch(agent: Agent, run_dir: Path, brief: Task) -> Task:
    return Task(
        description=(
            "Using the brief, write a story pitch for one original novel, as if you "
            "had only two or three paragraphs to win over a literary agent or sell "
            "the book to a publisher. The novel must use the {target_domain} concept "
            "in the brief as its central engine, so that it could not be told without "
            "it. Choose the genre that fits best. Open with a hook, introduce a "
            "protagonist who wants something specific, show the stakes escalating "
            "and the brief's strains and limits turning into conflict, and end the "
            "pitch paragraphs on the question or dilemma that makes a reader need the "
            "answer. Then, in a separate final paragraph, reveal how the story ends. "
            "Use the setting and vocabulary of the brief."
        ),
        expected_output=PITCH_FORMAT + FORMAT_RULES + CREATIVE_RULE,
        agent=agent,
        context=[brief],
        callback=save_to(run_dir / PITCH_REPORT),
    )


def revise_pitch(agent: Agent, run_dir: Path) -> Task:
    """Rewrite the first pitch using its benchmark. The pitch, the brief and the
    findings arrive as the {original_pitch}, {brief} and {feedback} inputs."""
    return Task(
        description=(
            "Below is a novel pitch written by an AI, followed by a hostile critic's "
            "scoring of it, and the brief it was written from. Write a better pitch for "
            "the novel that fixes the critic's findings.\n\n"
            "Work through the findings: remove or subvert every trope and cliché it "
            "lists, replace every generic name and stock phrase with something "
            "particular, turn abstractions into specific people, places, objects and "
            "events, avoid the existing works it says the pitch resembles, replace any "
            "predictable ending or twist with one a reader could not guess, and choose "
            "better comparable titles (real books, not too famous to be informative). "
            "Keep what the critic found strong. You may depart from the brief, invent "
            "beyond it, and change the protagonist, setting, genre or plot whenever that "
            "makes the pitch better; the brief is a starting point, not a limit. Do not "
            "mention the critic, the scoring or the earlier pitch.\n\n"
            "Before you answer, audit your draft the way the critic will. A hostile editor "
            "starts every pitch at 10 and subtracts these points for each defect found:\n"
            + defects_list()
            + "\nCount the points your draft would lose. If it would lose more than 2, "
            "rewrite it until it would not. Your own first draft is probably still "
            "generic: be suspicious of every name, phrase and plot beat that came easily.\n\n"
            "=== ORIGINAL PITCH ===\n{original_pitch}\n\n"
            "=== CRITIC'S SCORING OF IT ===\n{feedback}\n\n"
            "=== BRIEF ===\n{brief}"
        ),
        expected_output=PITCH_FORMAT + FORMAT_RULES + CREATIVE_RULE,
        agent=agent,
        callback=save_to(run_dir / PITCH2_REPORT),
    )
