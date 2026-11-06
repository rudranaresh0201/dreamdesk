// Tiny shared helper for the DreamDesk web apps: one state object S, a render() that returns HTML, and R() to redraw.
// Every page reload starts from the initial state (nothing is stored), so each episode starts fresh.
let S = {}, VIEW = () => "";
function app(init, view) { S = init; VIEW = view; R(); }
function R() { document.getElementById("app").innerHTML = VIEW(); }
function set(k, v) { S[k] = v; R(); }
function tog(k) { S[k] = !S[k]; R(); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c])); }
function tabs(key, names) {
  return `<nav role="tablist">${names.map(n => `<button role="tab" aria-selected="${S[key] === n}" onclick="set('${key}','${n}')">${n}</button>`).join("")}</nav>`;
}
function dialog(title, body, close = "S.dlg=null;R()") {
  return `<div role="dialog" aria-modal="true" aria-label="${title}"><h2>${title}</h2>${body}<button onclick="${close}">Close</button></div>`;
}
function menu(key, label, items) {
  return `<button aria-haspopup="menu" aria-expanded="${!!S[key]}" onclick="tog('${key}')">${label}</button>` +
    (S[key] ? `<div role="menu">${items.map(([n, js]) => `<button role="menuitem" onclick="S['${key}']=false;${js};R()">${n}</button>`).join("")}</div>` : "");
}
function field(label, key, type = "text") {
  return `<label>${label} <input type="${type}" aria-label="${label}" value="${esc(S[key] ?? "")}" oninput="S['${key}']=this.value"></label>`;
}
function check(label, key) {
  return `<label><input type="checkbox" ${S[key] ? "checked" : ""} onchange="S['${key}']=this.checked;R()"> ${label}</label>`;
}
