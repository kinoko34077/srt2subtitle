import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
const read = (path) => readFile(new URL(path, root), "utf8");

function section(source, start, end) {
  const startIndex = source.indexOf(start);
  assert.notEqual(startIndex, -1, `missing section start: ${start}`);
  const endIndex = source.indexOf(end, startIndex + start.length);
  assert.notEqual(endIndex, -1, `missing section end: ${end}`);
  return source.slice(startIndex, endIndex);
}

test("failed reruns preserve the last committed result and downloads", async () => {
  const source = await read("frontend/studio.js");
  const run = section(source, "async function runIntegratedExport()", "async function prepareSpeaker");

  assert.match(run, /const hadCommittedResult = hasCommittedResult\(\);/);
  assert.match(run, /commitIntegratedResult\(response\);/);
  assert.match(run, /前回の成功結果は保持しています/);
  assert.doesNotMatch(run, /state\.segments = \[\];[\s\S]*state\.output = \{ exoContentB64: "", srtContent: "", jsonContent: "" \};/);
  assert.match(source, /function hasCommittedResult\(\)/);
  assert.match(source, /function commitIntegratedResult\(response\)/);
});

test("integrated export captures one immutable run snapshot before controls are disabled or async work starts", async () => {
  const source = await read("frontend/studio.js");
  const run = section(source, "async function runIntegratedExport()", "async function prepareSpeaker");

  assert.match(run, /const runSnapshot = captureRunSnapshot\(\);/);
  assert.ok(
    run.indexOf("const runSnapshot = captureRunSnapshot();") < run.indexOf("setBusy(true);"),
    "run snapshot must be captured before disabling form controls so FormData keeps user-entered values",
  );
  assert.match(run, /for \(const \[index, speakerSnapshot\] of runSnapshot\.speakers\.entries\(\)\)/);
  assert.match(run, /prepareSpeaker\(speakerSnapshot, index \+ 1, runSnapshot\.transcriber\)/);
  assert.match(source, /function captureRunSnapshot\(\)/);
});

test("busy state locks run-affecting controls while leaving result downloads available", async () => {
  const [source, html] = await Promise.all([
    read("frontend/studio.js"),
    read("frontend/studio.html"),
  ]);

  const busy = section(source, "function setBusy(busy)", "function setDownloadDisabled");
  assert.match(busy, /querySelectorAll\("\[data-run-lock\]"\)/);
  assert.doesNotMatch(busy, /downloadExoButton|downloadSrtButton|downloadJsonButton/);
  assert.match(html, /data-run-lock/);
});

test("manual downloads keep the visible output name even while project controls are disabled", async () => {
  const source = await read("frontend/studio.js");
  const outputName = section(source, "function outputName(extension)", "function formatDateTime");

  assert.match(outputName, /querySelector\('\[name="output_name"\]'\)/);
  assert.doesNotMatch(outputName, /readProjectForm\(\)/);
});

test("persistent preset deletion requires explicit confirmation before request", async () => {
  const source = await read("frontend/studio.js");
  const deletion = section(source, "async function deletePresetRow", "function renderSegments");

  assert.match(deletion, /confirmDestructiveAction/);
  assert.ok(
    deletion.indexOf("confirmDestructiveAction") < deletion.indexOf('fetchJson("/api/v2/presets/delete"'),
    "confirmation must happen before the delete request",
  );
});

test("configured speaker removal is confirmed while empty cards remain one-click removable", async () => {
  const source = await read("frontend/studio.js");
  const addSpeaker = section(source, "function addSpeakerCard", "async function runIntegratedExport");

  assert.match(addSpeaker, /isConfiguredSpeakerCard\(card\)/);
  assert.match(addSpeaker, /confirmDestructiveAction/);
  assert.match(source, /function isConfiguredSpeakerCard\(card\)/);
});
