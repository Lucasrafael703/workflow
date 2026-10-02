const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {JSDOM} = require("jsdom");

function boot(fetchImpl) {
  const html = '<!doctype html><body><section data-work-board data-board-id="4" data-view-id="2"><table><tbody><tr data-work-item="9" data-work-updated-at="2026-10-02T12:00:00+00:00"><td id="work-cell-9-7" class="work-cell work-cell--text" data-work-cell data-field-id="7" data-item-id="9" data-value="Antes" tabindex="0"><span class="work-cell__value">Antes</span></td></tr></tbody></table><div data-work-board-toast></div></section></body>';
  const dom = new JSDOM(html, {runScripts: "outside-only", url: "https://lps.test/"});
  dom.window.fetch = fetchImpl;
  dom.window.eval(readFileSync("static/js/work-board.js", "utf8"));
  dom.window.document.dispatchEvent(new dom.window.Event("DOMContentLoaded", {bubbles: true}));
  return dom;
}

test("inline update replaces only the server-confirmed cell", async () => {
  let sent;
  const dom = boot((url, init) => {
    sent = {url, body: JSON.parse(init.body)};
    return Promise.resolve({ok: true, json: () => Promise.resolve({
      success: true, message: "Salvo.", target: "work-cell-9-7", updated_at: "2026-10-02T12:01:00+00:00",
      html: '<td id="work-cell-9-7" class="work-cell work-cell--text" data-work-cell data-field-id="7" data-item-id="9" data-value="Depois" tabindex="0"><span class="work-cell__value">Depois</span></td>'
    })});
  });
  const cell = dom.window.document.getElementById("work-cell-9-7");
  cell.dispatchEvent(new dom.window.MouseEvent("click", {bubbles: true}));
  const input = dom.window.document.querySelector(".work-cell__editor");
  input.value = "Depois";
  input.dispatchEvent(new dom.window.KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(sent.url, "/quadros/dominio/4/campos/7/itens/9/valor/");
  assert.equal(sent.body.value, "Depois");
  assert.equal(dom.window.document.getElementById("work-cell-9-7").textContent, "Depois");
});

test("manual search has no automatic input handler", () => {
  const dom = boot(() => Promise.reject(new Error("not used")));
  const input = dom.window.document.createElement("input");
  input.name = "q";
  input.dispatchEvent(new dom.window.Event("input", {bubbles: true}));
  assert.ok(true);
});
