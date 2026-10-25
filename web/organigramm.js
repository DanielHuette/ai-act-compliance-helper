/* Organisation chart tab: draws the connections between the stations and lets light run along them.
 *
 * Context: the stations are plain HTML in a grid, so text stays readable and translatable; the
 * wires are drawn from the measured card positions, which keeps them right at every width |
 * Input: data-to on each station, the "tab:shown" event, the language channel | Output: SVG
 * wires with travelling signals (none under reduced motion) and, in the one-column layout, a
 * "passes on to" line for connections that cannot be drawn between neighbours.
 */
import {onLanguage} from "./language.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const ONE_COLUMN = window.matchMedia("(max-width: 1099px)");
const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)");
const SIGNAL_SPEED = 110;

const flow = document.getElementById("flow");
const wires = flow ? flow.querySelector(".flow-wires") : null;
const stations = flow ? [...flow.querySelectorAll(".station")] : [];
let translate = (key) => key;

function edges() {
  return stations.flatMap((source) =>
    (source.dataset.to || "").split(" ").filter(Boolean)
      .map((id) => ({source, target: document.getElementById(id)}))
      .filter((edge) => edge.target));
}

function box(element, origin) {
  const rect = element.getBoundingClientRect();
  return {left: rect.left - origin.left, right: rect.right - origin.left, top: rect.top - origin.top,
    bottom: rect.bottom - origin.top, centerX: rect.left - origin.left + rect.width / 2,
    centerY: rect.top - origin.top + rect.height / 2};
}

function gridPath(a, b) {
  if (b.left >= a.right - 1) {
    const startY = a.centerY;
    const endY = Math.min(Math.max(startY, b.top + 24), b.bottom - 24);
    const bend = (b.left - a.right) / 2;
    return `M${a.right} ${startY} C${a.right + bend} ${startY} ${b.left - bend} ${endY} ${b.left} ${endY}`;
  }
  const bend = (b.top - a.bottom) / 2;
  return `M${a.centerX} ${a.bottom} C${a.centerX} ${a.bottom + bend} ${b.centerX} ${b.top - bend} ${b.centerX} ${b.top}`;
}

function railPath(a, b) {
  const x = a.left - 12;
  return `M${a.left} ${a.bottom - 18} H${x} V${b.top + 18} H${b.left}`;
}

function isNeighbour(edge) {
  const next = stations[stations.indexOf(edge.source) + 1];
  return next === edge.target;
}

function drawnEdges() {
  return ONE_COLUMN.matches ? edges().filter(isNeighbour) : edges();
}

function signal(path, index) {
  const length = path.getTotalLength();
  const dot = document.createElementNS(SVG_NS, "circle");
  dot.setAttribute("r", "3.4");
  dot.setAttribute("class", "signal");
  const motion = document.createElementNS(SVG_NS, "animateMotion");
  motion.setAttribute("dur", `${Math.max(1.4, length / SIGNAL_SPEED).toFixed(2)}s`);
  motion.setAttribute("begin", `-${((index * 0.37) % 2.6).toFixed(2)}s`);
  motion.setAttribute("repeatCount", "indefinite");
  motion.setAttribute("path", path.getAttribute("d"));
  dot.append(motion);
  return dot;
}

function draw() {
  if (!wires || flow.offsetParent === null) return;
  const origin = flow.getBoundingClientRect();
  wires.setAttribute("viewBox", `0 0 ${origin.width} ${origin.height}`);
  const paths = drawnEdges().map((edge) => {
    const a = box(edge.source, origin);
    const b = box(edge.target, origin);
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", ONE_COLUMN.matches ? railPath(a, b) : gridPath(a, b));
    return path;
  });
  wires.replaceChildren(...paths);
  if (!REDUCED_MOTION.matches) paths.forEach((path, index) => wires.append(signal(path, index)));
}

function writeHandoffs() {
  const all = edges();
  for (const station of stations) {
    station.querySelector(".handoff")?.remove();
    const outgoing = all.filter((edge) => edge.source === station);
    const hidden = outgoing.filter((edge) => !isNeighbour(edge));
    if (!hidden.length) continue;
    const key = hidden.length < outgoing.length ? "org.handoffAlso" : "org.handoff";
    const line = document.createElement("p");
    line.className = "handoff";
    line.textContent = translate(key, {
      targets: hidden.map((edge) => edge.target.querySelector("h3").textContent).join(", "),
    });
    station.querySelector(".skills").before(line);
  }
}

function refresh() {
  writeHandoffs();
  draw();
}

if (flow) {
  onLanguage(({t}) => {
    translate = t;
    refresh();
  });
  document.addEventListener("tab:shown", (event) => {
    if (event.detail.id !== "organigramm") {
      wires.pauseAnimations();
      return;
    }
    wires.unpauseAnimations();
    requestAnimationFrame(draw);
  });
  new ResizeObserver(() => draw()).observe(flow);
  ONE_COLUMN.addEventListener("change", refresh);
  REDUCED_MOTION.addEventListener("change", draw);
  document.fonts?.ready.then(draw);
}
