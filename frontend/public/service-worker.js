const CACHE_NAME = 'static-resources-v4';
const RESOURCE_URL_PATTERN = /\/api\/external\/resources\/(languages|timezones|countries)/;
const STATIC_ASSETS_PATTERN = /\/(favicon\.ico|logo192\.png|logo512\.png|manifest\.json)/;
const APP_SHELL_PATTERN = /(\/|\/index\.html)$/; // Matches root / or /index.html

self.addEventListener('install', (event) => {
    // Skip waiting to activate immediately
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    // Clean up old caches if any (standard practice)
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // 1. Handle API Resources & Static Assets (Cache First / StaleWhileRevalidate hybrid as before)
    //    Actually, previous code used CacheFirst for these. Let's keep it consistent or improve.
    //    The previous code was: check cache, if found return, else fetch & cache. This is "Cache First, fall back to Network".
    if (RESOURCE_URL_PATTERN.test(url.pathname) || STATIC_ASSETS_PATTERN.test(url.pathname)) {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    return fetch(event.request).then((networkResponse) => {
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    });
                });
            })
        );
        return; // Important: prevent falling through to other strategies
    }

    // 2. Handle App Shell (Root / index.html) - Stale While Revalidate
    //    We want to serve the cached index.html immediately, but update it in background.
    if (APP_SHELL_PATTERN.test(url.pathname)) {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    const fetchPromise = fetch(event.request).then((networkResponse) => {
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    });

                    // If we have a cached response, return it immediately
                    // The fetchPromise will still execute in background and update cache
                    if (cachedResponse) {
                        return cachedResponse;
                    }

                    // If no cache, wait for network
                    return fetchPromise;
                });
            })
        );
    }
});
