// Usage tracker – tools.aaris.tech
// Sends a single page-view event when a tool is loaded.
(function () {
  var m = location.pathname.match(/^\/tools\/([^/]+)/);
  if (!m) return;
  var slug = m[1];
  try {
    var blob = new Blob([JSON.stringify({ slug: slug })], { type: 'application/json' });
    navigator.sendBeacon('/api/track', blob);
  } catch (_) {
    // sendBeacon unavailable — fire-and-forget XHR
    var x = new XMLHttpRequest();
    x.open('POST', '/api/track');
    x.setRequestHeader('Content-Type', 'application/json');
    x.send(JSON.stringify({ slug: slug }));
  }
})();
