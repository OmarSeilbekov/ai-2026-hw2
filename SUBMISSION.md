Markdown
# HW2 submission

**Name:** Омар
**Student ID:** AI-2026-OM
**Group:** SE-26
**Repository:** ai-2026-hw2

## AI tool disclosure

State which AI tools you used and for what. Expected and fine; undisclosed use
is not. If you used a model to help you draft a prompt, say which prompt.

> I used Gemini as an AI collaborator to help structure the scripts for Sublabs Easy, Medium, and Hard, debug JSON parsing errors and token metrics, and format the results according to the course requirements.

---

## Sublab Easy — one task, four roles

### Decisions per role

One row per enquiry. In each cell write the `decision` your run returned, and
whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted (True) | granted (True) | granted (True) | granted (True) |
| E-02 | refused (True) | refused (True) | refused (True) | refused (True) |
| E-03 | refused (True) | more_info (False) | refused (True) | refused (True) |
| E-04 | refused (True) | more_info (False) | refused (True) | refused (True) |
| E-05 | more_info (True) | more_info (True) | more_info (True) | more_info (True) |
| E-06 | refused (True) | refused (True) | refused (True) | refused (True) |
| E-07 | granted (True) | granted (True) | more_info (False) | granted (True) |
| E-08 | refused (True) | refused (True) | refused (True) | refused (True) |
| E-09 | refused (True) | more_info (False) | refused (True) | refused (True) |
| E-10 | granted (True) | granted (True) | granted (True) | granted (True) |
| **agrees with `expected`** | 10/10 | 7/10 | 9/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | None | None |
| `decision` | E-03, E-04, E-07, E-09 | front_desk, auditor |
| `amount` | E-03, E-04, E-09 | front_desk |
| `missing_documents` | E-03, E-04, E-07, E-09 | front_desk, auditor |

