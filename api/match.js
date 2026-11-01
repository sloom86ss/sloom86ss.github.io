export default async function handler(req,res){
 res.setHeader("Cache-Control","s-maxage=30, stale-while-revalidate=120");
 if(req.method!=="GET"){res.setHeader("Allow","GET");return res.status(405).json({error:"استخدم GET."});}
 const event=String(req.query?.event||"").trim();
 const league=String(req.query?.league||"").trim();
 if(!/^\d{5,15}$/.test(event)||!/^soccer\/[a-z0-9.]+$/.test(league))return res.status(400).json({error:"معرّف المباراة أو البطولة غير صالح."});
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
 try{
  const url="https://site.api.espn.com/apis/site/v2/sports/"+league+"/summary?event="+encodeURIComponent(event);
  const response=await fetch(url,{signal:controller.signal,headers:{"Accept":"application/json","User-Agent":"SLOOM360 football match center"}});
  if(!response.ok)return res.status(response.status===404?404:502).json({error:"تفاصيل المباراة غير متاحة من مزود البيانات الآن."});
  const data=await response.json();
  const comp=data.header?.competitions?.[0]||data.boxscore?.teams?.[0]?.competition||{};
  const status=comp.status||{};
  const competitors=comp.competitors||[];
  const plays=Array.isArray(data.plays)?data.plays:(data.commentary?.items||[]);
  const events=plays.map(p=>{
   const text=p.text||p.description||p.type?.text||"";
   const type=p.type?.text||p.type?.name||"";
   return {text, type, clock:p.clock?.displayValue||p.clock||p.time||"", period:p.period?.number||p.period?.displayValue||"", team:p.team?.displayName||p.team?.name||"", athlete:p.athlete?.displayName||p.participants?.[0]?.athlete?.displayName||""};
  }).filter(x=>/goal|score|yellow card|red card|penalt|substitut|هدف|إنذار|بطاقة|طرد|استبدال/i.test(x.type+" "+x.text));
  const teams=(data.boxscore?.teams||[]).map(t=>({name:t.team?.displayName||"",logo:t.team?.logo||"",statistics:(t.statistics||[]).map(x=>({name:x.label||x.name,value:x.displayValue||x.value}))}));
  const playerGroups=(data.boxscore?.players||[]).map(group=>({team:group.team?.displayName||"",groups:(group.statistics||[]).map(g=>({name:g.name||g.text,labels:g.labels||[],athletes:(g.athletes||[]).map(a=>({name:a.athlete?.displayName||"",stats:a.stats||[],starter:a.starter,active:a.active}))}))}));
  return res.status(200).json({
   event,league,
   name:data.header?.competitions?.[0]?.competitors?.map(x=>x.team?.displayName).filter(Boolean).join(" - ")||"",
   status:status.type?.description||status.type?.detail||status.type?.name||"",
   state:status.type?.state||"",
   clock:status.displayClock||"",
   period:status.period||null,
   venue:comp.venue?.fullName||"",
   broadcast:(comp.broadcasts||[]).flatMap(x=>x.names||[]),
   competitors:competitors.map(x=>({name:x.team?.displayName||"",logo:x.team?.logo||"",score:x.score||"",winner:!!x.winner})),
   events,teams,playerGroups,
   note:"تعتمد التفاصيل على ما ينشره مزود البيانات؛ قد لا تتوفر كل أحداث المباراة أو إحصاءاتها."
  });
 }catch(error){return res.status(error.name==="AbortError"?504:502).json({error:"تعذر جلب تفاصيل المباراة حالياً."});}
 finally{clearTimeout(timer);}
}
