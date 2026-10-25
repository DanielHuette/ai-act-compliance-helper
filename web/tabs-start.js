/* Picks the tab from the address before the first paint.
 *
 * Context: loaded synchronously in <head>, so a deep link such as #benchmarks never flashes the
 * project tab first; tabs.js takes over once the page is parsed | Input: location.hash |
 * Output: data-tab on <html>, which the stylesheet uses to hide the other panels.
 */
(function () {
  var tabs = ["projekt", "organigramm", "benchmarks", "praesentation"];
  var wanted = window.location.hash.slice(1);
  document.documentElement.dataset.tab = tabs.indexOf(wanted) >= 0 ? wanted : "projekt";
})();
