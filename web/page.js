/* Page controller for the static classification walkthrough.
 *
 * Context: renders the questionnaire step by step on index.html without a server, in German
 * or English | Input: question_flow.json, locales/<language>.json, the ?lang= parameter and
 * the visitor's clicks | Output: translated page text, question groups, progress rail and the
 * final finding with citations and official examples.
 */
import {Walkthrough, NOT_APPLICABLE, pick} from "./walkthrough.js";

const SUPPORTED_LANGUAGES = ["de", "en"];
const DEFAULT_LANGUAGE = "de";
const LANGUAGE_STORAGE_KEY = "language";
const LANGUAGE_PARAMETER = "lang";

const RISK_CLASS_TONES = {
  high_risk_annex_iii: "high",
  high_risk_annex_i: "high",
  high_risk_conditional: "high",
  high_risk_exemption: "",
  not_high_risk: "minimal",
  not_ai_system: "minimal",
};

const stage = document.getElementById("stage");
const progressText = document.getElementById("progress-text");
const progressRight = document.getElementById("progress-right");
const progress = document.getElementById("progress");
const progressSteps = document.getElementById("progress-steps");
const canonicalLink = document.querySelector('link[rel="canonical"]');
const siteUrl = canonicalLink ? canonicalLink.href : "";

const catalogs = {};
let language = DEFAULT_LANGUAGE;
let flow = null;
let answers = {};
let screens = [];
let view = "loading";

function supportedLanguage(code) {
  const candidate = String(code || "").slice(0, 2).toLowerCase();
  return SUPPORTED_LANGUAGES.includes(candidate) ? candidate : null;
}

function languageFromUrl() {
  return supportedLanguage(new URLSearchParams(window.location.search).get(LANGUAGE_PARAMETER));
}

function storedLanguage() {
  try {
    return supportedLanguage(window.localStorage.getItem(LANGUAGE_STORAGE_KEY));
  } catch {
    return null;
  }
}

function storeLanguage(code) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, code);
    return true;
  } catch {
    return false;
  }
}

function browserLanguage() {
  for (const code of navigator.languages || [navigator.language]) {
    const supported = supportedLanguage(code);
    if (supported) return supported;
  }
  return null;
}

function initialLanguage() {
  return languageFromUrl() || storedLanguage() || browserLanguage() || DEFAULT_LANGUAGE;
}

async function loadCatalog(code) {
  if (!catalogs[code]) {
    const response = await fetch(`./locales/${code}.json`);
    if (!response.ok) throw new Error(`locales/${code}.json: HTTP ${response.status}`);
    catalogs[code] = await response.json();
  }
  return catalogs[code];
}

function t(key, values = {}) {
  const template = (catalogs[language] || {})[key] ?? (catalogs[DEFAULT_LANGUAGE] || {})[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (whole, name) => (name in values ? String(values[name]) : whole));
}

function text(value) {
  return pick(value, language) || "";
}

function el(tag, attrs = {}, childList = []) {
  const k = document.createElement(tag);
  for (const [n, v] of Object.entries(attrs)) {
    if (n === "text") k.textContent = v;
    else k.setAttribute(n, v);
  }
  for (const child of [].concat(childList)) if (child) k.append(child);
  return k;
}

function translateStaticText() {
  for (const node of document.querySelectorAll("[data-i18n]")) {
    node.textContent = t(node.dataset.i18n);
  }
  for (const node of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of node.dataset.i18nAttr.split(";")) {
      const [attribute, key] = pair.split(":").map((part) => part.trim());
      if (attribute && key) node.setAttribute(attribute, t(key));
    }
  }
  document.documentElement.lang = language;
  document.title = t("meta.title");
  for (const link of document.querySelectorAll(".language-switch a[data-language]")) {
    if (link.dataset.language === language) link.setAttribute("aria-current", "true");
    else link.removeAttribute("aria-current");
  }
}

function pageUrl() {
  if (!siteUrl || !languageFromUrl()) return siteUrl;
  const url = new URL(siteUrl);
  url.searchParams.set(LANGUAGE_PARAMETER, language);
  return url.href;
}

function updateDocumentLinks() {
  const url = pageUrl();
  if (canonicalLink && url) canonicalLink.href = url;
  const ogUrl = document.querySelector('meta[property="og:url"]');
  if (ogUrl && url) ogUrl.setAttribute("content", url);
}

