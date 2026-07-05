/**
 * MindBloom Service Worker
 * Enables offline functionality and caching
 */

const CACHE_NAME = 'mindbloom-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/css/styles.css',
    '/js/app.js',
    '/js/storage.js',
    '/js/safety.js',
    '/js/i18n.js',
    '/js/voice.js',
    '/js/ads.js',
    '/js/classes.js',
    '/icons/icon-192.png',
    '/icons/icon-512.png'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[SW] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
            .catch(err => console.log('[SW] Cache failed:', err))
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activating...');
    event.waitUntil(
        caches.keys()
            .then(keys => {
                return Promise.all(
                    keys.filter(key => key !== CACHE_NAME)
                        .map(key => caches.delete(key))
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - cache-first strategy
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip external requests
    if (!event.request.url.startsWith(self.location.origin)) return;

    event.respondWith(
        caches.match(event.request)
            .then(cachedResponse => {
                if (cachedResponse) {
                    // Return cached version
                    return cachedResponse;
                }

                // Fetch from network and cache
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200) {
                            return response;
                        }

                        // Clone the response
                        const responseToCache = response.clone();

                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch(() => {
                        // Return offline fallback for navigation requests
                        if (event.request.mode === 'navigate') {
                            return caches.match('/index.html');
                        }
                    });
            })
    );
});

// Handle background sync for offline data
self.addEventListener('sync', event => {
    if (event.tag === 'sync-checkins') {
        console.log('[SW] Syncing check-ins...');
        // Future: sync offline data when back online
    }
});

// Handle push notifications
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        self.registration.showNotification(data.title || 'MindBloom', {
            body: data.body || 'Time for your daily check-in',
            icon: '/icons/icon-192.png',
            badge: '/icons/icon-72.png',
            tag: 'mindbloom-notification',
            vibrate: [100, 50, 100]
        });
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/')
    );
});
