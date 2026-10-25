"""Question-flow walkthrough that classifies Annex I and Annex III high-risk systems.

Context: asks the questions a lawyer would ask instead of guessing answers from free text; every
question, exclusion and example cites the Commission's draft high-risk guidelines (19 May 2026).
| Input: data/rules/question_flow_layout.yaml, data/rules/question_flow/*.yaml, answers by question
id | Output: next question or question group, and a Finding with risk class and evidence.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from compliance_helper import paths
from compliance_helper.i18n import Language, pick

logger = logging.getLogger(__name__)

COVERED = "covered"
NOT_COVERED = "not_covered"
CONTINUE = "continue"
END = "end"

#: Met except for a condition the user cannot know, e.g. designation as critical entity
#: for Annex III point 2 (guidelines paras. 190-191); a "no" would be a false statement.
CONDITIONAL = "conditional"

#: Third answer besides yes/no: leaves a question undecided; it never affirms an element or a
#: condition and never fires an exclusion.
NOT_APPLICABLE = "not_applicable"

ANNEX_I_CITATION = "AI-Act/annex-I"


class RuleLayoutError(ValueError):
    """The question-flow layout refers to a question that does not exist or is ambiguous."""


def directory() -> Path:
    return paths.rules_dir()


def _data_text(value: Any, language: Language | None = None) -> str:
    """Return a rule-file text in the active language with its line breaks folded."""
    return " ".join(str(pick(value, language) or "").split())


def _picked_entries(entries: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple({key: pick(value) for key, value in entry.items()} for entry in entries)


@dataclass(frozen=True)
class Question:
    """A yes/no question a layperson can answer.

    Wording, heading and effect note keep the rule-file value, which may be bilingual, and are
    read in the language active at the time of access.
    """

    id: str
    wording: Any
    source_ref: str
    stage: str
    citation: str = ""
    heading: Any = ""
    on_yes: str = CONTINUE
    on_no: str = CONTINUE
    effect: Any = ""

    @property
    def text(self) -> str:
        return _data_text(self.wording)

    @property
    def german_text(self) -> str:
        """Authoritative wording that layout markers in the rule files refer to."""
        return _data_text(self.wording, Language.DE)

    @property
    def title(self) -> str:
        return str(pick(self.heading) or "")

    @property
    def effect_note(self) -> str:
        return _data_text(self.effect)


@dataclass(frozen=True)
class Provision:
    """A provision with its questions, exclusions and examples."""

    citation: str
    area: str
    heading: Any
    main_question: Question
    follow_up_questions: tuple[Question, ...]
    covered_entries: tuple[dict[str, Any], ...]
    not_covered_entries: tuple[dict[str, Any], ...]
    example_entries: tuple[dict[str, Any], ...]
    is_area_gate: bool = False
    branches: tuple[tuple[Question, ...], ...] = ()

    @property
    def title(self) -> str:
        return str(pick(self.heading) or "")

    @property
    def covered(self) -> tuple[dict[str, Any], ...]:
        return _picked_entries(self.covered_entries)

    @property
    def not_covered(self) -> tuple[dict[str, Any], ...]:
        return _picked_entries(self.not_covered_entries)

    @property
    def examples(self) -> tuple[dict[str, Any], ...]:
        return _picked_entries(self.example_entries)

    @property
    def chains(self) -> tuple[tuple[Question, ...], ...]:
        """Question chains each sufficient on its own: one per alternative, else all follow-ups."""
        return self.branches or (self.follow_up_questions,)


@dataclass(frozen=True)
class Finding:
    """Outcome of a walkthrough."""

    risk_class: str
    matched_provisions: tuple[Provision, ...]
    filter_applies: bool
    filter_reason: str
    evidence: tuple[str, ...]
    open_provisions: tuple[str, ...]
    closing_text: str = ""

    @property
    def citations(self) -> tuple[str, ...]:
        return tuple(p.citation for p in self.matched_provisions)


#: Questions about the user's own previous answers; the walkthrough computes these itself.
_SELF_REFERENTIAL_PREFIXES = ("haben sie alle",)


def _is_self_referential(question: dict[str, Any]) -> bool:
    text = _data_text(question.get("question"), Language.DE).lower()
    return any(text.startswith(m) for m in _SELF_REFERENTIAL_PREFIXES)


def _ordered_follow_ups(follow_up_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order follow-ups as elements first, exemptions last, dropping self-referential ones.

    A provision applies when an element is affirmed and no exemption applies, so exemptions must
    always be asked in full rather than skipped after the first decisive answer.
    """

    def rank(f: dict[str, Any]) -> int:
        return 1 if NOT_COVERED in (f.get("on_yes"), f.get("on_no")) else 0

    return sorted((f for f in follow_up_questions if not _is_self_referential(f)), key=rank)


