const CACHE_NAME="sloom365-shell-v4";
const SHELL=["/","/index.html","/sloom360.html","/ai.html","/manifest.webmanifest","/assets/sloom360-logo.svg"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE_NAME).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE_NAME).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",e=>{
 const r=e.request,u=new URL(r.url);
 if(r.method!=="GET"||u.origin!==self.location.origin||u.pathname.endsWith("/data.json"))return;
 if(r.mode==="navigate"){e.respondWith(fetch(r).then(res=>{if(res.ok)caches.open(CACHE_NAME).then(c=>c.put(r,res.clone()));return res;}).catch(async()=>await caches.match(r)||await caches.match("/index.html")));return;}
 e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(res=>{if(res.ok)caches.open(CACHE_NAME).then(c=>c.put(r,res.clone()));return res;})));
});