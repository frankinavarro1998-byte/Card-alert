self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('push', event => {
  let data = {title:'Card Stock Alert', body:'A watched product changed.', url:'/'};
  try { data = {...data, ...event.data.json()}; } catch {}
  event.waitUntil(self.registration.showNotification(data.title, {
    body:data.body,
    icon:'/static/icon-192.svg',
    badge:'/static/icon-192.svg',
    tag:data.url,
    renotify:true,
    data:{url:data.url}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data?.url || '/'));
});
