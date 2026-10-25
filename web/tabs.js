/* Tab bar at the bottom of the page: project, organisation chart, measurements, presentation.
 *
 * Context: every tab is a deep link (#projekt, #organigramm, #benchmarks, #praesentation), so a
 * CV link opens a tab directly and the browser's back and forward buttons move between tabs |
 * Input: the address hash, clicks and arrow keys on the tab bar | Output: one visible panel, the
 * tab state for assistive technology and a "tab:shown" event the tab modules listen to.
 */

const DEFAULT_TAB = "projekt";
const tabs = [...document.querySelectorAll('.dock [role="tab"]')];
const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));

function panelFor(hash) {
  const target = hash ? document.getElementById(decodeURIComponent(hash.slice(1))) : null;
  const panel = target ? target.closest('[role="tabpanel"]') : null;
  return panels.includes(panel) ? panel : document.getElementById(DEFAULT_TAB);
}

function show(panel, {focusTab = false} = {}) {
  document.documentElement.dataset.tab = panel.id;
  tabs.forEach((tab, index) => {
    const selected = panels[index] === panel;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    panels[index].hidden = !selected;
    if (selected && focusTab) tab.focus();
  });
  document.dispatchEvent(new CustomEvent("tab:shown", {detail: {id: panel.id}}));
}

function followAddress() {
  const panel = panelFor(window.location.hash);
  const changed = document.documentElement.dataset.tab !== panel.id || panel.hidden;
  show(panel);
  const isPanelLink = window.location.hash.slice(1) === panel.id;
  if (changed && isPanelLink) window.scrollTo({top: 0, behavior: "instant"});
}

function onTabKey(event) {
  if (event.key === " ") {
    event.preventDefault();
    event.currentTarget.click();
    event.currentTarget.focus();
    return;
  }
  const index = tabs.indexOf(event.currentTarget);
  const last = tabs.length - 1;
  const next = {ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: last}[event.key];
  if (next === undefined) return;
  event.preventDefault();
  const tab = tabs[(next + tabs.length) % tabs.length];
  tab.click();
  tab.focus();
}

for (const tab of tabs) tab.addEventListener("keydown", onTabKey);
window.addEventListener("hashchange", followAddress);
followAddress();
