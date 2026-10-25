/* Question-flow walkthrough for the static web page; mirrors classification/question_flow.py.
 *
 * Context: lets the classification run in the browser without installation; any change
 * here or in the Python version must keep scripts/check_parity.py green | Input:
 * question_flow.json and the answers given so far | Output: the next question group
 * and the final finding (risk class, matched provisions, evidence). Data texts are
 * plain strings or bilingual {de, en} objects; matching always uses the German text.
 */

export const COVERED = "covered";
export const NOT_COVERED = "not_covered";
export const CONTINUE = "continue";
export const END = "end";
export const CONDITIONAL = "conditional";
export const NOT_APPLICABLE = "not_applicable";
export const SOURCE_LANGUAGE = "de";
export const ANNEX_I_CITATION = "AI-Act/annex-I";

export function pick(value, language = SOURCE_LANGUAGE) {
  if (value && typeof value === "object" && SOURCE_LANGUAGE in value) {
    return value[language] || value[SOURCE_LANGUAGE];
  }
  return value;
}

function sourceText(value) {
  return pick(value, SOURCE_LANGUAGE) || "";
}

function singleLine(value) {
  return String(value || "").split(/\s+/).join(" ").trim();
}

function references(...refs) {
  return refs.filter(Boolean);
}

function withProduct(template, product, language) {
  return singleLine(pick(template, language)).replace("{product}", product);
}

function anyOfState(ids, answers) {
  const given = ids.map((k) => answers[k]);
  if (given.some((a) => a === true)) return COVERED;
  if (given.some((a) => a === undefined)) return CONTINUE;
  if (given.some((a) => a === NOT_APPLICABLE)) return CONDITIONAL;
  return NOT_COVERED;
}

function answerEffect(question, answer) {
  if (answer === true) return question.on_yes;
  if (answer === false) return question.on_no;
  return CONTINUE;
}

function evaluateChain(questions, answers) {
  let excludes = false;
  let applies = false;
  let pending = false;
  for (const f of questions) {
    const answer = answers[f.id];
    if (answer === undefined) { pending = true; continue; }
    const effect = answerEffect(f, answer);
    if (effect === NOT_COVERED) excludes = true;
    else if (effect === COVERED) applies = true;
  }
  if (excludes) return NOT_COVERED;
  if (applies) return COVERED;
  return pending ? CONTINUE : NOT_COVERED;
}

function evaluateChains(chains, answers) {
  const findings = chains.map((chain) => evaluateChain(chain, answers));
  if (findings.includes(COVERED)) return COVERED;
  return findings.includes(CONTINUE) ? CONTINUE : NOT_COVERED;
}

function markedQuestion(citation, marker, questions) {
  const found = questions.filter((f) => sourceText(f.text).includes(marker));
  if (found.length !== 1) {
    throw new Error(`Alternative of ${citation}: "${marker}" matches ${found.length} questions, expected one`);
  }
  return found[0];
}

function provisionBranches(provision, branches) {
  const marked = (markers) =>
    (markers || []).map((marker) => markedQuestion(provision.citation, marker, provision.follow_up_questions).id);
  const alternatives = Object.values(branches).map((branch) => ({
    members: new Set(marked(branch.questions)),
    required: new Set(marked(branch.required)),
  }));
  const owned = alternatives.flatMap(({members, required}) => [...members, ...required]);
  if (new Set(owned).size !== owned.length) {
    throw new Error(`Alternatives of ${provision.citation} share a question`);
  }
  return alternatives.map(({members, required}) => provision.follow_up_questions
    .filter((f) => !owned.includes(f.id) || members.has(f.id) || required.has(f.id))
    .map((f) => (required.has(f.id) ? {...f, on_no: NOT_COVERED} : f)));
}

export class Walkthrough {
  constructor(data) {
    this.d = data;
    this.layout = data.layout || {};
    this.preliminary_questions = data.preliminary_questions || [];
    this.notes = data.notes || [];
    this.provisions = data.provisions || [];
    this.filter_questions = data.filter_questions || [];
    this.profiling_question = data.profiling_question || null;
    this.annexI = data.annex_i || {};
    this.area_questions = data.area_questions || [];
    this.chains = new Map();
    for (const entry of this.layout.alternatives || []) {
      const matching = this.provisions.filter((p) => p.citation === entry.citation);
      if (!matching.length) throw new Error(`Alternatives for unknown provision ${entry.citation}`);
      for (const p of matching) this.chains.set(p, provisionBranches(p, entry.branches || {}));
    }
  }

