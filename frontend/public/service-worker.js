const CACHE_NAME = 'static-resources-v3';
const RESOURCE_URL_PATTERN = /\/api\/external\/resources\/(languages|timezones|countries)/;
const STATIC_ASSETS_PATTERN = /\/(favicon\.ico|logo192\.png|logo512\.png|manifest\.json)/;

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
    // Only intercept requests for our specific resources
    if (RESOURCE_URL_PATTERN.test(event.request.url) || STATIC_ASSETS_PATTERN.test(event.request.url)) {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    // Strategy: Cache First (Fall back to network)
                    // If cached, return it and DO NOT fetch from network.
                    if (cachedResponse) {
                        return cachedResponse;
                    }

                    // If not in cache, fetch from network
                    return fetch(event.request).then((networkResponse) => {
                        // Clone because response stream can only be consumed once
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    }).catch(err => {
                        console.warn('ServiceWorker: Network fetch failed', err);
                        // Optional: Return a fallback or just propagate error
                        throw err;
                    });
                });
            })
        );
    }
});