function structuredData() {
  const faqNumbers = [...document.querySelectorAll("[data-i18n$='.question']")]
    .map((node) => node.dataset.i18n.split(".")[1]);
  const howToNumbers = Object.keys(catalogs[language] || {})
    .filter((key) => /^ld\.howTo\.\d+\.name$/.test(key))
    .map((key) => key.split(".")[2]);
  const featureKeys = Object.keys(catalogs[language] || {}).filter((key) => key.startsWith("ld.feature."));
  const inLanguage = t("ld.inLanguage");
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": siteUrl + "#webpage",
        url: siteUrl,
        name: t("meta.siteName"),
        inLanguage,
        description: t("ld.websiteDescription"),
      },
      {
        "@type": "SoftwareApplication",
        name: t("meta.siteName"),
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web, Windows, macOS, Linux",
        inLanguage,
        offers: {"@type": "Offer", price: "0", priceCurrency: "EUR"},
        license: "https://www.apache.org/licenses/LICENSE-2.0",
        author: {"@type": "Person", name: "Daniel Hütte"},
        description: t("ld.appDescription"),
        featureList: featureKeys.map((key) => t(key)),
      },
      {
        "@type": "HowTo",
        name: t("ld.howTo.name"),
        inLanguage,
        totalTime: "PT5M",
        step: howToNumbers.map((n) => ({
          "@type": "HowToStep",
          name: t(`ld.howTo.${n}.name`),
          text: t(`ld.howTo.${n}.text`),
        })),
      },
      {
        "@type": "FAQPage",
        inLanguage,
        mainEntity: faqNumbers.map((n) => ({
          "@type": "Question",
          name: t(`faq.${n}.question`),
          acceptedAnswer: {"@type": "Answer", text: t(`faq.${n}.answer`)},
        })),
      },
    ],
  };
}

function updateStructuredData() {
  const node = document.getElementById("structured-data");
  if (node) node.textContent = JSON.stringify(structuredData(), null, 1);
}

function updateVersion() {
  const version = document.getElementById("version");
  if (version && flow) version.textContent = t("version", {date: flow.d.as_of || "—"});
}

/* The rail shows the five fixed phases, not a step count: the number of
 * follow-up steps depends on the answers. */
function phaseOf(question) {
  if (!question) return 1;
  if (question.stage === "preliminary") return 1;
  if (question.stage === "area") return 2;
  if (question.stage === "filter") return 4;
  return 3;
}

function setProgressSteps(phase) {
  for (const li of progressSteps.children) {
    const n = Number(li.dataset.phase);
    li.classList.toggle("current", n === phase);
    li.classList.toggle("done", n < phase);
    li.firstElementChild.textContent = n < phase ? "✓" : String(n);
  }
}

function setProgress(label, right, share) {
  progressText.textContent = label;
  progressRight.textContent = right || "";
  progress.style.setProperty("--progress", (share || 0) + "%");
}

function countText(count, oneKey, manyKey) {
  return count === 1 ? t(oneKey) : t(manyKey, {count});
}

const PARAGRAPH_AFTER = /^\(nach (\d+)\)$/;

function paragraphNumber(sourceRef) {
  const after = PARAGRAPH_AFTER.exec(sourceRef);
  if (after) return t("question.after", {ref: after[1]});
  return String(sourceRef).replace(/[()]/g, "");
}

function paragraphLabel(sourceRef) {
  const after = PARAGRAPH_AFTER.exec(sourceRef);
  if (after) return t("question.paragraphAfter", {ref: after[1]});
  return t("question.paragraph", {ref: paragraphNumber(sourceRef)});
}

function drawStart() {
  stage.replaceChildren(
    el("h2", {text: t("start.heading")}),
    el("p", {text: t("start.intro")}),
    el("p", {text: t("start.method")}),
    el("p", {class: "muted", text: t("start.privacy")}),
    el("div", {class: "actions"}, [
      el("button", {class: "button", id: "start", text: t("start.button")}),
    ]),
    el("p", {class: "source", text: t("start.source")}),
  );
  document.getElementById("start").onclick = begin;
  setProgressSteps(0);
  setProgress(t("progress.ready"), "", 0);
}

function areaName(question) {
  const area = (flow.layout.areas || []).find((x) => question.citation.startsWith(x.citation));
  return area ? text(area.title) : text(question.title);
}

function headingFor(firstQuestion) {
  if (firstQuestion.stage === "preliminary") return t("heading.preliminary");
  if (firstQuestion.stage === "area") return t("heading.area");
  if (firstQuestion.id.startsWith("main:")) return areaName(firstQuestion) || t("heading.main");
  if (firstQuestion.id.startsWith("annex-i-category:")) return t("heading.annexICategory");
  if (firstQuestion.stage === "annex_i") return t("heading.annexI");
  if (firstQuestion.stage === "filter") return t("heading.filter");
  return areaName(firstQuestion) || t("heading.other");
}

