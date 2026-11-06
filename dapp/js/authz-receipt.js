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

/**
 * Render the AuthZ receipt returned by dapp_api on successful capability calls.
 * Phase-1 façade only — proof validity ≠ authorization; Matrix remains sole authorizer.
 */
export function renderAuthzReceipt(receipt) {
    if (!receipt || typeof receipt !== "object") {
      return `<div class="authz-receipt muted">No authorization receipt returned</div>`;
    }
  
    const decision = receipt.decision || "—";
    const decisionClass = decision === "allow" ? "ok" : "err";
  
    return `
      <div class="authz-receipt panel">
        <h3 style="margin-top:0;font-size:0.95rem">Authorization receipt</h3>
        <p class="muted" style="margin:0 0 0.5rem;font-size:0.8rem">
          Server-side AuthZ decision (Phase 1 mock). Matrix is sole authorizer.
        </p>
        <dl class="receipt-grid">
          <dt>Decision</dt><dd class="${decisionClass}">${decision}</dd>
          <dt>Capability</dt><dd><code>${receipt.capability || "—"}</code></dd>
          <dt>Role</dt><dd>${receipt.role || "—"}</dd>
          <dt>Subject</dt><dd><code>${receipt.subject_id || "—"}</code></dd>
        </dl>
      </div>
    `;
  }