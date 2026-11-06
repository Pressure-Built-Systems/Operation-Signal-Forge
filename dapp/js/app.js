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

import { getSession, isLoggedIn, logout } from "./mock-auth.js";
import { renderLogin } from "./pages/login.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderInvestigations } from "./pages/investigations.js";
import { renderBrief } from "./pages/brief.js";
import { renderInvestigate } from "./pages/investigate.js";
import { renderTrustRegistry } from "./pages/trust-registry.js";
import { renderIdentity } from "./pages/identity.js";

const main = document.getElementById("main");
const topbar = document.getElementById("topbar");
const userLabel = document.getElementById("user-label");

document.getElementById("btn-logout")?.addEventListener("click", () => {
  logout();
  location.hash = "#/login";
  route();
});

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "") || "dashboard";
  const [path, qs] = raw.split("?");
  const params = Object.fromEntries(new URLSearchParams(qs || ""));
  return { path, params };
}

function setActiveNav(path) {
  document.querySelectorAll("nav a").forEach((a) => {
    const href = a.getAttribute("href").replace("#/", "");
    a.classList.toggle("active", href === path);
  });
}

/** Compact scopes string for the topbar (first 3 + remaining count). */
function formatScopes(scopes) {
  if (!Array.isArray(scopes) || scopes.length === 0) return "no scopes";
  if (scopes.length <= 3) return scopes.join(", ");
  return `${scopes.slice(0, 3).join(", ")} +${scopes.length - 3}`;
}

export function route() {
  const { path, params } = parseHash();
  const loggedIn = isLoggedIn();

  if (!loggedIn && path !== "login") {
    location.hash = "#/login";
  }

  const session = getSession();
  if (session) {
    topbar.hidden = false;
    const role = session.role || "—";
    const scopesStr = formatScopes(session.scopes);
    userLabel.innerHTML = `
      <span class="user-name">${session.name || session.email || "user"}</span>
      <span class="user-role">${role}</span>
      <span class="user-scopes" title="${(session.scopes || []).join("\n")}">${scopesStr}</span>
    `;
  } else {
    topbar.hidden = true;
    userLabel.textContent = "";
  }

  const effective = !loggedIn ? "login" : path === "login" ? "dashboard" : path;
  if (loggedIn && path === "login") {
    location.hash = "#/dashboard";
  }

  setActiveNav(effective === "login" ? "" : effective);

  const map = {
    login: () => renderLogin(main),
    dashboard: () => renderDashboard(main, session),
    investigations: () => renderInvestigations(main),
    brief: () => renderBrief(main, params),
    investigate: () => renderInvestigate(main, params),
    "trust-registry": () => renderTrustRegistry(main),
    identity: () => renderIdentity(main, session),
  };

  const fn = map[effective] || map.dashboard;
  fn();
}

window.addEventListener("hashchange", route);
route();