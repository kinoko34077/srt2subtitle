import test from "node:test";
import assert from "node:assert/strict";

import { buildExo, parseExoTemplate } from "../node_modules/.cache/exo-test/exo.js";

function makeSpeaker() {
  return {
    speaker_id: "spk_001",
    display_name: "test",
    base_layer: 1,
    subtitle_rule: {
      max_chars_per_line: 24,
      max_lines: 2,
      min_duration_sec: 0.5,
      max_duration_sec: 8,
    },
    template_exo: "template.exo",
    template_meta: {
      speaker_id: "spk_001",
      template_source: "template.exo",
      object_sections: [
        {
          name: "[0]",
          items: [
            ["start", "1"],
            ["end", "30"],
            ["layer", "1"],
          ],
        },
        {
          name: "[0.0]",
          items: [
            ["_name", "テキスト"],
            ["text", "0000"],
            ["font", "Meiryo"],
          ],
        },
      ],
      text_section_key: "[0.0]",
      placeholder_text: "",
      text_encoding: "utf16le_hex",
      file_encoding: "utf-8",
      base_settings: {
        width: "1920",
        height: "1080",
        rate: "30",
        scale: "1",
        length: "30",
        audio_rate: "48000",
        audio_ch: "2",
      },
      preview: {
        font: "Meiryo",
        size: "",
        color: "",
        color2: "",
        layer: "1",
      },
    },
  };
}

function render(text) {
  const speaker = makeSpeaker();
  const exo = buildExo(
    {
      name: "unicode regression",
      fps: 30,
      width: 1920,
      height: 1080,
      output_name: "output.exo",
    },
    [speaker],
    [
      {
        speaker_id: "spk_001",
        start_sec: 0,
        end_sec: 1,
        text,
        warnings: [],
        base_layer: 1,
        start_frame: 1,
        end_frame: 30,
      },
    ],
  );
  return { exo, speaker };
}

for (const text of ["字幕テスト", "字幕😀テスト"]) {
  test(`EXO UTF-16LE text round-trips exactly: ${text}`, () => {
    const { exo } = render(text);
    const textHex = /^text=([0-9a-f]+)$/mu.exec(exo)?.[1];
    assert.ok(textHex, "generated EXO must contain a hex text field");

    const expected = Buffer.from(text, "utf16le").toString("hex") + "0000";
    assert.equal(textHex, expected);

    const parsed = parseExoTemplate(exo, "spk_001", "generated.exo");
    assert.equal(parsed.placeholder_text, text);
    assert.equal(parsed.text_encoding, "utf16le_hex");
  });
}
