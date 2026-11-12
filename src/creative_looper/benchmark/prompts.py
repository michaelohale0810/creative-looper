"""The judge's instructions.

Every prompt starts from INTRO, which makes the judge hostile and sets one 1-10
calibration scale. Each asks for a JSON reply, parsed in `results.py`. The wording is
the benchmark's main lever for harshness, so changes here change every score.
"""

INTRO = """You are a hostile, expert evaluator in computational creativity and divergent
thinking. Your job is to find what is wrong with the work, not to encourage it. Assume
the piece was written by a language model, and that language models produce fluent,
competent, generic text. Fluent is not creative.

Calibration for every 1-10 score:
  1-2  generic filler that any model would write for this prompt
  3-4  typical language-model output: competent, familiar and forgettable (this is where
       most work belongs)
  5    what a capable human professional would produce on an ordinary day
  6-7  clearly above average: a specific, distinctive choice that most writers would not make
  8    rare: several such choices that reinforce each other
  9-10 you would be surprised to see this score given; almost never

Method: first list the piece's concrete weaknesses, quoting the words; only then choose
the score, and make the score agree with the weaknesses you listed. Do not reward
ambition, length, formal vocabulary or an academic tone. Abstract restatement of an idea
("forces", "dynamics", "competing interests", "institutional reform") is not originality.
If you are unsure between two scores, give the lower one. Only quote words and phrases
that actually appear in the piece; examples given in these instructions are not evidence.
Section headings and field labels come from a fixed template and are never to be judged
or cited."""

SEMANTIC_DISTANCE_PROMPT = INTRO + """

Primary Domain: {primary}
Target Domain: {target}

Score SEMANTIC DISTANCE (1-10): how bold and unexpected is the conceptual jump from the
Primary Domain to the Target Domain in the mapping below? Consider both how far apart the
domains are and whether the chosen phenomenon and mapping exploit that distance in a
non-obvious way. A distant pair mapped through an obvious, well-worn analogy scores low.
  1-3  cliche or obvious analogy, the kind everyone reaches for first
  4-6  reasonable and clear, but the connection is predictable; the mapping mostly renames
       parts (a "force" becomes an "agency") without showing anything new
  7-8  surprising connection whose structure holds in specific, checkable places
  9-10 almost never given: mind-bending and novel, and every row of the mapping survives scrutiny
Renaming biological parts as political offices is a labeling exercise, not distance.

=== PHENOMENON ===
{phenomenon}

=== MAPPING ===
{mapping}

Reply with only a JSON object, no other text. List the mapping's weaknesses first:
{{"semantic_distance": {{"weaknesses": ["<specific weakness>", "..."], "score": <integer 1-10>, "evidence": "<one or two sentences citing the weaknesses>"}}}}"""

REPORT_PROMPT = INTRO + """

You are scoring one creative piece ("{title}") written from a concept in the domain of
{target}. The concept's mechanics are described in the brief.

Score two criteria (1-10 each):

METAPHORICAL DENSITY: how deeply and inventively are the concept's core mechanics built
into the piece, rather than name-dropped?
  1-3  mechanics barely present, or only decorative theming
  4-6  present and recognizable, but mostly surface dressing; the pitch restates the
       brief's concepts in general terms ("sanctions", "reform", "sub-networks") while the
       actual events are a stock plot
  7-8  specific events, objects or rules in the story embody the mechanics, in ways the
       brief did not spell out
  9-10 almost never given: the story could not exist without the mechanics, and it extends them
A pitch that is a paragraph-length summary of the brief with a protagonist attached scores 4 or less.

FREEDOM FROM CLICHE: did the piece avoid standard AI tropes, corporate buzzwords and
predictable structures? Penalize stock phrasing ("tapestry", "delve", "symphony of",
"a testament to"), corporate buzzwords ("synergy", "leverage", "seamless", "empower",
"AI-powered", "dashboard"), predictable shapes (neon-soaked dystopia, chosen one, "in a
world where", the insider whistleblower, the AI-was-behind-it twist, a rogue
investigator), and generic invented names (Dr. Elena Vance, Kaelen Voss and the like).
  1-3  built mostly from stock tropes and phrasing
  4-6  some fresh moments inside a familiar template; includes a hook like "what happens
       when...", a generic ministry or agency, a stock genre label with a stock protagonist
  7-8  distinctive voice and structure, with only incidental cliches
  9-10 almost never given: original throughout
A formal, academic or "specialized" tone is not freshness. Famous comparable titles and
generic character names count against the piece.

=== BRIEF ===
{brief}

=== PIECE ===
{piece}

Reply with only a JSON object, no other text. List weaknesses before scoring:
{{"metaphorical_density": {{"weaknesses": ["<specific weakness>"], "score": <integer 1-10>, "evidence": "<one or two sentences>"}},
 "freedom_from_cliche": {{"weaknesses": ["<specific weakness>"], "score": <integer 1-10>, "evidence": "<one or two sentences>",
 "cliches_found": ["<short quoted examples, or an empty list>"]}}}}"""