def _references(*refs: str | None) -> tuple[str, ...]:
    """Paragraph references of a finding, without empty entries."""
    return tuple(ref for ref in refs if ref)


def _with_product(template: Any, product: str) -> str:
    return _data_text(template).replace("{product}", product)


def _any_of_state(question_ids: Iterable[str], answers: dict[str, Any]) -> str:
    """State of a group that holds when one of its questions is affirmed.

    COVERED on a yes, CONTINUE while a question is unanswered, CONDITIONAL when only "don't
    know" answers keep it from failing, NOT_COVERED when every answer is no.
    """
    given = [answers.get(k) for k in question_ids]
    if any(answer is True for answer in given):
        return COVERED
    if any(answer is None for answer in given):
        return CONTINUE
    if any(answer == NOT_APPLICABLE for answer in given):
        return CONDITIONAL
    return NOT_COVERED


def _answer_effect(question: Question, answer: Any) -> str:
    """Return the effect of an answer; both branches matter.

    A match can hang on a "no" (Annex III point 1(a)), so on_no is evaluated like on_yes.
    Unanswered and not-applicable answers have no effect.
    """
    if answer is True:
        return question.on_yes
    if answer is False:
        return question.on_no
    return CONTINUE


def _evaluate_chain(questions: tuple[Question, ...], answers: dict[str, Any]) -> str:
    """Evaluate a question chain; shared by the verdict and the question order.

    Never stops at the first decisive answer, otherwise questioning and evaluation diverge and a
    provision stays open forever. An affirmed exemption beats an affirmed element, as in the
    legal text.
    """
    excludes = False
    applies = False
    pending = False
    for f in questions:
        answer = answers.get(f.id)
        if answer is None:
            pending = True
            continue
        effect = _answer_effect(f, answer)
        if effect == NOT_COVERED:
            excludes = True
        elif effect == COVERED:
            applies = True
    if excludes:
        return NOT_COVERED
    if applies:
        return COVERED
    return CONTINUE if pending else NOT_COVERED


def _evaluate_chains(chains: tuple[tuple[Question, ...], ...], answers: dict[str, Any]) -> str:
    """A provision with alternatives applies when one alternative's chain applies."""
    findings = [_evaluate_chain(chain, answers) for chain in chains]
    if COVERED in findings:
        return COVERED
    return CONTINUE if CONTINUE in findings else NOT_COVERED


def _marked_question(citation: str, marker: str, questions: tuple[Question, ...]) -> Question:
    found = [q for q in questions if marker in q.german_text]
    if len(found) != 1:
        raise RuleLayoutError(
            f"Alternative of {citation}: {marker!r} matches {len(found)} questions, expected one"
        )
    return found[0]


def _with_branches(provision: Provision, branches: dict[str, dict[str, list[str]]]) -> Provision:
    """Split a provision's follow-ups into one chain per alternative plus the shared questions.

    A required question ends its own alternative with a "no", whatever its effect elsewhere.
    """

    def marked(markers: list[str] | None) -> list[str]:
        return [
            _marked_question(provision.citation, marker, provision.follow_up_questions).id
            for marker in markers or []
        ]

    alternatives = [
        (set(marked(branch.get("questions"))), set(marked(branch.get("required"))))
        for branch in branches.values()
    ]
    owned = [k for members, required in alternatives for k in (*members, *required)]
    if len(owned) != len(set(owned)):
        raise RuleLayoutError(f"Alternatives of {provision.citation} share a question")
    chains = tuple(
        tuple(
            dataclasses.replace(q, on_no=NOT_COVERED) if q.id in required else q
            for q in provision.follow_up_questions
            if q.id not in owned or q.id in members | required
        )
        for members, required in alternatives
    )
    return dataclasses.replace(provision, branches=chains)


