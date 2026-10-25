# What is measured

**English** | [Deutsch](MEASUREMENT.de.md)

**Context:** how the published classification figures were obtained and what they are worth | **Input:** the 217 official examples in `official_examples.json`, the walkthrough, the run logs `answers-*.json` and `remeasurement.json` | **Output:** the hit rate, the method, every mismatch with its cause, and what is not measured

As of 4 October 2026. The figures are kept in `figures.json`; `tests/test_measurement.py` recounts
them from the run logs on every test run.

## The figure

**Context:** the headline result | **Input:** all 217 examples, each answered once | **Output:** hit rate and average length of a walkthrough

**207 of 217 official examples** from the European Commission are classified correctly, in
**5.3 steps** per case on average.

The method:

1. The 217 examples come from the draft Commission guidelines of 19 May 2026 on classifying
   high-risk artificial intelligence (AI) systems. Each describes an AI system and states the
   Commission's verdict.
2. A reader who knows only the description — not the verdict — answers the questions of the
   walkthrough with it. `scripts/answer_questions.py` hands out the next open questions and, with
   `--result`, the finding.
3. The finding is compared with the Commission's verdict.

## What the figure is worth

**Context:** why the figure means something, and in which direction it errs | **Input:** origin of the expected verdicts and length of the examples | **Output:** two limits of the measurement

The expected verdicts come from the Commission, not from the author of the rules. That is the
difference from the previous version, where the same person wrote both the rules and the test
cases; there, a high hit rate only meant that the helper agreed with that one reading.

The example descriptions are short. Staff classifying their own system know more about it than
two sentences say, so the measured figure tends to be too low rather than too high.

## The ten mismatches

**Context:** every example the walkthrough classifies differently from the Commission | **Input:** the run logs, with the remeasurement overriding the first run | **Output:** the cause of each mismatch

Seven of them do not measure the walkthrough. Examples 2, 6, 13, 47, 48, 72 and 114 come from the
section of the guidelines on the derogation in Article 6(3) of the AI Act (Regulation (EU)
2024/1689). Their descriptions
establish no area of Annex III. The walkthrough asks about the derogation only once an area
applies — as the law requires, because Article 6(3) only exempts what first falls under Annex III.
Without an area the question never comes up. For the user the outcome is the same: no high-risk
obligations.

Leaving these seven out gives **207 of 210**.

The other three:

| Example | Cause |
|---|---|
| 108 | The description does not say that a law enforcement authority deploys the system. |
| 141 | The description names no area; the example is a counter-example to the derogation. |
| 187 | The description names no safety function for a translation tool in road traffic. |

All three fail because the example text leaves out the decisive feature — the deploying
authority, the area, the safety function. Staff classifying their own system know it.

A fourth mismatch, example 92, was closed on 4 October 2026. The preliminary question on assessing
people lacked a sentence from paragraph (73) of the guidelines: a business remains a business even
if it belongs to a single person and is not a legal person. Whoever evaluates only the balance
sheets, turnover and payment behaviour of a business assesses no person. The sentence is now part
of the question; before, it was only in the explanation, where the user could not answer it.

## What else is measured

**Context:** checks that run beside the hit rate | **Input:** the commands and tests named in the table | **Output:** one result per check

| What | Result | Where |
|---|---|---|
| Web page and Python program compute the same finding | 400 of 400 runs | `scripts/check_parity.py --runs 400` |
| Every legal basis in the rule set points to real official text | 302 of 302 | `tests/test_classification.py` |
| Legal corpus split without loss | 2,811 units per language, no warning | `data/processed/corpus_report.json`, `corpus_report.en.json` |
| Free-text classification of 100 company questions | at least 95 of 100, German and English | `tests/test_purposes.py`, `tests/test_accuracy_en.py` (slow tests, need the local models) |
| The built package starts and serves the question flow | on every package build | `packaging/launch_check.py` |

## What is not measured

**Context:** the open gaps | **Input:** the parts of the answer without an outside benchmark | **Output:** two statements of what nobody has checked

The derived obligations. They come from `data/rules/ai_act_obligations.yaml` and are checked
against the text of the Regulation, but not measured against an outside benchmark — no official
collection of examples exists for them.

No lawyer has reviewed the walkthrough.
