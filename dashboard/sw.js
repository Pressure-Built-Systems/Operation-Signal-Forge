/* Signal Forge dashboard — tile + shell cache
 * Caches OSM tiles as they are viewed and core static assets.
 * Does not pre-download world tiles (OSM usage policy).
 */
const SHELL_CACHE = 'sf-dashboard-shell-v1';
const TILE_CACHE = 'sf-osm-tiles-v1';
const TILE_HOSTS = [
  'tile.openstreetmap.org',
  'a.tile.openstreetmap.org',
  'b.tile.openstreetmap.org',
  'c.tile.openstreetmap.org',
];

const SHELL_URLS = [
  './',
  './index.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== TILE_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

function isTileRequest(url) {
  try {
    const u = new URL(url);
    return TILE_HOSTS.some((h) => u.hostname === h || u.hostname.endsWith('.' + h));
  } catch (_) {
    return false;
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = req.url;

  if (isTileRequest(url)) {
    event.respondWith(
      caches.open(TILE_CACHE).then(async (cache) => {
        const cached = await cache.match(req);
        if (cached) return cached;
        try {
          const res = await fetch(req);
          // Cross-origin tile responses are often "opaque" (status 0, ok=false)
          // but still cacheable and usable as image data.
          if (res && (res.ok || res.type === 'opaque' || res.status === 0)) {
            try {
              await cache.put(req, res.clone());
            } catch (putErr) {
              console.warn('[tiles] cache.put failed', putErr);
            }
          }
          return res;
        } catch (err) {
          return new Response('', { status: 503, statusText: 'Tile unavailable offline' });
        }
      })
    );
    return;
  }

  // Same-origin dashboard shell: network-first, fall back to cache
  const dest = req.destination;
  if (dest === 'document' || dest === 'script' || dest === 'style' || url.includes('index.html')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then((c) => c || caches.match('./index.html')))
    );
  }
});