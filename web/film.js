/* Presentation tab: eight scenes that play by themselves like a short promotional film.
 *
 * Context: the scenes are HTML with CSS animations, so they stay sharp, translatable and light;
 * this module only keeps time | Input: the scenes and chapter buttons in #film, the "tab:shown"
 * event, page visibility, prefers-reduced-motion | Output: the current scene, chapter progress,
 * play and pause; it starts on its own when the tab opens, except under reduced motion.
 */
import {onLanguage} from "./language.js";

const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)");
const STAR_COUNT = 12;
const TILE_COUNT = 180;

const film = document.getElementById("film");
const stage = film ? film.querySelector(".film-stage") : null;
const scenes = film ? [...film.querySelectorAll(".scene")] : [];
const chapters = film ? [...film.querySelectorAll(".film-chapters button")] : [];
const playButton = film ? film.querySelector(".film-play") : null;
let t = (key) => key;
let current = 0;
let elapsed = 0;
let playing = false;
let lastFrame = 0;
let tabVisible = false;

function star(cx, cy) {
  const points = Array.from({length: 10}, (_, index) => {
    const radius = index % 2 ? 4.2 : 10;
    const angle = (Math.PI / 5) * index - Math.PI / 2;
    return `${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`;
  });
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", `M${points.join("L")}Z`);
  return path;
}

function buildVisuals(mismatches) {
  const ring = document.getElementById("film-stars");
  ring.replaceChildren(...Array.from({length: STAR_COUNT}, (_, index) => {
    const angle = (2 * Math.PI * index) / STAR_COUNT;
    return star(78 * Math.cos(angle), 78 * Math.sin(angle));
  }));
  document.getElementById("film-tiles").replaceChildren(...Array.from({length: TILE_COUNT}, (_, index) => {
    const tile = document.createElement("i");
    tile.style.setProperty("--n", String((index * 7) % TILE_COUNT));
    return tile;
  }));
  document.getElementById("film-waffle").replaceChildren(...mismatches.map((missed, index) => {
    const cell = document.createElement("i");
    cell.style.setProperty("--n", String(index));
    if (missed) cell.className = "off";
    return cell;
  }));
}

function duration(index) {
  return Number(scenes[index].dataset.duration) || 6000;
}

function restartAnimations(scene) {
  scene.classList.remove("is-current");
  void scene.offsetWidth;
  scene.classList.add("is-current");
}

function showScene(index) {
  current = index;
  elapsed = 0;
  scenes.forEach((scene, position) => {
    if (position === index) restartAnimations(scene);
    else scene.classList.remove("is-current");
  });
  chapters.forEach((chapter, position) => {
    if (position === index) chapter.setAttribute("aria-current", "step");
    else chapter.removeAttribute("aria-current");
  });
  updateMeters();
}

function updateMeters() {
  chapters.forEach((chapter, position) => {
    const done = position < current ? 100 : position > current ? 0 : (elapsed / duration(current)) * 100;
    chapter.querySelector(".meter i").style.setProperty("--done", `${Math.min(100, done)}%`);
  });
}

function setPlaying(value) {
  playing = value;
  stage.classList.toggle("paused", !value);
  playButton.setAttribute("aria-pressed", String(value));
  playButton.setAttribute("aria-label", t(value ? "film.pause" : "film.play"));
  lastFrame = performance.now();
  if (value) requestAnimationFrame(tick);
}

function tick(now) {
  if (!playing) return;
  elapsed += now - lastFrame;
  lastFrame = now;
  if (elapsed >= duration(current)) {
    if (current === scenes.length - 1) {
      elapsed = duration(current);
      updateMeters();
      setPlaying(false);
      return;
    }
    showScene(current + 1);
  }
  updateMeters();
  requestAnimationFrame(tick);
}

function togglePlay() {
  if (!playing && current === scenes.length - 1 && elapsed >= duration(current)) showScene(0);
  setPlaying(!playing);
}

function onTab(event) {
  tabVisible = event.detail.id === "praesentation";
  if (!tabVisible) {
    setPlaying(false);
    return;
  }
  showScene(current);
  if (!REDUCED_MOTION.matches) setPlaying(true);
}

if (film) {
  fetch("./benchmarks.json")
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error(String(response.status)))))
    .then((data) => buildVisuals(data.examples.map((cell) => !cell.matched)))
    .catch(() => buildVisuals([]));
  chapters.forEach((chapter, index) => chapter.addEventListener("click", () => {
    showScene(index);
    if (!playing && !REDUCED_MOTION.matches) setPlaying(true);
  }));
  playButton.addEventListener("click", togglePlay);
  onLanguage(({t: translate}) => {
    t = translate;
    playButton.setAttribute("aria-label", t(playing ? "film.pause" : "film.play"));
  });
  document.addEventListener("tab:shown", onTab);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) setPlaying(false);
  });
  showScene(0);
  setPlaying(false);
  const openTab = document.documentElement.dataset.tab;
  if (openTab) onTab({detail: {id: openTab}});
}
