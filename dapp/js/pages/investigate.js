/**
 * Copyright 2026 Operation Signal Forge contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { SAMPLE_CELL } from "../mock-data.js";
import { investigateAnomaly } from "../api.js";
import { renderAuthzReceipt } from "../authz-receipt.js";

export function renderInvestigate(root, params) {
  const cellId = params.cell_id || SAMPLE_CELL.cell_id;
  root.innerHTML = `
    <h1>Investigate anomaly</h1>
    <p class="sub">Runs <code>investigate_anomaly</code> (composes brief + recommend_next_sensor).</p>
    <div class="panel">
      <div class="row">
        <div>
          <label for="cell">cell_id</label>
          <input id="cell" value="${cellId}" />
        </div>
        <div>
          <label>&nbsp;</label>
          <button type="button" class="btn" id="btn-run">Run investigation</button>
        </div>
      </div>
      <p id="src" class="muted"></p>
      <div id="out"></div>
    </div>
  `;

  const out = root.querySelector("#out");
  const src = root.querySelector("#src");

  root.querySelector("#btn-run").addEventListener("click", async () => {
    const id = root.querySelector("#cell").value.trim();
    out.innerHTML = `<p class="muted">Running…</p>`;
    const res = await investigateAnomaly(id);
    src.textContent = `Source: ${res.source}`;

    if (!res.ok) {
      out.innerHTML = `
        <p class="err">${res.error || "Investigation failed"}</p>
        ${res.status === 403 ? `<p class="muted">Matrix denied this capability for the current role/scopes.</p>` : ""}
      `;
      return;
    }

    const inv = res.data?.data?.investigation || res.data?.investigation;
    const receipt = res.data?.authz_receipt;

    if (!inv) {
      out.innerHTML = `<p class="err">No investigation payload</p>`;
      return;
    }

    const next = inv.next_sensor;
    out.innerHTML = `
      <p class="ok">Status: ${inv.investigation_status} · advisory_only=${inv.advisory_only}</p>
      <h3>Overall assessment</h3>
      <p>${inv.overall_assessment}</p>
      <h3>Supporting capabilities</h3>
      <ul>${(inv.supporting_capabilities || [])
        .map((s) => `<li><code>${s.capability}</code> — ${s.status}</li>`)
        .join("")}</ul>
      <h3>recommend_next_sensor</h3>
      ${
        next
          ? `<p><strong>${next.recommended_sensor}</strong> · priority <span class="tag">${next.priority}</span></p>
             <p class="muted">${next.rationale || next.expected_investigative_value || ""}</p>`
          : `<p class="muted">No next_sensor in payload</p>`
      }
      <h3>Detection brief (composed)</h3>
      <p>${inv.detection_brief?.headline || "—"}</p>
      ${renderAuthzReceipt(receipt)}
      <h3>Full payload</h3>
      <pre class="pre">${JSON.stringify(inv, null, 2)}</pre>
    `;
  });
}