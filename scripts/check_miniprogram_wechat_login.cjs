/* Native simulator -> real WeChat login -> public Windows API. No audio or exports. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const automator=require('/tmp/podcast-mini-qa/node_modules/miniprogram-automator');
const out=path.resolve(__dirname,'../docs/miniprogram/screenshots/windows-integration');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label){const end=Date.now()+45000;while(Date.now()<end){const v=await fn();if(v)return v;await wait(350);}throw Error('Timeout: '+label);}
(async()=>{
 const config=require('../miniprogram/config');
 assert.equal(config.developmentLogin,false);
 assert.equal(config.apiBase,'https://api.podnotes.cloud');
 fs.mkdirSync(out,{recursive:true});
 const mini=await automator.connect({wsEndpoint:'ws://127.0.0.1:9421'});
 const watchdog=setTimeout(()=>{console.error('Native integration timed out');process.exit(1);},95000);
 let stage='login/search';
 try{
  if(process.argv.includes('--diagnose')) {
   let login;
   try { login=await mini.callWxMethod('login'); console.log(JSON.stringify({stage:'wx.login',hasCode:!!login.code,errMsg:login.errMsg})); }
   catch(e) { console.log(JSON.stringify({stage:'wx.login',error:e.message})); return; }
   if(login.code) {
    const r=await mini.callWxMethod('request',{url:config.apiBase+'/mini/login',method:'POST',data:{code:login.code}});
    console.log(JSON.stringify({stage:'backend.login',status:r.statusCode,detail:typeof r.data?.detail==='string'?r.data.detail:undefined,sessionReturned:!!r.data?.token}));
    if(r.data?.token && process.argv.includes('--tasks')) {
     const headers={Authorization:'Bearer '+r.data.token};
     const listing=await mini.callWxMethod('request',{url:config.apiBase+'/mini/tasks',method:'GET',header:headers});
     console.log(JSON.stringify({stage:'backend.tasks',status:listing.statusCode,count:listing.data?.tasks?.length}));
     for(const job of (listing.data?.tasks || []).slice(0,5)) {
      const response=await mini.callWxMethod('request',{url:config.apiBase+'/mini/tasks/'+encodeURIComponent(job.id),method:'GET',header:headers});
      const data=response.data || {}; const segments=data.segments || []; const text=data.text || '';
      console.log(JSON.stringify({stage:'backend.task',id:job.id,title:job.title,created:job.created,status:job.status,http:response.statusCode,hasSegmentsField:Object.hasOwn(data,'segments'),segmentCount:segments.length,speakers:[...new Set(segments.map(s=>s.speaker).filter(Boolean))],lastSegmentEnd:segments.at(-1)?.end_time,textLength:text.length,timestampCount:(text.match(/\[\d{2}:\d{2}(?::\d{2})?\]/g)||[]).length,legacyHeader:text.startsWith('Title:'),timing:data.timing || null}));
     }
    }
    if(r.data?.token && process.argv.includes('--quota')) {
     const session=await mini.callWxMethod('request',{url:config.apiBase+'/mini/session',method:'GET',header:{Authorization:'Bearer '+r.data.token}});
     console.log(JSON.stringify({stage:'backend.session',status:session.statusCode,dailyLimit:session.data?.daily_limit,demo:session.data?.demo}));
    }
    if(r.data?.token && process.argv.includes('--search')) {
     const search=await mini.callWxMethod('request',{url:config.apiBase+'/mini/search',method:'GET',data:{q:'知行小酒馆'},header:{Authorization:'Bearer '+r.data.token}});
     console.log(JSON.stringify({stage:'backend.search',status:search.statusCode,detail:typeof search.data?.detail==='string'?search.data.detail:undefined,resultCount:search.data?.results?.length}));
     const feed=search.data?.results?.[0];
     if(feed){const ep=await mini.callWxMethod('request',{url:config.apiBase+'/mini/feeds/'+encodeURIComponent(feed.id)+'/episodes',method:'GET',header:{Authorization:'Bearer '+r.data.token}});console.log(JSON.stringify({stage:'backend.episodes',status:ep.statusCode,detail:typeof ep.data?.detail==='string'?ep.data.detail:undefined,count:ep.data?.episodes?.length}));}

    }
   }
   return;
  }
  await mini.callWxMethod('removeStorageSync','miniSession');
  let page=await mini.reLaunch('/pages/index/index');
  await (await page.$('input')).input('知行小酒馆');
  await (await page.$('button.primary')).tap();
  await until(async()=>{const d=await page.data();if(d.error)throw Error(d.error);return !d.loading && d.results.length;},'WeChat login and search');
  assert.equal(await page.data('demo'),false);
  await mini.screenshot({path:path.join(out,'search.png')});
  const count=(await page.data('results')).length;
  stage='episodes';
  await (await page.$('.row')).tap();
  page=await until(async()=>{const p=await mini.currentPage();return p.path==='pages/episodes/episodes'?p:null;},'episodes page');
  await until(async()=>{const d=await page.data();if(d.error)throw Error(d.error);return !d.loading && d.episodes.length;},'RSS episodes');
  await mini.screenshot({path:path.join(out,'episodes.png')});
  const report={status:'passed',origin:config.apiBase,mode:'native simulator; fresh wx.login; real public API',search_results:count,episode_count:(await page.data('episodes')).length,submitted_audio:false,phone_tested:false};
  fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
 }catch(e){fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify({status:'failed',stage,error:e.message,submitted_audio:false},null,2));throw Error(stage+': '+e.message);}
 finally{clearTimeout(watchdog);await mini.disconnect();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
