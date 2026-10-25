/* Measurement tab: draws the recounted figures from benchmarks.json.
 *
 * Context: every number on this tab comes from the run logs through scripts/export_benchmarks.py,
 * so the page cannot drift from the measurement | Input: benchmarks.json, the language channel
 * | Output: one cell per official example, bars per Commission verdict, the step histogram,
 * the corpus split and a hover tooltip; text follows the chosen language.
 */
import {onLanguage} from "./language.js";

const VERDICT_KEYS = {
  high_risk: "bench.verdict.highRisk",
  not_high_risk: "bench.verdict.notHighRisk",
  exemption_applies: "bench.verdict.exemption",
};
const GROUPS = ["matched", "no_area", "missing_feature"];

const tip = document.getElementById("chart-tip");
let data = null;
let loadFailed = false;
let t = (key) => key;
let numberFormat = new Intl.NumberFormat("de-DE");

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (name === "text") node.textContent = value;
    else node.setAttribute(name, value);
  }
  node.append(...[].concat(children).filter(Boolean));
  return node;
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function groupOf(cell) {
  return cell.group || "matched";
}

function showTip(event, text) {
  tip.textContent = text;
  tip.hidden = false;
  const x = Math.min(event.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  const y = Math.max(8, event.clientY - tip.offsetHeight - 12);
  tip.style.left = `${x}px`;
  tip.style.top = `${y}px`;
}

function hideTip() {
  tip.hidden = true;
}

function cellText(cell) {
  return t("bench.cell", {
    number: cell.index + 1,
    verdict: t(VERDICT_KEYS[cell.expected]),
    result: t(`bench.group.${groupOf(cell)}`),
  });
}

function drawWaffle() {
  const waffle = document.getElementById("bench-waffle");
  waffle.replaceChildren(...data.examples.map((cell) => {
    const square = el("i", {class: groupOf(cell)});
    square.addEventListener("pointerenter", (event) => showTip(event, cellText(cell)));
    square.addEventListener("pointermove", (event) => showTip(event, cellText(cell)));
    square.addEventListener("pointerleave", hideTip);
    return square;
  }));
  const counts = Object.fromEntries(GROUPS.map((group) => [group, 0]));
  for (const cell of data.examples) counts[groupOf(cell)] += 1;
  document.getElementById("bench-legend").replaceChildren(...GROUPS.map((group) =>
    el("li", {}, [el("i", {class: group}), el("span", {text: t(`bench.group.${group}`)}),
      el("b", {text: numberFormat.format(counts[group])})])));
  setText("bench-headline", t("bench.headline.figure", {matched: data.matched, total: data.total}));
  setText("bench-waffle-takeaway", t("bench.waffle.takeaway", {
    noArea: counts.no_area, mismatches: data.total - data.matched,
    matched: data.matched, without: data.total - counts.no_area}));
  document.getElementById("bench-mismatches").replaceChildren(...data.examples
    .filter((cell) => cell.group).map((cell) => el("li", {text: cellText(cell)})));
}

function drawVerdicts() {
  const largest = Math.max(...data.verdicts.map((bar) => bar.total));
  document.getElementById("bench-verdicts").replaceChildren(...data.verdicts.map((bar) => {
    const share = (bar.matched / largest) * 100;
    const rest = ((bar.total - bar.matched) / largest) * 100;
    const missed = data.examples.find((cell) => cell.expected === bar.verdict && cell.group);
    const track = el("span", {class: "track"}, [
      el("span", {class: "fill"}),
      missed ? el("span", {class: `rest ${missed.group}`}) : null,
    ]);
    track.children[0].style.width = `${share}%`;
    if (track.children[1]) track.children[1].style.width = `${rest}%`;
    return el("li", {}, [
      el("span", {class: "bar-label"}, [el("span", {text: t(VERDICT_KEYS[bar.verdict])}),
        el("b", {text: t("bench.ofTotal", {part: bar.matched, total: bar.total})})]),
      track,
    ]);
  }));
  const cautious = data.verdicts.find((bar) => bar.verdict === "not_high_risk");
  const noArea = data.examples.filter((cell) => cell.group === "no_area").length;
  setText("bench-verdicts-takeaway", [
    cautious && cautious.matched === cautious.total ? t("bench.verdicts.noneTooStrict") : "",
    t("bench.verdicts.exemptionShare", {noArea, mismatches: data.total - data.matched}),
  ].filter(Boolean).join(" "));
}

function fullSteps() {
  const counts = new Map(data.steps.map((bin) => [bin.steps, bin.count]));
  const last = Math.max(...counts.keys());
  return Array.from({length: last}, (_, index) => ({steps: index + 1, count: counts.get(index + 1) || 0}));
}

function drawSteps() {
  const bins = fullSteps();
  const highest = Math.max(...bins.map((bin) => bin.count));
  const plot = el("div", {class: "histogram-plot", role: "img",
    "aria-label": t("bench.steps.label", {average: numberFormat.format(data.average_steps)})});
  for (const bin of bins) {
    const column = el("span", {class: "column"}, [el("span", {text: String(bin.count)})]);
    column.style.setProperty("--h", `${(bin.count / highest) * 88}%`);
    column.addEventListener("pointermove", (event) =>
      showTip(event, t("bench.steps.tip", {count: bin.count, steps: bin.steps})));
    column.addEventListener("pointerleave", hideTip);
    plot.append(column);
  }
  const average = el("span", {class: "average"},
    [el("span", {text: t("bench.steps.average", {average: numberFormat.format(data.average_steps)})})]);
  average.style.setProperty("--x", `${((data.average_steps - 0.5) / bins.length) * 100}%`);
  plot.append(average);
  document.getElementById("bench-steps").replaceChildren(
    el("span", {class: "histogram-y", text: t("bench.steps.yAxis")}), plot,
    el("span", {class: "histogram-axis"}, bins.map((bin) => el("span", {text: String(bin.steps)}))),
    el("span", {class: "histogram-x", text: t("bench.steps.xAxis")}));
  setText("bench-steps-takeaway", t("bench.steps.takeaway", {
    average: numberFormat.format(data.average_steps), most: bins.length}));
}

function drawCorpus() {
  const total = data.corpus.reduce((sum, part) => sum + part.units, 0);
  setText("bench-corpus-total", numberFormat.format(total));
  document.getElementById("bench-corpus").replaceChildren(...data.corpus.map((part) => {
    const segment = el("i", {class: `part-${part.part}`});
    segment.style.width = `${(part.units / total) * 100}%`;
    segment.addEventListener("pointermove", (event) => showTip(event,
      `${t(`bench.corpus.${part.part}`)}: ${numberFormat.format(part.units)}`));
    segment.addEventListener("pointerleave", hideTip);
    return segment;
  }));
  document.getElementById("bench-corpus-legend").replaceChildren(...data.corpus.map((part) =>
    el("li", {}, [el("i", {class: `part-${part.part}`}), el("span", {text: t(`bench.corpus.${part.part}`)}),
      el("b", {text: numberFormat.format(part.units)})])));
}

function draw() {
  if (loadFailed) setText("bench-headline", t("bench.error"));
  if (!data) return;
  setText("bench-parity", t("bench.ofTotal", {part: data.parity_runs, total: data.parity_runs}));
  drawWaffle();
  drawVerdicts();
  drawSteps();
  drawCorpus();
}

if (tip) {
  onLanguage(({language, t: translate}) => {
    t = translate;
    numberFormat = new Intl.NumberFormat(language === "en" ? "en-GB" : "de-DE");
    draw();
  });
  fetch("./benchmarks.json")
    .then((response) => {
      if (!response.ok) throw new Error(`benchmarks.json: HTTP ${response.status}`);
      return response.json();
    })
    .then((content) => {
      data = content;
      draw();
    })
    .catch(() => {
      loadFailed = true;
      draw();
    });
  window.addEventListener("scroll", hideTip, {passive: true});
}