  provisionChains(provision) {
    return this.chains.get(provision) || [provision.follow_up_questions];
  }

  preliminaryEntry(id) {
    return (this.layout.preliminary_questions || []).find((e) => e.id === id) || {};
  }

  provisionBlocked(provision, answers) {
    for (const f of this.preliminary_questions) {
      const e = this.preliminaryEntry(f.id);
      const affected = e.applies_to || [];
      if (!affected.includes(provision.citation)) continue;
      if (answers[f.id] === false && !e.supplementary_only) return true;
    }
    return false;
  }

  areaDeselected(provision, answers) {
    return answers["area:" + provision.area] === false;
  }

  areaBlocked(provision, answers) {
    const gate = (this.layout.gates_by_area || {})[provision.area];
    if (!gate || gate === provision.citation) return false;
    const gateProvision = this.provisions.find((p) => p.citation === gate);
    if (!gateProvision) return false;
    return answers[gateProvision.main_question.id] === false;
  }

  compound(area) {
    return (this.layout.compounds || []).find((v) => v.area === area) || null;
  }

  compoundProvisionState(provision, answers) {
    const mainAnswer = answers[provision.main_question.id];
    if (mainAnswer === undefined) return CONTINUE;
    if (mainAnswer === false) return NOT_COVERED;
    const enumeration = provision.follow_up_questions.filter((f) => answerEffect(f, true) === CONTINUE);
    const pending = provision.follow_up_questions.some((f) => answers[f.id] === undefined);
    for (const f of provision.follow_up_questions) {
      if (answerEffect(f, answers[f.id]) === NOT_COVERED) return NOT_COVERED;
    }
    if (enumeration.length && !enumeration.some((f) => answers[f.id] === true)) {
      return pending ? CONTINUE : NOT_COVERED;
    }
    return pending ? CONTINUE : COVERED;
  }

  compoundFinding(area, answers) {
    const v = this.compound(area);
    if (!v) return NOT_COVERED;
    if (answers["area:" + area] === false) return NOT_COVERED;
    const marker = sourceText(v.special_case_main_question_contains);
    const ruleProvisions = this.provisions.filter(
      (p) => p.area === area && !(marker && sourceText(p.main_question.text).includes(marker))
    );
    if (!ruleProvisions.length) return NOT_COVERED;
    const mayStayOpen = v.may_stay_open || {};
    const openMarker = sourceText(mayStayOpen.main_question_contains);
    const findings = [];
    let conditional = false;
    for (const provision of ruleProvisions) {
      const finding = this.compoundProvisionState(provision, answers);
      if (
        openMarker &&
        sourceText(provision.main_question.text).includes(openMarker) &&
        finding === NOT_COVERED &&
        answers[provision.main_question.id] !== false
      ) {
        conditional = true;
        continue;
      }
      findings.push(finding);
    }
    if (findings.includes(NOT_COVERED)) return NOT_COVERED;
    if (findings.includes(CONTINUE)) return CONTINUE;
    return conditional ? CONDITIONAL : COVERED;
  }

  provisionFinding(provision, answers) {
    if (
      this.provisionBlocked(provision, answers) ||
      this.areaBlocked(provision, answers) ||
      this.areaDeselected(provision, answers)
    ) {
      return NOT_COVERED;
    }
    if (this.compound(provision.area)) return NOT_COVERED;
    const mainAnswer = answers[provision.main_question.id];
    if (mainAnswer === undefined) return CONTINUE;
    if (mainAnswer === false) return NOT_COVERED;
    if (provision.is_area_gate) return NOT_COVERED;
    return evaluateChains(this.provisionChains(provision), answers);
  }

  groupWaived(group, answers) {
    for (const k of group.waived_when || []) {
      const f = (this.annexI.questions || {})[k];
      if (f && answers[f.id] === true) return true;
    }
    return false;
  }

  groupIds(group, key) {
    const questions = this.annexI.questions || {};
    return (group[key] || []).filter((k) => questions[k]).map((k) => questions[k].id);
  }

  annexIFinding(answers) {
    if (!this.annexI.gate) return NOT_COVERED;
    const gate = answers[this.annexI.gate.id];
    if (gate === undefined) return CONTINUE;
    if (gate === false) return NOT_COVERED;
    const categories = anyOfState((this.annexI.categories || []).map((g) => g.id), answers);
    if (categories !== COVERED) return categories === CONTINUE ? CONTINUE : NOT_COVERED;
    let conditional = false;
    for (const group of this.annexI.conditions || []) {
      if (this.groupWaived(group, answers)) continue;
      const state = anyOfState(this.groupIds(group, "any_of"), answers);
      if (state === CONTINUE || state === NOT_COVERED) return state;
      conditional = conditional || state === CONDITIONAL;
      for (const k of this.groupIds(group, "exclusion")) {
        if (answers[k] === undefined) return CONTINUE;
        if (answers[k] === true) return NOT_COVERED;
      }
    }
    return conditional ? CONDITIONAL : COVERED;
  }