function drawQuestions({scroll = true} = {}) {
  const group = screens[screens.length - 1];
  const step = screens.length;
  const firstQuestion = group[0];
  const heading = headingFor(firstQuestion);
  setProgressSteps(phaseOf(firstQuestion));
  setProgress(t("progress.step", {step, heading}),
    countText(group.length, "progress.questionsOne", "progress.questionsMany"),
    Math.min(92, Math.round((step / Math.max(step + 1, 6)) * 100)));

  const parts = [el("h2", {text: heading})];
  if (firstQuestion.stage === "area") {
    parts.push(el("p", {class: "hint", text: t("group.areaHint")}));
  }

  const list = el("ul", {class: "questions"});
  let lastArea = null;
  for (const f of group) {
    if (f.id.startsWith("main:")) {
      const area = areaName(f);
      if (area && area !== lastArea) {
        list.append(el("li", {class: "section-label", text: area}));
        lastArea = area;
      }
    }
    const row = el("li", {class: "question"});
    const margin = el("div", {class: "margin-note"});
    if (f.source_ref) {
      margin.append(el("b", {text: paragraphLabel(f.source_ref)}));
      margin.append(el("span", {text: t("question.guidelines")}));
    }
    const content = el("div");
    content.append(el("p", {class: "question-text", text: text(f.text)}));
    const choice = el("div", {class: "choice", role: "group"});
    const options = [[true, "answer.yes"], [false, "answer.no"], [NOT_APPLICABLE, "answer.unknown"]];
    for (const [value, key] of options) {
      const pressed = answers[f.id] === value ? "true" : "false";
      const button = el("button", {type: "button", "aria-pressed": pressed, text: t(key)});
      button.onclick = () => {
        answers[f.id] = value;
        for (const other of choice.children) other.setAttribute("aria-pressed", "false");
        button.setAttribute("aria-pressed", "true");
        updateNextButton();
      };
      choice.append(button);
    }
    content.append(choice);
    const effectNote = text(f.effect_note);
    if (effectNote) content.append(el("p", {class: "effect-note", text: effectNote}));
    row.append(margin, content);
    list.append(row);
  }
  parts.push(list);

  const nextButton = el("button", {class: "button", id: "next", text: t("nav.next"), disabled: ""});
  nextButton.onclick = advance;
  const backButton = el("button", {class: "button outline", text: t("nav.back")});
  backButton.onclick = goBack;
  const pending = el("span", {class: "open", id: "open"});
  parts.push(el("div", {class: "actions"}, [nextButton, backButton, pending]));

  stage.replaceChildren(...parts);
  if (scroll) window.scrollTo({top: 0, behavior: "instant"});
  updateNextButton();

  function updateNextButton() {
    const missing = group.filter((f) => answers[f.id] === undefined).length;
    const next = document.getElementById("next");
    const open = document.getElementById("open");
    if (missing) {
      next.setAttribute("disabled", "");
      open.textContent = countText(missing, "open.one", "open.many");
    } else {
      next.removeAttribute("disabled");
      open.textContent = "";
    }
  }
}

function readableCitation(citation) {
  const annexIII = /^AI-Act\/annex-III\/pt-(\d+)(?:-([a-h]))?$/.exec(citation);
  if (annexIII) {
    const [, point, letter] = annexIII;
    return letter ? t("citation.annexIIILetter", {point, letter}) : t("citation.annexIII", {point});
  }
  if (citation === "AI-Act/annex-I") return t("citation.annexI");
  return citation;
}

function closingText(finding) {
  return finding.closing_text || t(`finding.${finding.risk_class}.sentence`);
}

