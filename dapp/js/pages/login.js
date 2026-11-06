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

import { login } from "../mock-auth.js";

export function renderLogin(root) {
  root.innerHTML = `
    <div class="login-wrap panel">
      <h1>Sign in</h1>
      <p class="sub">Mock credentials only — no wallet or blockchain.</p>
      <form id="login-form">
        <label for="email">Email</label>
        <input id="email" type="email" value="analyst@example.org" autocomplete="username" />
        <label for="password">Password</label>
        <input id="password" type="password" value="analyst" autocomplete="current-password" />
        <p class="muted" style="font-size:0.8rem;margin:0 0 1rem">
          Try <code>analyst@example.org</code> / <code>analyst</code><br/>
          or <code>commander@example.org</code> / <code>commander</code>
        </p>
        <button class="btn block" type="submit">Log in</button>
        <p id="login-error" class="err" hidden></p>
      </form>
    </div>
  `;

  root.querySelector("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = root.querySelector("#email").value;
    const password = root.querySelector("#password").value;
    const err = root.querySelector("#login-error");
    err.hidden = true;

    const result = await login(email, password);   // ← await was missing

    if (!result.ok) {
      err.hidden = false;
      err.textContent = result.error || "Login failed";
      return;
    }
    location.hash = "#/dashboard";
  });
}