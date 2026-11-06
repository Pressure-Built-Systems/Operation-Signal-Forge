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
import { generateBrief } from "../api.js";
import { renderAuthzReceipt } from "../authz-receipt.js";

export async function renderBrief(root, params) {
  const cellId = params.cell_id || SAMPLE_CELL.cell_id;
  root.innerHTML = `
    <h1>Detection brief</h1>
    <p class="sub">Capability: <code>generate_detection_brief</code> · cell <code>${cellId}</code></p>
    <div class="panel"><p class="muted">Loading…</p></div>
  `;

  const res = await generateBrief(cellId);

  if (!res.ok) {
    root.querySelector(".panel").innerHTML = `
      <p class="err">${res.error || "Failed to load brief"}</p>
      ${res.status === 403 ? `<p class="muted">Matrix denied this capability for the current role/scopes.</p>` : ""}
    `;
    return;
  }

  const brief = res.data?.data?.brief || res.data?.brief;
  const receipt = res.data?.authz_receipt;

  if (!brief) {
    root.querySelector(".panel").innerHTML = `<p class="err">Failed to load brief</p>`;
    return;
  }

  root.innerHTML = `
    <h1>Detection brief</h1>
    <p class="sub">Source: <strong>${res.source}</strong> · advisory only</p>
    <div class="panel">
      <h2 style="margin-top:0">${brief.headline}</h2>
      <p><span class="tag high">${brief.confidence_band}</span>
         <span class="tag">fused ${brief.fused_probability}</span>
         <span class="tag">${brief.status}</span></p>
      <h3>Scores</h3>
      <pre class="pre">${JSON.stringify(brief.scores, null, 2)}</pre>
      <h3>Recommendations</h3>
      <ul>${(brief.recommendations || []).map((r) => `<li>${r}</li>`).join("")}</ul>
    </div>
    ${renderAuthzReceipt(receipt)}
    <p><a class="link" href="#/investigate?cell_id=${encodeURIComponent(cellId)}">Run full investigation →</a></p>
  `;
}