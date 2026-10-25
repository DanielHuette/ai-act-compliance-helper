# Liability: what this tool is not

**English** | [Deutsch](liability.de.md)

**Context:** the limits of what the tool's output may be used for | **Input:** the license, the measurements and the known limits of the current state | **Output:** what the tool is not, what can be wrong and what it can do

This page makes no excuses. Whoever has read it knows what they are holding. It concerns the
classification of artificial intelligence (AI) systems under Regulation (EU) 2024/1689 laying down
harmonised rules on artificial intelligence (AI Act) and the information on the General Data
Protection Regulation (GDPR) and the German Federal Data Protection Act.

## No legal advice

**Context:** the legal status of the output | **Input:** the German Legal Services Act (Rechtsdienstleistungsgesetz) | **Output:** a clear boundary

This tool provides **no legal advice** within the meaning of the German Legal Services Act. It does
not examine a specific individual case in someone else's matter; it classifies the answers or the
description entered, using a rule set, and names the provisions of the law that apply.

Legal advice comes from people licensed to give it: a lawyer, and for certain questions the
competent supervisory authority. Whoever makes a decision with financial or legal consequences
(rebuild a product or not, put a system into service or not, file a notification or not) obtains
that advice.

## No substitute for an individual review

**Context:** what the tool cannot know | **Input:** the two routes to a classification | **Output:** a list of blind spots

The classification comes either from the user's answers to a question flow or from a description in
the user's own words, matched against a rule set of vocabularies and conditions. Neither can do what
a review of the individual case does:

* It does not know the contract with the provider.
* It does not know the instructions for use of the system.
* It does not know the actual data flows in the company.
* It does not know the agreements with the works council.
* It does not know the practice of the competent supervisory authority.
* It does not know case law: not a single court decision is included.

Yet these are exactly the points that decide whether an obligation applies and how to meet it.

## No warranty

**Context:** what the license says | **Input:** Apache License 2.0, sections 7 and 8 | **Output:** no warranty, no liability

The tool is published under the Apache License 2.0. Its sections 7 and 8 apply without restriction:
the software is provided "as is", without warranty of any kind, and no liability is accepted for
damages. That is not small print; it is the situation.

In particular, there is no warranty:

* that the classification is correct,
* that the list of obligations is complete,
* that the list of obligations contains no obligations that do not apply,
* that the article references are correct,
* that the deadlines are current,
* that the legal text shipped with the tool matches the official version,
* that the English texts say exactly what the German ones say.

## What can concretely be wrong

**Context:** the known weaknesses, measured where possible | **Input:** [architecture.md](architecture.md), section "Limits of the system", and the current data | **Output:** what to check yourself

This is not abstract. It is measured and listed in detail in [architecture.md](architecture.md),
section "Limits of the system". The essentials:

**The list of obligations is longer rather than shorter.** It contains all obligations of the
detected risk class and role, including ones that do not fit the individual project. Measured on
9 October 2026: a company that uses bought software to pre-sort job applications received 14
obligations, among them the fundamental rights impact assessment of Article 27, which binds only
bodies governed by public law, private bodies providing public services and deployers under Annex
III points 5(b) and (c). Check every item yourself.

**The classification can come out too low.** In the question flow it depends on the answers: a wrong
answer gives a wrong finding, and the tool cannot notice. On the free-text route (command line,
search page, JavaScript Object Notation (JSON) interface) traits are recognised from vocabularies and, when the models are
installed, from comparison with purpose sentences. Whoever describes the project in other words than
these anticipate may not be recognised. A description that matches no rule ends at "no particular
obligations apart from AI literacy under Article 4", and that classification carries the confidence
"likely", not "certain". Read the confidence levels and the open questions.

**10 of the 217 official examples are classified differently from the Commission.** Each deviation
is explained in [../data/evaluation/MEASUREMENT.md](../data/evaluation/MEASUREMENT.md).

**The guidelines are a draft.** The questions rest on the European Commission's draft guidelines of
19 May 2026 on classifying high-risk AI systems. The consultation ran until 23 June 2026; the final
version may differ. Guidelines do not bind courts in any case.

**The shipped legal text is not the authentic publication.** The AI Act and the General Data
Protection Regulation come from the Official Journal of the European Union, in German and English,
and the Federal Data Protection Act (Bundesdatenschutzgesetz, BDSG) from gesetze-im-internet.de.
The tool breaks these texts into units with its own parsers, and a parser can misplace or lose text.
The English BDSG is a translation by the Language Service of the Federal Ministry of the Interior;
only the German text is legally binding. Details: [data-sources.md](data-sources.md).

**The English questions and explanations are translations.** Questions, rules, use cases and
explanations were written in German and translated into English; no lawyer has reviewed either
language. If a translation is missing, the German text is shown. The paragraph number on every
question is the cross-check against the guidelines.

**The deadlines may have changed.** The caveat is in the rule set and in every answer: the deadlines
are as published in the Official Journal of 12 July 2024; at the date of the rule set, changes to
individual deadlines were under political discussion.

**The use cases are not checked.** The 44 use cases were written by the author and have not been
checked by any authority or law firm. They illustrate; they are not a legal source, and the tool
files them under "Guidelines", not as law.

**Recitals are not obligations.** A recital gives reasons for a regulation, it does not regulate. It
can appear as a passage. Reading it as an obligation is wrong.

**A worded answer can misrepresent an article.** The check catches an invented number, but not a
wrong summary of an existing provision. Whoever relies on an obligation reads the passage word for
word; it is shown with the answer.

**The data has a date.** The obligations, risk classes and data protection review path carry the date
31 May 2026, the question flow 4 October 2026; the legal texts were fetched on 3 October 2026
(German) and 9 October 2026 (English). Case law, guidelines, adequacy decisions and delegated acts
after these dates are not included. The further back these dates lie, the less reliable the
information.

## What the tool can do

**Context:** so the picture is not lopsided | **Input:** the features of the current version | **Output:** what it is good for

It can:

* give a first overview of the direction a project is heading,
* name the provisions of the law where one reads on oneself, with the exact point, not only the
  annex,
* name the questions to clarify before talking to a law firm,
* keep the provider view and the deployer view apart,
* show that the AI Act and data protection law apply side by side, not one instead of the other,
* do all this in German or English, and on the question-flow page without an account, without
  network and without the answers leaving the device.

As preparation it is useful. As a basis for decisions it is not.

## If you find an error

**Context:** how errors reach the project | **Input:** your observation | **Output:** a report through the dedicated channel

Report it. A wrong article reference affects everyone who uses the tool. There is a dedicated way to
report legal errors, with its own form; the details are in [CONTRIBUTING.md](../CONTRIBUTING.md), in
the section on legal errors.