function drawFinding({scroll = true} = {}) {
  const e = flow.result(answers, language);
  const riskClass = e.risk_class in RISK_CLASS_TONES ? e.risk_class : "not_high_risk";
  setProgressSteps(5);
  setProgress(t("progress.finding"), countText(screens.length, "progress.stepsOne", "progress.stepsMany"), 100);

  const parts = [el("div", {class: "finding " + RISK_CLASS_TONES[riskClass]}, [
    el("p", {class: "kicker", text: t("finding.kicker")}),
    el("p", {class: "verdict", text: t(`finding.${riskClass}.word`)}),
    el("p", {text: closingText({...e, risk_class: riskClass})}),
  ])];

  if (e.matched_provisions.length) {
    const dl = el("dl");
    for (const p of e.matched_provisions) {
      dl.append(el("dt", {text: text(p.title) || p.area}));
      dl.append(el("dd", {class: "location", text: readableCitation(p.citation)}));
      dl.append(el("dd", {class: "muted", text: text(p.main_question.text)}));
    }
    parts.push(el("section", {class: "block"}, [el("h3", {text: t("finding.basisHeading")}), dl]));
  }
  if (e.filter_applies) {
    parts.push(el("section", {class: "block"}, [
      el("h3", {text: t("finding.exemptionHeading")}), el("p", {text: e.filter_reason})]));
  }
  if (RISK_CLASS_TONES[riskClass] === "minimal") {
    parts.push(el("section", {class: "block"}, [
      el("h3", {text: t("finding.nowHeading")}),
      el("p", {text: t("finding.nowText")}),
      el("p", {class: "muted", text: t("finding.nowChange")}),
    ]));
  }
  if (e.evidence.length) {
    parts.push(el("p", {class: "source-ref",
      text: t("finding.evidence", {refs: e.evidence.map(paragraphNumber).join(", ")})}));
  }

  for (const p of e.matched_provisions) {
    if (!p.examples.length) continue;
    const details = el("details");
    details.append(el("summary",
      {text: countText(p.examples.length, "finding.examplesOne", "finding.examplesMany")}));
    for (const b of p.examples) {
      const isHighRisk = b.verdict === "high_risk";
      const rationale = text(b.rationale);
      details.append(el("div", {class: "example"}, [
        el("p", {class: "assessment " + (isHighRisk ? "yes" : "no"),
          text: t(isHighRisk ? "example.covered" : "example.notCovered")}),
        el("p", {text: text(b.scenario)}),
        rationale ? el("p", {class: "muted", text: rationale}) : null,
        b.source_ref ? el("p", {class: "source-ref", text: paragraphLabel(b.source_ref)}) : null,
      ]));
    }
    parts.push(details);
  }

  const restartButton = el("button", {class: "button outline", text: t("nav.restart")});
  restartButton.onclick = restart;
  parts.push(el("div", {class: "actions"}, [restartButton]));

  stage.replaceChildren(...parts);
  if (scroll) window.scrollTo({top: 0, behavior: "instant"});
}

function drawLoadError() {
  stage.replaceChildren(
    el("h2", {text: t("error.heading")}),
    el("p", {text: t("error.text")}));
}

function draw(options) {
  if (view === "start") drawStart(options);
  else if (view === "questions") drawQuestions(options);
  else if (view === "finding") drawFinding(options);
  else if (view === "error") drawLoadError(options);
}

function begin() {
  answers = {};
  screens = [];
  advance();
}

function advance() {
  const group = flow.nextGroup(answers);
  if (!group.length) {
    view = "finding";
  } else {
    screens.push(group);
    view = "questions";
  }
  draw();
}

function goBack() {
  for (const question of screens.pop() || []) delete answers[question.id];
  view = screens.length ? "questions" : "start";
  draw();
}

function restart() {
  answers = {};
  screens = [];
  view = "start";
  draw();
}

function applyLanguage() {
  translateStaticText();
  updateDocumentLinks();
  updateStructuredData();
  updateVersion();
}

async function switchLanguage(code) {
  try {
    await loadCatalog(code);
  } catch {
    return;
  }
  language = code;
  storeLanguage(code);
  const url = new URL(window.location.href);
  url.searchParams.set(LANGUAGE_PARAMETER, code);
  window.history.replaceState(null, "", url);
  applyLanguage();
  draw({scroll: false});
}

for (const link of document.querySelectorAll(".language-switch a[data-language]")) {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    switchLanguage(link.dataset.language);
  });
}

async function loadInitialCatalog() {
  const wanted = initialLanguage();
  try {
    await loadCatalog(wanted);
    return wanted;
  } catch {
    await loadCatalog(DEFAULT_LANGUAGE);
    return DEFAULT_LANGUAGE;
  }
}

async function main() {
  const [chosen, data] = await Promise.all([
    loadInitialCatalog(),
    fetch("./question_flow.json").then((r) => r.json()).catch(() => null),
  ]);
  language = chosen;
  if (data) {
    flow = new Walkthrough(data);
    view = "start";
  } else {
    view = "error";
  }
  applyLanguage();
  draw({scroll: false});
}

main();
