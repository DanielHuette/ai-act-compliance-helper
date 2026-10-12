/* Browser client for the local compliance helper web UI.
 *
 * Context: talks only to this service's own API, so it works offline and no input
 * leaves the host; classification and answer get the same facts, so they agree |
 * Input: description, question and questionnaire answers from page.html, UI strings
 * and language from its #ui-text data block | Output: risk card, rationale,
 * obligations, evidence and deadlines in the page language, all rendered via
 * textContent; the entered form survives a switch of the page language.
 */
"use strict";

const UI = JSON.parse(document.getElementById("ui-text").textContent);

function say(key, values) {
  const template = UI.text[key] || key;
  return template.replace(/\{(\w+)\}/g, function (whole, name) {
    return (values && name in values) ? String(values[name]) : whole;
  });
}

function withLanguage(url) {
  return url + (url.indexOf("?") === -1 ? "?" : "&") + "lang=" + encodeURIComponent(UI.lang);
}

const form = document.getElementById("check-form");
const checkButton = document.getElementById("check-button");
const statusLine = document.getElementById("status-line");
const resultSection = document.getElementById("result");
const errorArea = document.getElementById("error-area");

function make(tag, cssClass, text) {
  const node = document.createElement(tag);
  if (cssClass) { node.className = cssClass; }
  if (text !== undefined && text !== null && text !== "") { node.textContent = text; }
  return node;
}

function clear(node) {
  while (node.firstChild) { node.removeChild(node.firstChild); }
}

function localDate(iso) {
  if (!iso) { return ""; }
  const parts = String(iso).split("-");
  if (UI.lang !== "de" || parts.length !== 3) { return String(iso); }
  return parts[2] + "." + parts[1] + "." + parts[0];
}

function showError(sentence, hint) {
  document.getElementById("error-text").textContent = sentence;
  document.getElementById("error-hint").textContent = hint || "";
  errorArea.hidden = false;
  errorArea.scrollIntoView({ behavior: "smooth", block: "center" });
}

/* The API returns user-facing errors in the "error" field; anything else is
 * replaced by a localized sentence so no raw server message reaches the user. */
