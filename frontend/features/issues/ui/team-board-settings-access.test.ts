import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

const issuesPageSource = readFileSync(
  path.join(import.meta.dirname, "issues-pages.tsx"),
  "utf8",
);

test("team issues page keeps a reachable board settings entry point", () => {
  assert.match(
    issuesPageSource,
    /onClick=\{\(\) => setBoardSettingsId\(board\.board_id\)\}/,
  );
});
