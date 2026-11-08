/* Real catalog check; --ui adds explicitly labeled in-memory UI fixtures. Never submits audio. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const automator=require(process.env.MINI_AUTOMATOR_MODULE || '/tmp/podcast-mini-qa/node_modules/miniprogram-automator');
const uiCheck=process.argv.includes('--ui');
const output=path.resolve(__dirname,'../docs/miniprogram/screenshots',process.argv.includes('--editorial') ? 'editorial-redesign' : (uiCheck ? 'ui-iteration' : '.'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,label){const end=Date.now()+45000;while(Date.now()<end){const value=await fn();if(value)return value;await sleep(250);}throw new Error('Timed out: '+label);}
(async()=>{
 const health=await fetch('http://127.0.0.1:8010/mini/health').then(r=>r.json());
 assert.ok(health.development && !health.demo,'Requires local REAL mode');
 const mini=await automator.connect({wsEndpoint:'ws://127.0.0.1:9421'});
 const errors=[];mini.on('exception',e=>errors.push(e));
 const watchdog=setTimeout(()=>{console.error('Catalog check timed out');process.exit(1);},100000);
 try {
  fs.mkdirSync(output,{recursive:true});
  let page=await mini.reLaunch('/pages/index/index');
  if(uiCheck) {
   await until(async()=>!(await page.data('loading')) && await page.data('development'),'home session');
   await mini.screenshot({path:path.join(output,'01-home.png')});
  }
  await (await page.$('input')).input('知行小酒馆');
  await (await page.$('button.primary')).tap();
  await until(async()=>{const d=await page.data();if(d.error)throw new Error(d.error);return !d.loading && d.results.length;},'real results');
  assert.equal(await page.data('demo'),false);
  await mini.screenshot({path:path.join(output,'06-real-search.png')});
  await (await page.$('.row')).tap();
  page=await until(async()=>{const p=await mini.currentPage();return p && p.path==='pages/episodes/episodes' ? p:null;},'real episodes page');
  await until(async()=>{const d=await page.data();if(d.error)throw new Error(d.error);return !d.loading && d.episodes.length;},'real RSS episodes');
  const d=await page.data();assert.equal(d.demo,false);assert.match(d.title,/知行小酒馆/);
  await mini.screenshot({path:path.join(output,'07-real-episodes.png')});
  const checks=['Real search and RSS list; no audio submitted'];
  if(uiCheck) {
   const episodeInput=await page.$('input');
   await episodeInput.input('不存在的单集QA');
   await until(async()=>(await page.data('viewEpisodes')).length===0,'empty episode filter');
   assert.equal((await page.data('episodes')).length,20);
   await mini.screenshot({path:path.join(output,'08-episode-empty.png')});
   await (await page.$('.clear-button')).tap();
   await until(async()=>(await page.data('viewEpisodes')).length===20,'clear episode filter');
   checks.push('Episode filter and clear preserve loaded data');
   await mini.switchTab('/pages/tasks/tasks');
   page=await until(async()=>{const p=await mini.currentPage();return p && p.path==='pages/tasks/tasks' ? p:null;},'tasks page');
   await until(async()=>!(await page.data('loading')),'tasks settled');
   await mini.screenshot({path:path.join(output,'02-tasks-live.png')});
   const now=Math.floor(Date.now()/1000);
   const fixtures=[{id:'ui-only-completed',title:'示例：把一期播客，留成可以重读的文字',status:'completed',label:'文字已就绪',hint:'打开阅读、复制或导出全文',createdLabel:'示例记录'},{id:'ui-only-active',title:'示例：长节目正在转写，稍后回来查看',status:'transcribing',label:'正在转写',hint:'正在识别音频，长节目需要更多时间',createdLabel:'示例记录'},{id:'ui-only-failed',title:'示例：音频来源暂时无法连接',status:'failed',label:'处理失败',hint:'打开记录查看原因和重试方式',error:'音频来源暂不可用，请稍后重新提交',createdLabel:'示例记录'}];
   await page.setData({tasks:fixtures,viewTasks:fixtures,activeCount:1,completedCount:1,failedCount:1,filter:'all',demo:true,error:''});
   await mini.screenshot({path:path.join(output,'03-tasks-fixture.png')});
   await (await page.$$('[data-filter="completed"]'))[0].tap();
   await until(async()=>(await page.data('viewTasks')).length===1,'completed task filter');
   assert.equal((await page.data('viewTasks'))[0].id,'ui-only-completed');
   await mini.screenshot({path:path.join(output,'04-tasks-filter.png')});
   checks.push('Task status controls verified with explicitly labeled UI-only fixtures; no server task created');
   page=await mini.reLaunch('/pages/reader/reader?id=ui-only-fixture');
   await until(async()=>!(await page.data('loading')) && !!(await page.data('error')),'fixture reader initial 404');
   const text='【演示内容，并非真实播客转写】\n\n[00:00] 一期播客，不必只听过一遍。\n\n[01:20] 把喜欢的片段留下来，读的时候可以调节字号。\n\n[03:10] 输入关键词，快速找到相关文字。复制和导出仍会保留全文。\n\n[05:30] 本页是界面测试样例，没有下载或转写第三方节目。';
   await page.setData({task:{id:'ui-only-fixture',title:'示例：让值得记住的声音，成为文字',status:'completed',text,created:now},text,query:'',charCount:text.replace(/\s/g,'').length,statusLabel:'文字已就绪',createdLabel:'示例记录',expiresLabel:'示例保留日期',demo:true,error:'',fontSize:32,loading:false});
   await mini.screenshot({path:path.join(output,'05-reader-fixture.png')});
   await (await page.$('[data-size="36"]')).tap();
   await until(async()=>await page.data('fontSize')===36,'large reading font');
   await (await page.$('input')).input('关键词');
   await until(async()=>await page.data('matchCount')===1,'reader match count');
   assert.match(await page.data('text'),/关键词/);
   assert.ok(!(await page.data('text')).includes('一期播客'));
   await mini.screenshot({path:path.join(output,'09-reader-filter.png')});
   await (await page.$('.clear-button')).tap();
   await until(async()=>await page.data('text')===text,'clear reader filter');
   checks.push('Reader font, match count and clear verified with labeled UI-only transcript; no clipboard or file sent');
   const longText='【长正文界面测试，非真实播客转写】\n\n'+Array.from({length:200},(_,i)=>`[${String(i).padStart(3,'0')}] 这是第${i+1}段界面测试文字，用于检查长正文阅读、关键词筛选和页面滚动。内容仅供本机界面验证。`).join('\n\n');
   await page.setData({task:{id:'ui-only-fixture',title:'示例：长正文阅读与滚动检查',status:'completed',text:longText,created:now},text:longText,charCount:longText.replace(/\s/g,'').length});
   await mini.callWxMethod('pageScrollTo',{scrollTop:1000000,duration:0});
   await sleep(300);
   assert.ok((await page.scrollTop())>1000,'Long transcript can be scrolled');
   await mini.screenshot({path:path.join(output,'10-reader-long-bottom.png')});
   await mini.callWxMethod('pageScrollTo',{scrollTop:0,duration:0});
   await (await page.$('input')).input('第200段');
   await until(async()=>await page.data('matchCount')===1,'long transcript final paragraph match');
   assert.match(await page.data('text'),/第200段/);
   checks.push('200-paragraph local fixture scrolls to the end and final paragraph remains searchable');
   await mini.reLaunch('/pages/index/index');
  }
  assert.equal(errors.length,0);
  const report={status:'passed',mode:uiCheck ? 'real catalog plus labeled local UI fixtures' : 'real catalog, read only',title:d.title,first_page_episodes:d.episodes.length,has_more:d.hasMore,submitted_audio:false,checks,exceptions:errors};
  fs.writeFileSync(path.join(output,'real-catalog-validation.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
 } finally {clearTimeout(watchdog);await mini.disconnect();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