  annexIOpen(answers) {
    if (!this.annexI.gate) return false;
    const gate = answers[this.annexI.gate.id];
    if (gate === undefined || gate === false) return false;
    return anyOfState((this.annexI.categories || []).map((g) => g.id), answers) === CONDITIONAL;
  }

  nextAnnexIQuestion(answers) {
    if (!this.annexI.gate) return null;
    if (answers[this.annexI.gate.id] === undefined) return this.annexI.gate;
    if (answers[this.annexI.gate.id] === false) return null;
    const categories = this.annexI.categories || [];
    for (const g of categories) {
      if (answers[g.id] === undefined) return g;
    }
    if (anyOfState(categories.map((g) => g.id), answers) !== COVERED) return null;
    const questions = Object.fromEntries(Object.values(this.annexI.questions || {}).map((f) => [f.id, f]));
    for (const group of this.annexI.conditions || []) {
      if (this.groupWaived(group, answers)) continue;
      const ids = this.groupIds(group, "any_of");
      for (const k of ids) {
        if (answers[k] === undefined) return questions[k];
      }
      if (anyOfState(ids, answers) === NOT_COVERED) return null;
      for (const k of this.groupIds(group, "exclusion")) {
        if (answers[k] === undefined) return questions[k];
      }
    }
    return null;
  }

  nextQuestion(answers) {
    for (const f of this.preliminary_questions) {
      if (answers[f.id] === undefined) return f;
      const e = this.preliminaryEntry(f.id);
      if (answers[f.id] === false && e.on_no === END) return null;
    }
    const annexI = this.nextAnnexIQuestion(answers);
    if (annexI) return annexI;

    for (const f of this.area_questions) {
      if (answers[f.id] === undefined) return f;
    }

    const skipped = new Set();
    for (const provision of this.provisions) {
      if (skipped.has(provision.area)) continue;
      if (
        this.provisionBlocked(provision, answers) ||
        this.areaBlocked(provision, answers) ||
        this.areaDeselected(provision, answers)
      ) continue;
      if (answers[provision.main_question.id] === undefined) return provision.main_question;
      if (answers[provision.main_question.id] === false) {
        if (provision.is_area_gate) skipped.add(provision.area);
        continue;
      }
      for (const f of provision.follow_up_questions) {
        if (answers[f.id] === undefined) return f;
      }
    }

    const applies =
      this.provisions.some((p) => this.provisionFinding(p, answers) === COVERED) ||
      (this.layout.compounds || []).some(
        (v) => this.compoundFinding(v.area, answers) === COVERED
      );
    if (applies) {
      for (const f of this.filter_questions) {
        if (answers[f.id] === undefined) return f;
      }
      if (this.filter_questions.some((f) => answers[f.id] === true) && this.profiling_question) {
        if (answers[this.profiling_question.id] === undefined) return this.profiling_question;
      }
    }
    return null;
  }

  nextGroup(answers) {
    const firstQuestion = this.nextQuestion(answers);
    if (!firstQuestion) return [];
    const pending = (questionList) => questionList.filter((f) => answers[f.id] === undefined);

    if (firstQuestion.stage === "preliminary") return pending(this.preliminary_questions);
    if (firstQuestion.stage === "area") return pending(this.area_questions);
    if (firstQuestion.stage === "annex_i") {
      if (this.annexI.gate && firstQuestion.id === this.annexI.gate.id) return [firstQuestion];
      if (firstQuestion.id.startsWith("annex-i-category:")) return pending(this.annexI.categories || []);
      return pending(Object.values(this.annexI.questions || {}));
    }
    if (firstQuestion.stage === "filter") {
      if (this.profiling_question && firstQuestion.id === this.profiling_question.id) return [firstQuestion];
      return pending(this.filter_questions);
    }
    if (firstQuestion.id.startsWith("main:")) {
      const group = [];
      const blocked = new Set();
      for (const provision of this.provisions) {
        if (blocked.has(provision.area)) continue;
        if (
          this.provisionBlocked(provision, answers) ||
          this.areaBlocked(provision, answers) ||
          this.areaDeselected(provision, answers)
        ) continue;
        if (answers[provision.main_question.id] !== undefined) {
          if (answers[provision.main_question.id] === false && provision.is_area_gate) {
            blocked.add(provision.area);
          }
          continue;
        }
        group.push(provision.main_question);
      }
      return group;
    }
    let provision = this.provisions.find((p) => p.follow_up_questions.some((f) => f.id === firstQuestion.id));
    if (!provision) provision = this.provisions.find((p) => p.citation === firstQuestion.citation);
    if (!provision) return [firstQuestion];
    return pending(provision.follow_up_questions);
  }