def _apply_alternatives(
    provisions: list[Provision], alternatives: list[dict[str, Any]]
) -> list[Provision]:
    by_citation = {entry["citation"]: entry.get("branches") or {} for entry in alternatives}
    unknown = set(by_citation) - {p.citation for p in provisions}
    if unknown:
        raise RuleLayoutError(f"Alternatives for unknown provisions: {sorted(unknown)}")
    return [
        _with_branches(p, by_citation[p.citation]) if p.citation in by_citation else p
        for p in provisions
    ]


def _make_question(
    raw: dict[str, Any], question_id: str, stage: str, citation: str = "", title: Any = ""
) -> Question:
    return Question(
        id=question_id,
        wording=raw.get("question") or raw.get("main_question") or "",
        source_ref=str(raw.get("source_ref") or ""),
        stage=stage,
        citation=citation,
        heading=title,
        on_yes=str(raw.get("on_yes") or CONTINUE),
        on_no=str(raw.get("on_no") or CONTINUE),
        effect=raw.get("effect_note") or "",
    )


@dataclass
class Walkthrough:
    """Asks the next question and derives the final Finding."""

    layout: dict[str, Any] = field(default_factory=dict)
    preliminary_questions: tuple[Question, ...] = ()
    notes: tuple[Question, ...] = ()
    provisions: tuple[Provision, ...] = ()
    filter_questions: tuple[Question, ...] = ()
    profiling_question: Question | None = None
    annex_i_gate: Question | None = None
    annex_i_categories: tuple[Question, ...] = ()
    annex_i_conditions: tuple[dict[str, Any], ...] = ()
    annex_i_questions: dict[str, Question] = field(default_factory=dict)
    area_questions: tuple[Question, ...] = ()
    source_entries: tuple[Any, ...] = ()

    @classmethod
    def load(cls, rules_root: Path | None = None) -> Walkthrough:
        rules_root = rules_root or directory()
        layout = yaml.safe_load(
            (rules_root / "question_flow_layout.yaml").read_text(encoding="utf-8")
        )
        parts = {}
        for file in sorted((rules_root / "question_flow").glob("*.yaml")):
            parts[file.stem] = yaml.safe_load(file.read_text(encoding="utf-8"))

        preliminary_and_filter = parts["preliminaries-and-filter"]
        by_id = {f["id"]: f for f in preliminary_and_filter.get("preliminary_questions", [])}
        gates: list[Question] = []
        notes: list[Question] = []
        for entry in layout.get("preliminary_questions", []):
            raw = by_id.get(entry["id"])
            if raw is None:
                logger.warning("Preliminary question %s missing from data", entry["id"])
                continue
            f = _make_question(raw, entry["id"], "preliminary")
            (gates if entry.get("kind") == "gate" else notes).append(f)

        gates_by_area = layout.get("gates_by_area") or {}
        order = [b["citation"] for b in layout.get("areas", [])]
        title_by_area = {b["citation"]: b["title"] for b in layout.get("areas", [])}

        provisions: list[Provision] = []
        for name, content in parts.items():
            for position, raw in enumerate(content.get("provisions") or []):
                provision_citation = str(raw.get("citation") or "")
                area = next((b for b in order if provision_citation.startswith(b)), "")
                if not area:
                    logger.warning("Provision %s belongs to no area", provision_citation)
                    continue
                provisions.append(
                    Provision(
                        citation=provision_citation,
                        area=area,
                        heading=title_by_area.get(area, ""),
                        # Id includes file and position: Annex III point 2 has four
                        # provisions under the same citation.
                        main_question=_make_question(
                            raw,
                            f"main:{name}:{position}",
                            "provision",
                            provision_citation,
                            content.get("title", ""),
                        ),
                        follow_up_questions=tuple(
                            _make_question(
                                f,
                                f"follow-up:{name}:{position}:{i}",
                                "provision",
                                provision_citation,
                                content.get("title", ""),
                            )
                            for i, f in enumerate(
                                _ordered_follow_ups(raw.get("follow_up_questions") or [])
                            )
                        ),
                        covered_entries=tuple(raw.get("covered") or []),
                        not_covered_entries=tuple(raw.get("not_covered") or []),
                        example_entries=tuple(raw.get("examples") or []),
                        is_area_gate=gates_by_area.get(area) == provision_citation,
                    )
                )
        provisions.sort(
            key=lambda p: (
                order.index(p.area) if p.area in order else 99,
                0 if p.is_area_gate else 1,
                p.citation,
            )
        )
        provisions = _apply_alternatives(provisions, layout.get("alternatives") or [])

        filter_rule = preliminary_and_filter.get("filter") or {}
        filter_questions = tuple(
            _make_question(b, f"filter:{b.get('id')}", "filter")
            for b in filter_rule.get("conditions") or []
        )
        profiling_entry = filter_rule.get("profiling_counter_exemption") or {}
        profiling_question = (
            _make_question(profiling_entry, "filter:profiling", "filter")
            if profiling_entry
            else None
        )

        annex_i_data = parts.get("annex-i-products") or {}
        annex_i_layout = layout.get("annex_i") or {}
        skipped_questions = set(annex_i_layout.get("skipped_questions") or [])
        annex_i_questions_by_key = {
            f["id"]: _make_question(f, f"annex-i:{f['id']}", "annex_i", ANNEX_I_CITATION)
            for f in annex_i_data.get("questions") or []
            if f.get("id") not in skipped_questions
        }
        annex_i_gate_id = annex_i_layout.get("gate") or ""
        annex_i_gate_question = annex_i_questions_by_key.pop(annex_i_gate_id, None)
        annex_i_category_questions = tuple(
            _make_question(
                g,
                f"annex-i-category:{g.get('id')}",
                "annex_i",
                ANNEX_I_CITATION,
                g.get("common_name") or "",
            )
            for g in annex_i_data.get("product_categories") or []
            if g.get("question")
        )

        area_questions = tuple(
            Question(
                id="area:" + b["citation"],
                wording=b.get("question") or "",
                source_ref="",
                stage="area",
                citation=b["citation"],
                heading=b.get("title") or "",
            )
            for b in layout.get("areas", [])
            if b.get("question")
        )

        source_entries = tuple(
            {
                _data_text(i["source"], Language.DE): i["source"]
                for i in parts.values()
                if i.get("source")
            }.values()
        )
        return cls(
            layout=layout,
            preliminary_questions=tuple(gates),
            notes=tuple(notes),
            provisions=tuple(provisions),
            filter_questions=filter_questions,
            profiling_question=profiling_question,
            annex_i_gate=annex_i_gate_question,
            annex_i_categories=annex_i_category_questions,
            annex_i_conditions=tuple(annex_i_layout.get("conditions") or []),
            annex_i_questions=annex_i_questions_by_key,
            area_questions=area_questions,
            source_entries=source_entries,
        )

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(sorted(str(pick(source)) for source in self.source_entries))

    def _preliminary_entry(self, question_id: str) -> dict[str, Any]:
        entries: list[dict[str, Any]] = self.layout.get("preliminary_questions", [])
        for e in entries:
            if e.get("id") == question_id:
                return e
        return {}

    def _provision_blocked(self, provision: Provision, answers: dict[str, Any]) -> bool:
        """Whether a preliminary question already excluded this provision."""
        for f in self.preliminary_questions:
            entry = self._preliminary_entry(f.id)
            affected = entry.get("applies_to") or []
            if provision.citation not in affected:
                continue
            answer = answers.get(f.id)
            if answer is False and not entry.get("supplementary_only"):
                return True
        return False

    def _area_deselected(self, provision: Provision, answers: dict[str, Any]) -> bool:
        """Whether the user deselected this area in the area step."""
        return answers.get("area:" + provision.area) is False

    def _area_blocked(self, provision: Provision, answers: dict[str, Any]) -> bool:
        """Whether a denied area gate closed this provision (closed, not open)."""
        gate = (self.layout.get("gates_by_area") or {}).get(provision.area)
        if not gate or gate == provision.citation:
            return False
        gate_provision = next((p for p in self.provisions if p.citation == gate), None)
        if gate_provision is None:
            return False
        return answers.get(gate_provision.main_question.id) is False

    def provision_finding(self, provision: Provision, answers: dict[str, Any]) -> str:
        """State of a provision given the answers so far.

        Provisions inside a compound never apply alone; the compound decides. An area gate only
        opens its area and never applies itself, because broad gates (points 6 and 7) do not
        know the exemptions of the letters below them.
        """
        if (
            self._provision_blocked(provision, answers)
            or self._area_blocked(provision, answers)
            or self._area_deselected(provision, answers)
        ):
            return NOT_COVERED
        if self._compound(provision.area) is not None:
            return NOT_COVERED
        main_answer = answers.get(provision.main_question.id)
        if main_answer is None:
            return CONTINUE
        if main_answer is False:
            return NOT_COVERED
        if provision.is_area_gate:
            return NOT_COVERED
        return _evaluate_chains(provision.chains, answers)

    def _group_waived(self, group: dict[str, Any], answers: dict[str, Any]) -> bool:
        """Whether an Annex I condition group is waived.

        Art. 6(1)(a) requires a safety component of a product OR the product itself.
        """
        for k in group.get("waived_when") or []:
            question = self.annex_i_questions.get(k)
            if question is not None and answers.get(question.id) is True:
                return True
        return False

    def _group_ids(self, group: dict[str, Any], key: str) -> list[str]:
        return [
            self.annex_i_questions[k].id
            for k in group.get(key) or []
            if k in self.annex_i_questions
        ]

    def annex_i_finding(self, answers: dict[str, Any]) -> str:
        """Annex I state under Art. 6(1).

        An affirmed category and every condition group must hold; a group holds when one of its
        questions is affirmed and none of its exclusions is. A group left open only by "don't
        know" answers makes the finding CONDITIONAL; one denied group ends the path. A category
        the user does not know confirms no regulated product: the path ends and stays open.
        """
        if self.annex_i_gate is None:
            return NOT_COVERED
        gate = answers.get(self.annex_i_gate.id)
        if gate is None:
            return CONTINUE
        if gate is False:
            return NOT_COVERED
        categories = _any_of_state((g.id for g in self.annex_i_categories), answers)
        if categories != COVERED:
            return CONTINUE if categories == CONTINUE else NOT_COVERED
        conditional = False
        for group in self.annex_i_conditions:
            if self._group_waived(group, answers):
                continue
            state = _any_of_state(self._group_ids(group, "any_of"), answers)
            if state in (CONTINUE, NOT_COVERED):
                return state
            conditional = conditional or state == CONDITIONAL
            for k in self._group_ids(group, "exclusion"):
                if k not in answers:
                    return CONTINUE
                if answers[k] is True:
                    return NOT_COVERED
        return CONDITIONAL if conditional else COVERED

    def annex_i_open(self, answers: dict[str, Any]) -> bool:
        """Whether Annex I stays open because no category was affirmed, only left unknown."""
        if self.annex_i_gate is None or answers.get(self.annex_i_gate.id) in (None, False):
            return False
        return _any_of_state((g.id for g in self.annex_i_categories), answers) == CONDITIONAL

    def _next_annex_i_question(self, answers: dict[str, Any]) -> Question | None:
        if self.annex_i_gate is None:
            return None
        if self.annex_i_gate.id not in answers:
            return self.annex_i_gate
        if answers[self.annex_i_gate.id] is False:
            return None
        for g in self.annex_i_categories:
            if g.id not in answers:
                return g
        if _any_of_state((g.id for g in self.annex_i_categories), answers) != COVERED:
            return None
        questions = {q.id: q for q in self.annex_i_questions.values()}
        for group in self.annex_i_conditions:
            if self._group_waived(group, answers):
                continue
            ids = self._group_ids(group, "any_of")
            for k in ids:
                if k not in answers:
                    return questions[k]
            if _any_of_state(ids, answers) == NOT_COVERED:
                return None
            for k in self._group_ids(group, "exclusion"):
                if k not in answers:
                    return questions[k]
        return None

    def _compound(self, area: str) -> dict[str, Any] | None:
        compounds: list[dict[str, Any]] = self.layout.get("compounds") or []
        for v in compounds:
            if v.get("area") == area:
                return v
        return None

    def _compound_provision_state(self, provision: Provision, answers: dict[str, Any]) -> str:
        """State of one compound provision.

        Met when the main question is affirmed, no exemption applies and, where the provision
        enumerates traits, at least one trait is affirmed.
        """
        main_answer = answers.get(provision.main_question.id)
        if main_answer is None:
            return CONTINUE
        if main_answer is False:
            return NOT_COVERED
        enumeration = [
            f for f in provision.follow_up_questions if _answer_effect(f, True) == CONTINUE
        ]
        pending = any(f.id not in answers for f in provision.follow_up_questions)
        for f in provision.follow_up_questions:
            if _answer_effect(f, answers.get(f.id)) == NOT_COVERED:
                return NOT_COVERED
        if enumeration and not any(answers.get(f.id) is True for f in enumeration):
            return CONTINUE if pending else NOT_COVERED
        return CONTINUE if pending else COVERED

    def compound_finding(self, area: str, answers: dict[str, Any]) -> str:
        """State of a compound area; all its provisions must apply.

        A condition the user cannot know may stay open; the result is then CONDITIONAL
        instead of a false NOT_COVERED.
        """
        v = self._compound(area)
        if v is None:
            return NOT_COVERED
        marker = str(pick(v.get("special_case_main_question_contains"), Language.DE) or "")
        if answers.get("area:" + area) is False:
            return NOT_COVERED
        provisions = [p for p in self.provisions if p.area == area]
        rule = [p for p in provisions if not (marker and marker in p.main_question.german_text)]
        if not rule:
            return NOT_COVERED
        may_stay_open = v.get("may_stay_open") or {}
        open_marker = str(pick(may_stay_open.get("main_question_contains"), Language.DE) or "")
        findings = []
        conditional = False
        for provision in rule:
            finding = self._compound_provision_state(provision, answers)
            if (
                open_marker
                and open_marker in provision.main_question.german_text
                and finding == NOT_COVERED
                and answers.get(provision.main_question.id) is not False
            ):
                conditional = True
                continue
            findings.append(finding)
        if NOT_COVERED in findings:
            return NOT_COVERED
        if CONTINUE in findings:
            return CONTINUE
        return CONDITIONAL if conditional else COVERED

    def next_question(self, answers: dict[str, Any]) -> Question | None:
        """Next question to ask, or None when the result is settled.

        Order: gate preliminaries, Annex I (Art. 6(1) precedes 6(2)), area selection, provisions
        area by area, then the Art. 6(3) filter and profiling only if a provision applies.
        """
        for f in self.preliminary_questions:
            if f.id not in answers:
                return f
            entry = self._preliminary_entry(f.id)
            if answers[f.id] is False and entry.get("on_no") == END:
                return None

        question = self._next_annex_i_question(answers)
        if question is not None:
            return question

        for f in self.area_questions:
            if f.id not in answers:
                return f

        skipped_areas: set[str] = set()
        for provision in self.provisions:
            if provision.area in skipped_areas:
                continue
            # Must mirror provision_finding exactly; scripts/check_parity.py guards this.
            if (
                self._provision_blocked(provision, answers)
                or self._area_blocked(provision, answers)
                or self._area_deselected(provision, answers)
            ):
                continue
            if provision.main_question.id not in answers:
                return provision.main_question
            if answers[provision.main_question.id] is False:
                if provision.is_area_gate:
                    skipped_areas.add(provision.area)
                continue
            for f in provision.follow_up_questions:
                if f.id not in answers:
                    return f

        applies = any(
            self.provision_finding(p, answers) == COVERED for p in self.provisions
        ) or any(
            self.compound_finding(str(v.get("area")), answers) == COVERED
            for v in self.layout.get("compounds") or []
        )
        if applies:
            for f in self.filter_questions:
                if f.id not in answers:
                    return f
            if (
                any(answers.get(f.id) is True for f in self.filter_questions)
                and self.profiling_question
                and self.profiling_question.id not in answers
            ):
                return self.profiling_question
        return None

    def next_group(self, answers: dict[str, Any]) -> tuple[Question, ...]:
        """All questions shown together on one page (one step).

        Steps: preliminaries, area selection, Annex I gate, Annex I categories, Annex I
        conditions, open main questions, one provision's follow-ups, the Art. 6(3) filter, then
        profiling (only relevant after an affirmed filter condition).
        """
        first_question = self.next_question(answers)
        if first_question is None:
            return ()

        def pending(questions: Iterable[Question]) -> tuple[Question, ...]:
            return tuple(q for q in questions if q.id not in answers)

        if first_question.stage == "preliminary":
            return pending(self.preliminary_questions)
        if first_question.stage == "area":
            return pending(self.area_questions)

        if first_question.stage == "annex_i":
            if self.annex_i_gate is not None and first_question.id == self.annex_i_gate.id:
                return (first_question,)
            if first_question.id.startswith("annex-i-category:"):
                return pending(self.annex_i_categories)
            return pending(tuple(self.annex_i_questions.values()))

        if first_question.stage == "filter":
            if self.profiling_question and first_question.id == self.profiling_question.id:
                return (first_question,)
            return pending(self.filter_questions)

        if first_question.id.startswith("main:"):
            group: list[Question] = []
            blocked: set[str] = set()
            for provision in self.provisions:
                if provision.area in blocked:
                    continue
                if (
                    self._provision_blocked(provision, answers)
                    or self._area_blocked(provision, answers)
                    or self._area_deselected(provision, answers)
                ):
                    continue
                if provision.main_question.id in answers:
                    if answers[provision.main_question.id] is False and provision.is_area_gate:
                        blocked.add(provision.area)
                    continue
                group.append(provision.main_question)
            return tuple(group)

        found = next((p for p in self.provisions if p.citation == first_question.citation), None)
        if found is None:
            return (first_question,)
        # Several provisions can share a citation (Annex III point 2 has four).
        for candidate in self.provisions:
            if any(f.id == first_question.id for f in candidate.follow_up_questions):
                found = candidate
                break
        return pending(found.follow_up_questions)

    def result(self, answers: dict[str, Any]) -> Finding:
        """Derive the Finding from the answers.

        Annex I comes first (Art. 6(1) precedes 6(2)); an Annex I path left open by "don't know"
        answers yields to an Annex III high-risk finding but not to "not high risk".
        """
        ai_question_id = self.preliminary_questions[0].id if self.preliminary_questions else ""
        if answers.get(ai_question_id) is False:
            entry = self._preliminary_entry(ai_question_id)
            return Finding(
                risk_class="not_ai_system",
                matched_provisions=(),
                filter_applies=False,
                filter_reason="",
                evidence=_references(self.preliminary_questions[0].source_ref),
                open_provisions=(),
                closing_text=_data_text(entry.get("closing_text")),
            )
        annex_i = self.annex_i_finding(answers)
        if annex_i == COVERED:
            return self._annex_i_result(answers, conditional=False, open_provisions=())
        finding = self._annex_iii_result(answers)
        if self.annex_i_open(answers):
            finding = dataclasses.replace(
                finding, open_provisions=(*finding.open_provisions, ANNEX_I_CITATION)
            )
        if annex_i == CONDITIONAL and finding.risk_class in (
            "not_high_risk",
            "high_risk_exemption",
        ):
            return self._annex_i_result(
                answers, conditional=True, open_provisions=finding.open_provisions
            )
        return finding

    def _annex_i_category(self, answers: dict[str, Any]) -> Question | None:
        return next((g for g in self.annex_i_categories if answers.get(g.id) is True), None)

    def _annex_i_result(
        self, answers: dict[str, Any], conditional: bool, open_provisions: tuple[str, ...]
    ) -> Finding:
        layout = self.layout.get("annex_i") or {}
        category = self._annex_i_category(answers)
        product = _data_text(category.heading if category else layout.get("product_fallback"))
        return Finding(
            risk_class="high_risk_conditional" if conditional else "high_risk_annex_i",
            matched_provisions=(),
            filter_applies=False,
            filter_reason="",
            evidence=_references(
                self.annex_i_gate.source_ref if self.annex_i_gate else "",
                category.source_ref if category else "",
            ),
            open_provisions=open_provisions,
            closing_text=_with_product(
                layout.get("when_open" if conditional else "closing_text"), product
            ),
        )

    def _annex_iii_result(self, answers: dict[str, Any]) -> Finding:
        matched = [p for p in self.provisions if self.provision_finding(p, answers) == COVERED]
        pending = [
            p.citation for p in self.provisions if self.provision_finding(p, answers) == CONTINUE
        ]
        for v in self.layout.get("compounds") or []:
            area = str(v.get("area"))
            finding = self.compound_finding(area, answers)
            if finding == COVERED:
                matched += [p for p in self.provisions if p.area == area][:1]
            elif finding == CONDITIONAL:
                first_provision = [p for p in self.provisions if p.area == area][:1]
                may_stay_open = v.get("may_stay_open") or {}
                return Finding(
                    risk_class="high_risk_conditional",
                    matched_provisions=tuple(first_provision),
                    filter_applies=False,
                    filter_reason="",
                    evidence=_references(str(may_stay_open.get("source_ref") or "")),
                    open_provisions=tuple(pending),
                    closing_text=_data_text(may_stay_open.get("when_open")),
                )
            elif finding == CONTINUE:
                pending.append(area)
        if not matched:
            return Finding(
                risk_class="not_high_risk",
                matched_provisions=(),
                filter_applies=False,
                filter_reason="",
                evidence=(),
                open_provisions=tuple(pending),
            )

        condition = next((f for f in self.filter_questions if answers.get(f.id) is True), None)
        profiling = answers.get(self.profiling_question.id) if self.profiling_question else None
        # Art. 6(3): a filter condition exempts only if the system performs no profiling.
        if condition is not None and profiling is False:
            return Finding(
                risk_class="high_risk_exemption",
                matched_provisions=tuple(matched),
                filter_applies=True,
                filter_reason=condition.text,
                evidence=_references(
                    condition.source_ref,
                    self.profiling_question.source_ref if self.profiling_question else "",
                ),
                open_provisions=tuple(pending),
            )
        return Finding(
            risk_class="high_risk_annex_iii",
            matched_provisions=tuple(matched),
            filter_applies=False,
            filter_reason="",
            evidence=_references(*(p.main_question.source_ref for p in matched)),
            open_provisions=tuple(pending),
        )

    def figures(self) -> dict[str, int]:
        """Counts of questions, provisions, exclusions and examples."""
        return {
            "preliminary_questions": len(self.preliminary_questions),
            "notes": len(self.notes),
            "provisions": len(self.provisions),
            "questions": len(self.preliminary_questions)
            + sum(1 + len(p.follow_up_questions) for p in self.provisions)
            + len(self.filter_questions)
            + (1 if self.profiling_question else 0)
            + (1 if self.annex_i_gate else 0)
            + len(self.annex_i_categories)
            + len(self.annex_i_questions)
            + len(self.area_questions),
            "exclusions": sum(len(p.not_covered) for p in self.provisions),
            "examples": sum(len(p.examples) for p in self.provisions),
        }