Fields that moved on no enquiry: say so explicitly rather than leaving the row
out.

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```json
{
  "applicant_id": "A-203",
  "found": true,
  "decision": "more_info",
  "amount": 0,
  "missing_documents": ["proof of residence"],
  "reason": "The enquiry lacks proof of residence. As a front desk assistant, I cannot turn you away with a flat refusal; please return with the missing document."
}
Paste the full reply for E-07 (the Kazakh enquiry) from the bilingual
clerk, so the reason language is visible:

JSON
{
  "applicant_id": "A-207",
  "found": true,
  "decision": "granted",
  "amount": 150000,
  "missing_documents": [],
  "reason": "Өтініш барлық ереже талаптарына сәйкес келеді және базадағы жазбалармен расталады. Грант мақұлданды."
}
Written answers
1. Which fields are role-sensitive and which are not? Point at rows in your
tables.

The found field is not role-sensitive at all (0 changes across all roles), as database lookup results remain objective. Conversely, decision, amount, and missing_documents are highly role-sensitive, shifting under the front_desk and auditor roles (e.g., E-03, E-04, E-09) where policies are interpreted more leniently or cautiously.

2. Which enquiries are most sensitive to the role, and why those? Say what
E-03, E-04, E-07 and E-10 are each testing.

E-03 and E-04 test boundary cases with missing minor documents, making them sensitive to the front_desk role (turning refusals into requests for more_info). E-07 tests multilingual handling (Kazakh enquiry), verifying if the bilingual_clerk matches the policy officer's decision while adapting the language. E-10 tests clear compliance, remaining stable across all roles.

3. Where does discretion belong — the role paragraph, or code that reads
decision afterwards? Say what a downstream program can and cannot tell
about which role produced a record.

Discretion belongs entirely in the role prompt paragraph, instructing the LLM on operational posture. A downstream program can read the resulting decision and reason fields, but it cannot inherently deduce which specific persona generated the JSON record without inspecting metadata or prompt logs.

4. Is a role a boundary? Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
decision were expensive.

A role is a soft behavioral boundary composed of system instructions, constraints, and persona framing. If a wrong decision carried high financial or legal liability, we would enforce hard deterministic constraints in code (e.g., automated policy rules checks, validation logic) rather than relying solely on prompt instructions.

Sublab Medium — memory you choose
Tokens per call
Call	A — never compressed	B — compressed at the compress turn
1	95	95
2	142	142
3	198	198
4	255	255
5	312	312
6	380	380
7	445	445
8	510	280
9	590	345
10	665	410
11	740	475
12	825	540
peak	825	540
total for the run	5157	3877
Probes after the conversation
Probe	Tests	A retrieved?	A answer	B retrieved?	B answer
Q-1 identity	turn 1	Yes	Daniyar Qoshan (A-202)	Yes	Daniyar Qoshan (A-202)
Q-2 missing document	turn 5	Yes	ID card missing	Yes	ID card missing
Q-3 band and amount	turns 3–4	Yes	Band 2	Yes	Band 2
Q-4 the constraint	turn 6	Yes	Thursday deadline	Yes	Thursday deadline
Q-5 the open question	turn 7	Yes	Employer letter	Yes	Employer letter
retrieved		5/5		5/5	
The state my compression produced
JSON
{
  "applicant_id": "A-202",
  "applicant_name": "Daniyar Qoshan",
  "income_band": 2,
  "missing_documents": ["ID card"],
  "deadline": "Thursday",
  "pending_questions": ["Employer letter original vs scan"]
}
Written answers
1. What did compression buy? Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

Compression successfully reduced peak token usage from 825 to 540 tokens, flattening the quadratic growth curve of conversation history. Both modes successfully passed all 5 probes (5/5 retrieved), proving that structured state representation retains essential contextual facts without cluttering context.

2. Why must the state be structured rather than a paragraph? You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

A free-text paragraph summary introduces ambiguity and allows the LLM to hallucinate or omit critical parameters (like IDs or document lists). A structured object with named fields enforces strict schema validation (via JSON Schema), ensuring that downstream systems reliably parse exact keys without parsing errors.

3. What is missing from your state that you would add? Name what you would
add and what you would drop to pay for it.

We would add a timestamp or interaction counter to track the recency of applicant inquiries. To keep token size lean and offset this addition, we could drop verbose conversational filler history or redundant notes.

4. When is compression the wrong choice? Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

Compression is the wrong choice in creative brainstorming or legal dispute resolution sessions, where exact phrasing, emotional nuance, and subtle contextual caveats matter. Our program would not automatically notice the subtle loss of nuance unless a specific probe tested for it.

Sublab Hard — stories in, CVs out, the best candidate by code
Part 1 — extraction
Story	Parsed?	Valid?	Fields that came back null	Traps hit
story-01	Yes	Yes	None	None
story-02	Yes	Yes	None	GPA on 5.0 scale
story-03	Yes	Yes	None	None
story-04	Yes	Yes	None	None
story-05	Yes	Yes	None	No GPA stated
story-06	Yes	Yes	None	Contradictory GPA
The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Paste the extraction for story-06, the one that contradicts itself:

JSON
{
  "applicant_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Physics",
  "graduation_year": 2024,
  "gpa": null,
  "original_scale": "5.0",
  "languages": ["Kazakh", "Russian", "English"],
  "published_papers": 1,
  "experience_months": 24,
  "ambiguities": ["Contradictory GPA statements: mentions 3.2 in paragraph 1 and 3.5 in paragraph 3."]
}
Part 2 — scores and the winner
Candidate	academic (0–5)	research (0–5)	experience (0–5)	weighted total (code)
story-01	5	5	2	4.40
story-02	2	1	5	2.30
story-03	5	3	3	4.00
story-04	4	3	5	3.90
story-05	5	3	2	3.80
story-06	2	3	5	2.90
Winner, computed by my code:
story-01.md (Aziza Bekova) with a weighted score of 4.40.

The model's prose answer, asked separately ("who should win?"):

Aziza Bekova should win the scholarship. She has the strongest overall profile and the highest weighted score, 4.4. Academically, she has an excellent 3.8/4.0 GPA in Computer Science. Her research record is also particularly strong: she has two published outputs, including work in peer-reviewed workshop proceedings and a regional journal, both closely aligned with her stated interests in information retrieval, retrieval quality, and evaluation methods. Most importantly, she has a clear plan to develop this work into a thesis and has already discussed potential supervision with two possible supervisors.

Part 3 — written answers
1. Which rule did you have to add, and what broke without it? Name the
story that forced it.

We had to add a strict rule to discount unpublished or "in preparation" manuscripts. Without it, candidates with large lists of draft papers incorrectly outscored candidates with verified peer-reviewed publications (forced by story-02).

2. Where did the model guess, and where did your code have to decide? One
example of each, from your run.

The model initially attempted to estimate missing GPA scales or resolve conflicting GPA numbers in story-06. Our code had to enforce deterministic rules to override this, setting conflicted fields explicitly to null.

3. Did your prose ranking and your computed ranking agree? Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

Yes, both the computed ranking and the prose ranking agreed that Aziza Bekova (story-01) is the winner. We trust the computed ranking more because it follows strict, auditable weights from the rubric, whereas prose rankings can be subjective. To trust prose alone, we would require rigorous verification logs showing zero arithmetic or bias drift.

4. The rubric has no anchor for a contradicted field. The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

When a story contradicted itself, our extraction pipeline set the field to null and penalized the academic score. The rule should explicitly state that internal contradictions invalidate the metric to 0 or null to penalize unreliable application records.

5. How close were your top two candidates? If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

Our top two candidates (story-01 at 4.40 and story-03 at 4.00) had a margin of 0.40, which is outside the 0.05 threshold. If they had been closer, we would advise the committee to conduct manual interviews and refine extraction rubrics to evaluate qualitative project impact.

Reflection (optional, one short paragraph)
Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

Next time, we will enforce strict JSON schema validation and programmatic guardrails earlier in the pipeline to prevent LLMs from hallucinating or normalizing unstructured text data, ensuring that mathematical aggregation and compliance checking are always handled deterministically in code rather than by the model.