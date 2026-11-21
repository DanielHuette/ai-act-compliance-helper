const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const panel = document.getElementById("projekt");
const root = document.documentElement;

const headings = [...panel.querySelectorAll(".image-block h2, .reading h2")];
const sections = [...panel.querySelectorAll(".app, .reading section")];

const moves = [];
function addMove(element, kind, delay = 0) {
  if (element) moves.push({ element, kind, delay });
}

addMove(panel.querySelector(".image-block .framed-image"), "left");
addMove(panel.querySelector(".image-block > div"), "right");
addMove(panel.querySelector("#knowledge"), "tilt");
addMove(panel.querySelector("#risk"), "zoom");
addMove(panel.querySelector("#areas > h2"), "tilt");
addMove(panel.querySelector("#areas > p"), "tilt");
panel.querySelectorAll(".area-list li").forEach((card, index) => {
  const column = index % 4;
  addMove(card, column < 2 ? "left" : "right", (column === 0 || column === 3 ? 0.12 : 0) + Math.floor(index / 4) * 0.1);
});
addMove(panel.querySelector("#sources > h2"), "tilt");
panel.querySelectorAll("#sources > p").forEach((text) => addMove(text, "tilt"));
panel.querySelectorAll(".source-list li").forEach((card, index) => {
  addMove(card, ["left", "zoom", "right"][index % 3]);
});
addMove(panel.querySelector("#software"), "zoom");

function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}

function pageTop(element) {
  let top = 0;
  for (let node = element; node; node = node.offsetParent) top += node.offsetTop;
  return top;
}

function fillLevel(element, viewHeight) {
  const box = element.getBoundingClientRect();
  const entering = clamp((viewHeight * 0.92 - box.top) / (viewHeight * 0.42), 0, 1);
  const leaving = clamp((box.bottom - 100) / (viewHeight * 0.2), 0, 1);
  return Math.min(entering, leaving);
}

function transformFor(kind, rest) {
  if (rest < 0.001) return "none";
  if (kind === "tilt") return `perspective(1400px) rotateX(${(rest * 22).toFixed(2)}deg) translateY(${(rest * 80).toFixed(1)}px)`;
  if (kind === "left") return `perspective(1400px) translateX(${(-rest * innerWidth * 0.7).toFixed(1)}px) rotateY(${(rest * 38).toFixed(2)}deg)`;
  if (kind === "right") return `perspective(1400px) translateX(${(rest * innerWidth * 0.7).toFixed(1)}px) rotateY(${(-rest * 38).toFixed(2)}deg)`;
  return `scale(${(1 - rest * 0.2).toFixed(3)})`;
}

function update() {
  if (panel.hidden) return;
  const viewHeight = innerHeight;
  for (const heading of headings) {
    heading.style.setProperty("--fill", (fillLevel(heading, viewHeight) * 104).toFixed(1) + "%");
  }
  const still = innerWidth <= 980;
  for (const { element, kind, delay } of moves) {
    if (still) {
      element.style.transform = "";
      element.style.opacity = "";
      continue;
    }
    const top = pageTop(element) - scrollY;
    const progress = clamp((viewHeight * 1.08 - top) / (viewHeight * 0.8) - delay, 0, 1);
    const rest = Math.pow(1 - progress, 1.5);
    element.style.transform = transformFor(kind, rest);
    element.style.opacity = (1 - rest * 0.85).toFixed(3);
  }
}

function addDividers() {
  const seen = new IntersectionObserver((entries) => {
    for (const entry of entries) entry.target.classList.toggle("is-drawn", entry.isIntersecting);
  }, { rootMargin: "0px 0px -12% 0px" });
  for (const section of sections) {
    const divider = document.createElement("div");
    divider.className = "divider";
    divider.setAttribute("aria-hidden", "true");
    divider.innerHTML = "<i></i><b>+</b>";
    section.prepend(divider);
    seen.observe(divider);
  }
}

if (!reducedMotion) {
  root.classList.add("has-effects");
  for (const heading of headings) heading.classList.add("fill");
  addDividers();
  let waiting = false;
  const schedule = () => {
    if (waiting) return;
    waiting = true;
    requestAnimationFrame(() => {
      waiting = false;
      update();
    });
  };
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule);
  addEventListener("hashchange", schedule);
  new MutationObserver(schedule).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
  new ResizeObserver(schedule).observe(panel);
  update();
}