UNIQUENESS_PROMPT = INTRO + """

You are now a literary agent who rejects 99% of the pitches in the slush pile and has read
thousands of AI-written ones. Below is a story pitch in the genre of {target}. Decide how
UNIQUE it is: could this exact book only come from this idea, or is it interchangeable
with dozens of others?

Do these in order:
1. Name up to three REAL, well-known books, films or shows this pitch resembles, and what
   it shares with each. Only name works you are certain exist. Use an empty list only if
   you truly find no resemblance.
2. List three to six specific weaknesses, quoting the pitch.
3. Judge each comparable title the pitch itself names: does it exist, and does it fit?
4. List every common Hollywood or book cliché you find in the pitch (trope checklist),
   naming each trope. Use an empty list only if you find none.
5. Score CORE PREMISE NOVELTY (1-10): has the core concept been done before? Use the same
   scale as below, and be harsh.
6. Score TWIST EXECUTION (1-10): the pitch ends with a separate paragraph that reveals how
   the story ends (labelled "The ending"). How unpredictable are the turns and that
   ending? Could a reader guess it from the setup and the stakes? Does the ending pay off
   what the pitch set up, or is it a stock reveal (it was a dream, the AI did it, the
   mentor was the villain)? A predictable ending scores 4 or less, and a pitch with no
   ending paragraph scores 1.
7. Write a harsh critique: a brutally honest paragraph on why the pitch is derivative or
   original.
8. Score UNIQUENESS (1-10), your overall verdict, penalizing tropes heavily:
  1-2  interchangeable with countless pitches in its genre
  3-4  a familiar premise with a gimmick; generic protagonist and setting; told in
       abstractions (the usual result for AI pitches)
  5    competent, but you can name the book it is derived from
  6-7  one element (premise, protagonist, setting or voice) is truly distinctive and made
       concrete with particulars
  8    premise, protagonist and voice are all fresh and specific, and you struggle to name a
       precedent
  9-10 almost never given
Hard caps: a pitch with no particular people, places, objects or events (only roles,
institutions and forces) cannot exceed 4. A pitch whose premise matches a well-known work
cannot exceed 5. A pitch whose title, protagonist or hook could belong to any other book of
its genre cannot exceed 6.

Rule-based checks already found these problems (treat them as established facts):
{flags}

=== BRIEF THE PITCH WAS WRITTEN FROM ===
{brief}

=== PITCH ===
{piece}

Reply with only a JSON object, no other text:
{{"uniqueness": {{"closest_existing_works": ["<title: what it shares>"], "weaknesses": ["<specific weakness>"],
 "comparable_titles_verdict": "<one sentence>", "trope_checklist": ["<trope found>"],
 "core_premise_novelty": <integer 1-10>, "twist_execution_score": <integer 1-10>,
 "harsh_critique": "<one paragraph>", "score": <integer 1-10>, "evidence": "<one or two sentences>"}}}}"""
