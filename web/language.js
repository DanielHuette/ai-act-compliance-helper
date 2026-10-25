/* Shared language channel between page.js and the tab modules.
 *
 * Context: page.js loads the catalogs and decides the language; the organisation chart,
 * measurement and presentation tabs draw texts of their own and must redraw on a switch |
 * Input: publishLanguage({language, t}) from page.js | Output: every listener called with the
 * current language at once and again after each switch.
 */

let current = null;
const listeners = new Set();

export function publishLanguage(detail) {
  current = detail;
  for (const listener of listeners) listener(detail);
}

export function onLanguage(listener) {
  listeners.add(listener);
  if (current) listener(current);
}