  result(answers, language = SOURCE_LANGUAGE) {
    const aiQuestionId = this.preliminary_questions.length ? this.preliminary_questions[0].id : "";
    if (answers[aiQuestionId] === false) {
      const e = this.preliminaryEntry(aiQuestionId);
      return {
        risk_class: "not_ai_system",
        matched_provisions: [],
        filter_applies: false,
        filter_reason: "",
        evidence: references(this.preliminary_questions[0].source_ref),
        open_provisions: [],
        closing_text: singleLine(pick(e.closing_text, language)),
      };
    }
    const annexI = this.annexIFinding(answers);
    if (annexI === COVERED) return this.annexIResult(answers, false, [], language);
    const finding = this.annexIIIResult(answers, language);
    if (this.annexIOpen(answers)) finding.open_provisions = [...finding.open_provisions, ANNEX_I_CITATION];
    if (annexI === CONDITIONAL && ["not_high_risk", "high_risk_exemption"].includes(finding.risk_class)) {
      return this.annexIResult(answers, true, finding.open_provisions, language);
    }
    return finding;
  }

  annexICategory(answers) {
    return (this.annexI.categories || []).find((g) => answers[g.id] === true) || null;
  }

  annexIResult(answers, conditional, openProvisions, language) {
    const layout = this.layout.annex_i || {};
    const category = this.annexICategory(answers);
    const product = category
      ? String(pick(category.title, language) || "")
      : singleLine(pick(layout.product_fallback, language));
    return {
      risk_class: conditional ? "high_risk_conditional" : "high_risk_annex_i",
      matched_provisions: [],
      filter_applies: false,
      filter_reason: "",
      evidence: references(this.annexI.gate && this.annexI.gate.source_ref, category && category.source_ref),
      open_provisions: openProvisions,
      closing_text: withProduct(conditional ? layout.when_open : layout.closing_text, product, language),
    };
  }

  annexIIIResult(answers, language) {
    const matched = this.provisions.filter((p) => this.provisionFinding(p, answers) === COVERED);
    const pending = this.provisions
      .filter((p) => this.provisionFinding(p, answers) === CONTINUE)
      .map((p) => p.citation);
    for (const v of this.layout.compounds || []) {
      const finding = this.compoundFinding(v.area, answers);
      if (finding === COVERED) {
        const firstProvision = this.provisions.find((p) => p.area === v.area);
        if (firstProvision) matched.push(firstProvision);
      } else if (finding === CONDITIONAL) {
        const firstProvision = this.provisions.find((p) => p.area === v.area);
        const mayStayOpen = v.may_stay_open || {};
        return {
          risk_class: "high_risk_conditional",
          matched_provisions: firstProvision ? [firstProvision] : [],
          filter_applies: false,
          filter_reason: "",
          evidence: references(mayStayOpen.source_ref),
          open_provisions: pending,
          closing_text: singleLine(pick(mayStayOpen.when_open, language)),
        };
      } else if (finding === CONTINUE) pending.push(v.area);
    }
    if (!matched.length) {
      return {
        risk_class: "not_high_risk",
        matched_provisions: [],
        filter_applies: false,
        filter_reason: "",
        evidence: [],
        open_provisions: pending,
        closing_text: "",
      };
    }
    const condition = this.filter_questions.find((f) => answers[f.id] === true) || null;
    const profiling = this.profiling_question ? answers[this.profiling_question.id] : undefined;
    if (condition && profiling === false) {
      return {
        risk_class: "high_risk_exemption",
        matched_provisions: matched,
        filter_applies: true,
        filter_reason: singleLine(pick(condition.text, language)),
        evidence: references(condition.source_ref, this.profiling_question && this.profiling_question.source_ref),
        open_provisions: pending,
        closing_text: "",
      };
    }
    return {
      risk_class: "high_risk_annex_iii",
      matched_provisions: matched,
      filter_applies: false,
      filter_reason: "",
      evidence: references(...matched.map((p) => p.main_question.source_ref)),
      open_provisions: pending,
      closing_text: "",
    };
  }
}
