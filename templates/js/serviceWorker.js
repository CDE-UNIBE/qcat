/*
 * Basic service worker which returns an 'offline' template with info that
 * a proper offline mode is on the todo list.
 */

'use strict';

var version = {{ version }};
var currentCache = {
  offline: 'cache' + version
};
const templateUrl = '{{ template_url }}';

this.addEventListener('install', event => {
  event.waitUntil(
    caches.open(currentCache.offline).then(function(cache) {
      return cache.addAll([
        templateUrl
      ]);
    })
  );
});

this.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request.url).catch(error => {
        // Return the offline page
        return caches.match(templateUrl);
      })
    );
  }
  else {
    // Respond with everything else if we can
    event.respondWith(caches.match(event.request).then(function (response) {
      return response || fetch(event.request);
    }));
  }
});
