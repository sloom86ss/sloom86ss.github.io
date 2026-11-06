const CACHE_NAME='smart-edu-360-v8';
const CORE_FILES=[
 './','./index.html','./manifest.webmanifest','./icon.svg',
 './manners-course.html','./smart-teacher.html','./manners-listening.html','./assessment.html','./certificates.html',
 './alphabet.html','./handwriting.html','./word-writing.html','./english-course.html','./english-assessment.html','./phonics.html','./certificates.html',
 './images/lessons/alphabet.svg',
 './images/lessons/handwriting.svg',
 './images/lessons/phonics.svg',
 './images/lessons/listening.svg',
 './images/lessons/reading.svg',
 './images/lessons/word-writing.svg',
 './images/lessons/dictation.svg',
 './images/lessons/sentences.svg',
 './images/lessons/build-sentences.svg',
 './images/lessons/sentence-writing.svg',
 './images/lessons/grammar.svg',
 './images/lessons/conversation.svg',
 './images/lessons/daily-conversations.svg',
 './images/lessons/advanced-listening.svg',
 './images/lessons/speaking.svg',
 './images/lessons/paragraph-writing.svg',
 './images/lessons/manners-1.svg',
 './images/lessons/manners-2.svg',
 './images/lessons/manners-3.svg',
 './images/lessons/manners-4.svg'
];
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(CORE_FILES)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE_NAME).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const request=event.request;
 if(request.method!=='GET'||new URL(request.url).origin!==self.location.origin)return;
 event.respondWith(caches.match(request).then(cached=>{
  const fresh=fetch(request).then(response=>{
   if(response&&response.ok){const copy=response.clone();caches.open(CACHE_NAME).then(cache=>cache.put(request,copy));}
   return response;
  }).catch(()=>cached);
  return cached||fresh;
 }));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(list=>{
  for(const client of list){if('focus' in client)return client.focus();}
  if(clients.openWindow)return clients.openWindow('./index.html');
 }));
});
