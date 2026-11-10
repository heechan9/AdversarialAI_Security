/* eslint-disable @typescript-eslint/no-require-imports -- Existing Node CJS SSR harness pattern. */
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), ts = require("typescript"), Module = require("node:module");
const root = path.resolve(__dirname, ".."), resolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, ...rest) { return resolve.call(this, request.startsWith("@/") ? path.join(root, request.slice(2)) : request, parent, ...rest); };
for (const ext of [".ts", ".tsx"]) require.extensions[ext] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022 } }).outputText, file);
const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
const data = require("../public/evidence/fixed-array-cross-score.json");
assert.equal(data.schema_version, 1);
assert.equal(data.selected_unique_images, 4);
assert.equal(data.selected_conditions_per_cell, data.conditions.length);
assert.equal(data.completed_cells, data.total_cells);
assert.equal(data.total_cells, data.scoring_environments.length * data.attack_array_origins.length);
assert.equal(new Set(data.cells.map(c => c.scorer + ":" + c.attack_origin)).size, data.total_cells);
assert.deepEqual(data.cells.map(c => c.scorer + ":" + c.attack_origin).sort(), data.scoring_environments.flatMap(s => data.attack_array_origins.map(o => s + ":" + o)).sort());
assert.ok(data.cells.every(c => c.status === "COMPLETE" && c.selected_outputs === data.conditions.length));
assert.equal(data.cells.reduce((n, c) => n + c.selected_outputs, 0), data.selected_outputs_across_matrix);
assert.equal(data.cells.filter(c => c.scorer === "windows_native_default").length, data.windows_new_processes);
assert.equal(data.cells.filter(c => c.scorer === "windows_native_default").reduce((n, c) => n + c.selected_outputs, 0), data.windows_new_selected_outputs);
let same = 0, matched = 0, origin = 0, different = 0;
for (const c of data.conditions) {
    for (const labels of [c.pc_origin_labels, c.linux_origin_labels]) { same++; matched += Number(labels.windows === labels.linux); }
    for (const environment of ["windows", "linux"]) { origin++; different += Number(c.pc_origin_labels[environment] !== c.linux_origin_labels[environment]); }
}
assert.equal(same, data.same_array_cross_environment.compared_label_pairs);
assert.equal(matched, data.same_array_cross_environment.matching_label_pairs);
assert.equal(origin, data.different_array_origin_within_environment.compared_label_pairs);
assert.equal(different, data.different_array_origin_within_environment.differing_label_pairs);
assert.equal(matched, 10); assert.equal(different, 10);
assert.equal(data.same_array_cross_environment.exact_probability_vector_pairs, 0);
assert.equal(data.same_array_cross_environment.max_abs_probability_component_delta, 2.9206275939941406e-6);
assert.deepEqual(data.verdicts, { external_stage_b: "FAIL", stage_b_approved: false, generation_cause: "UNRESOLVED", full_781_accuracy_recomputed: false, performance_improvement_claim: false });
assert.equal(data.execution.new_training, false); assert.equal(data.execution.new_attack_generation, false); assert.equal(data.execution.weights_changed, false);
const historical = require("../public/evidence/verification-status.json");
assert.equal(historical.cards.find(c => c.id === "external-01").status, "FAIL");
assert.equal(historical.cause_status, "UNRESOLVED");
const locale = require("../app/locale-provider.tsx"), originalLocale = locale.useLocale;
const Component = require("../app/fixed-array-cross-score.tsx").default;
const original = JSON.stringify(data);
try {
    for (const language of ["ko", "en"]) {
        locale.useLocale = () => ({ locale: language });
        const html = renderToStaticMarkup(React.createElement(Component));
        assert.ok(html.includes('id="cross-score"'));
        assert.ok(html.includes("10 / 10") && html.includes("4 / 4") && html.includes("2.92 × 10⁻⁶"));
        assert.equal((html.match(/5 \/ 5/g) || []).length, 4);
        assert.ok(html.includes("FAIL") && html.includes("UNRESOLVED"));
        assert.ok(html.includes(language === "en" ? "not 20 independent samples" : "독립 표본 20개가 아닙니다"));
        assert.ok(html.includes(language === "en" ? "no full 781-image accuracy improvement" : "전체 781장 정확도 향상"));
        assert.ok(!/NaN|undefined/.test(html));
        if (language === "en") assert.ok(!/[가-힣]/.test(html));
    }
} finally { locale.useLocale = originalLocale; }
assert.equal(JSON.stringify(data), original);
const page = fs.readFileSync(path.join(root, "app/page.tsx"), "utf8");
assert.ok(page.includes("<FixedArrayCrossScore />") && page.includes("<ResearchDiagnostics />"));
assert.ok(!/C:\\\\Users|relative_path|libfile_|return_without_inputs|\.npz/.test(JSON.stringify(data)));
console.log("PASS: fixed-array public counts and labels reconcile; KO/EN SSR retains sample limits, probability differences and external FAIL/UNRESOLVED. This checks the public summary, not private inference.");