async function post(url, payload) {
  let response;
  try {
    response = await fetch(withLanguage(url), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (failure) {
    throw new Error(say("service_unreachable"));
  }
  let data = null;
  try { data = await response.json(); } catch (failure) { data = null; }
  if (!response.ok) {
    const sentence = (data && data.error)
      ? data.error
      : say("error_status", { status: response.status });
    const error = new Error(sentence);
    error.hint = (data && data.hint) || "";
    throw error;
  }
  return data;
}

/* "Don't know" is the empty value and is not sent: an omitted trait becomes an
 * open question, while an explicit "no" is a statement that changes the result. */
function collectFacts() {
  const traits = {};
  const roles = [];
  document.querySelectorAll('#check-form .item').forEach(function (item) {
    const id = item.dataset.id;
    const kind = item.dataset.kind;
    if (kind === "choice") { return; }
    if (kind === "yes_no") {
      const chosen = item.querySelector('input[type="radio"]:checked');
      if (chosen && chosen.value !== "") { traits[id] = chosen.value; }
      return;
    }
    const field = item.querySelector('input[type="text"]');
    if (field && field.value.trim() !== "") { traits[id] = field.value.trim(); }
  });
  document.querySelectorAll('#check-form input[name="roles"]:checked')
    .forEach(function (box) { roles.push(box.value); });
  return { traits: traits, roles: roles };
}

/* Colour is decorative only; the badge word carries the meaning. */
const CARD_CLASS = {
  prohibited: "k-prohibited",
  high_risk_annex_i: "k-high",
  high_risk_annex_iii: "k-high",
  high_risk_exemption: "k-high",
  gpai_systemic_risk: "k-transparency",
  gpai: "k-transparency",
  transparency: "k-transparency",
  minimal: "k-minimal",
  unclear: ""
};

function renderCard(id, explanation, roles) {
  const card = document.getElementById("card");
  card.className = "risk-card " + (CARD_CLASS[id] || "");
  document.getElementById("card-badge").textContent = UI.text["badge_" + id] || id;
  document.getElementById("card-title").textContent = UI.text["title_" + id] || id;
  document.getElementById("card-text").textContent = explanation || "";

  const row = document.getElementById("card-roles");
  if (roles && roles.length) {
    row.textContent = say("your_role", {
      roles: roles.map(function (r) {
        return (UI.roles[r.id] || r.id) + " — " + r.explanation;
      }).join(" · ")
    });
  } else {
    row.textContent = say("role_missing");
  }
}

function renderRationale(indicators) {
  const target = document.getElementById("rationale");
  clear(target);
  if (!indicators || !indicators.length) {
    target.appendChild(make("p", "explanation", say("no_rationale")));
    return;
  }
  indicators.forEach(function (indicator) {
    const box = make("div", "reason");
    const sentence = make("p", null, indicator.rationale);
    const marker = make("span", "confidence s-" + indicator.confidence,
      UI.text["confidence_" + indicator.confidence] || indicator.confidence);
    sentence.appendChild(document.createTextNode(" "));
    sentence.appendChild(marker);
    box.appendChild(sentence);
    if (indicator.legal_basis && indicator.legal_basis.length) {
      box.appendChild(make("p", "citation",
        say("citations", { citations: (indicator.citations || indicator.legal_basis).join(", ") })));
    }
    target.appendChild(box);
  });
}

function renderObligations(targetId, obligations) {
  const target = document.getElementById(targetId);
  clear(target);
  if (!obligations || !obligations.length) {
    target.appendChild(make("p", "explanation", say("no_obligations")));
    return 0;
  }
  const today = new Date().toISOString().slice(0, 10);
  obligations.forEach(function (obligation, index) {
    const row = make("div", "obligation");

    const box = document.createElement("input");
    box.type = "checkbox";
    box.id = targetId + "-" + index;
    /* Checkbox state is deliberately not persisted; printing keeps the list. */
    row.appendChild(box);

    const body = make("div", "obligation-body");
    const title = make("label",
      "obligation-title" + (obligation.severity && obligation.severity !== "obligation"
        ? " severity-" + obligation.severity : ""),
      obligation.title);
    title.setAttribute("for", box.id);
    body.appendChild(title);
    body.appendChild(make("p", "obligation-action", obligation.action_required));

    const meta = make("div", "obligation-meta");
    meta.appendChild(make("span", "citation", obligation.citation_text));
    if (obligation.applies_from) {
      const upcoming = obligation.applies_from > today;
      meta.appendChild(make("span", "deadline" + (upcoming ? " pending" : ""),
        say(upcoming ? "applies_from" : "applies_since",
          { date: localDate(obligation.applies_from) })));
    }
    if (obligation.evidence_of_compliance) {
      meta.appendChild(make("span", null,
        say("evidence_of_compliance", { text: obligation.evidence_of_compliance })));
    }
    body.appendChild(meta);
    if (obligation.on_infringement) {
      body.appendChild(make("p", "citation",
        say("on_infringement", { text: obligation.on_infringement })));
    }
    row.appendChild(body);
    target.appendChild(row);
  });
  return obligations.length;
}

function routeNames(routes) {
  return (routes || []).map(function (route) {
    return UI.text["route_" + route] || route;
  }).join(", ");
}

function traitNames(ids) {
  return ids.map(function (id) {
    const question = document.getElementById("question-" + id);
    return question ? question.textContent : id;
  }).join("; ");
}

function renderEvidence(evidence) {
  const target = document.getElementById("evidence");
  clear(target);
  if (!evidence || !evidence.length) {
    target.appendChild(make("p", "explanation", say("no_evidence")));
    return;
  }
  evidence.forEach(function (passage, index) {
    const box = make("details", "passage");
    if (index === 0) { box.open = true; }
    const summary = document.createElement("summary");
    summary.appendChild(make("span", "passage-head", passage.citation));
    if (passage.title) {
      summary.appendChild(document.createTextNode(" "));
      summary.appendChild(make("span", "passage-title", "— " + passage.title));
    }
    box.appendChild(summary);
    box.appendChild(make("div", "wording", passage.excerpt));
    box.appendChild(make("p", "routes", say("found_via", { routes: routeNames(passage.routes) })));
    target.appendChild(box);
  });
}

let deadlinesLoaded = false;

async function renderDeadlines() {
  if (deadlinesLoaded) { return; }
  const target = document.getElementById("deadlines");
  let data;
  try {
    const response = await fetch(withLanguage("/api/deadlines"));
    if (!response.ok) { throw new Error("HTTP status " + response.status); }
    data = await response.json();
  } catch (failure) {
    clear(target);
    target.appendChild(make("p", "explanation", say("deadlines_failed")));
    return;
  }
  clear(target);
  const list = make("ul", "deadlines");
  data.stages.forEach(function (stage) {
    const row = make("li", "deadline-row " + (stage.already_in_force ? "in-force" : "upcoming"));
    row.appendChild(make("span", "deadline-date", localDate(stage.date_value)));
    row.appendChild(make("span", "deadline-badge",
      say(stage.already_in_force ? "deadline_in_force" : "deadline_upcoming")));
    row.appendChild(make("span", null, stage.event));
    list.appendChild(row);
  });
  target.appendChild(list);
  target.appendChild(make("p", "citation", say("deadline_citation", { citation: data.citation })));
  if (data.caveat) {
    target.appendChild(make("p", "caveat", data.caveat));
  }
  deadlinesLoaded = true;
}

function renderOpenQuestions(questions) {
  const block = document.getElementById("questions-block");
  const list = document.getElementById("open-questions");
  clear(list);
  if (!questions || !questions.length) { block.hidden = true; return; }
  questions.forEach(function (question) { list.appendChild(make("li", null, question)); });
  block.hidden = false;
}

async function runCheck() {
  errorArea.hidden = true;
  const description = document.getElementById("description").value.trim();
  const question = document.getElementById("question").value.trim();

  if (!description && !question) {
    showError(say("input_missing"), say("input_missing_hint"));
    return;
  }

  const facts = collectFacts();
  checkButton.disabled = true;
  statusLine.textContent = say("checking");

  try {
    const classificationResponse = await post("/api/classify",
      Object.assign({ description: description || question }, facts));

    const classification = classificationResponse.classification;
    renderCard(classificationResponse.most_severe_class,
      classificationResponse.most_severe_explanation,
      classificationResponse.role_explanations);
    renderRationale(classification.indicators);
    renderObligations("obligations", classification.obligations);
    const dataProtectionCount = renderObligations("data-protection",
      classification.data_protection);
    document.getElementById("data-protection-block").hidden = !dataProtectionCount;
    renderOpenQuestions(classification.open_questions);

    if (classificationResponse.unrecognized_traits
        && classificationResponse.unrecognized_traits.length) {
      showError(
        say("unrecognized", { traits: traitNames(classificationResponse.unrecognized_traits) }),
        say("unrecognized_hint"));
    }

    resultSection.hidden = false;
    statusLine.textContent = say("classified_composing");
    renderDeadlines();

    /* If the model-backed answer fails, the deterministic classification above
     * stays visible. */
    const answerResponse = await post("/api/ask",
      Object.assign({ question: question || say("default_question"), description: description },
        facts));
    const answer = answerResponse.answer;
    document.getElementById("answer").textContent = answer.text;
    document.getElementById("answer-source").textContent = answer.without_model
      ? say("answer_without_model")
      : say("answer_with_model", { model: answer.model });
    renderEvidence(answer.evidence);

    const learningBlock = document.getElementById("learning-block");
    if (answer.learning_note) {
      document.getElementById("learning-note").textContent = answer.learning_note;
      document.getElementById("example-cases").textContent =
        (answer.example_cases && answer.example_cases.length)
          ? say("example_cases", { cases: answer.example_cases.join(" · ") })
          : "";
      learningBlock.hidden = false;
    } else {
      learningBlock.hidden = true;
    }

    if (answer.warnings && answer.warnings.length) {
      showError(answer.warnings[0], answer.warnings.slice(1).join(" "));
    }
    statusLine.textContent = say("done", { ms: answerResponse.duration_ms || 0 });
    document.getElementById("card").scrollIntoView(
      { behavior: "smooth", block: "start" });

  } catch (error) {
    showError(error.message, error.hint);
    statusLine.textContent = "";
  } finally {
    checkButton.disabled = false;
  }
}

form.addEventListener("submit", function (event) {
  event.preventDefault();
  runCheck();
});

/* Shows the length limit before the API rejects an oversized description. */
const descriptionField = document.getElementById("description");
const charCount = document.getElementById("char-count");
function updateCharCount() {
  charCount.textContent = String(descriptionField.value.length);
}
descriptionField.addEventListener("input", updateCharCount);

/* The language links reload the page; the entered form and whether a result was
 * shown travel through sessionStorage, which may be unavailable or blocked. */
const STATE_KEY = "compliance-helper-search";

function formState() {
  const fields = [];
  Array.prototype.forEach.call(form.elements, function (element) {
    if (!element.name) { return; }
    if (element.type === "radio" || element.type === "checkbox") {
      if (element.checked) { fields.push([element.name, element.value]); }
    } else if (element.value) {
      fields.push([element.name, element.value]);
    }
  });
  return fields;
}

function restoreFormState(fields) {
  const saved = {};
  fields.forEach(function (entry) {
    saved[entry[0]] = (saved[entry[0]] || []).concat([String(entry[1])]);
  });
  Array.prototype.forEach.call(form.elements, function (element) {
    const values = saved[element.name];
    if (!values) { return; }
    if (element.type === "radio" || element.type === "checkbox") {
      element.checked = values.indexOf(element.value) !== -1;
    } else {
      element.value = values[0];
    }
  });
  const answered = Object.keys(saved).some(function (name) {
    return name !== "description" && name !== "question" && saved[name][0] !== "";
  });
  if (answered) { document.querySelector("details.questionnaire").open = true; }
}

function storeState(state) {
  try {
    sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch (failure) {
    return false;
  }
  return true;
}

function takeStoredState() {
  try {
    const raw = sessionStorage.getItem(STATE_KEY);
    sessionStorage.removeItem(STATE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (failure) {
    return null;
  }
}

document.querySelectorAll(".language-switch a").forEach(function (link) {
  link.addEventListener("click", function () {
    storeState({ fields: formState(), ran: !resultSection.hidden });
  });
});

const storedState = takeStoredState();
if (storedState && Array.isArray(storedState.fields)) {
  restoreFormState(storedState.fields);
  if (storedState.ran) { runCheck(); }
}
updateCharCount();
