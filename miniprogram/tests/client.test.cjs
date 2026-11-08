const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
function harness(options = {}) {
  const storage = new Map();
  const calls = [];
  global.wx = {
    getAccountInfoSync: () => ({ miniProgram: { envVersion:options.release ? 'release' : 'develop' } }),
    getStorageSync:k=>storage.get(k), setStorageSync:(k,v)=>storage.set(k,v), removeStorageSync:k=>storage.delete(k),
    request:r=> {
      calls.push(r);
      if (r.url.endsWith('/login')) return r.success({ statusCode:200,data:{token:'session-'+calls.length,demo:true} });
      if(options.networkFailure) return r.fail();
      if(options.expire && calls.filter(c=>!c.url.endsWith('/login')).length===1) return r.success({statusCode:401,data:{}});
      r.success({statusCode:200,data:{results:[]}});
    },
    downloadFile:r=>r.success({statusCode:options.downloadStatus || 200,tempFilePath:'/tmp/text.txt'})
  };
  // Isolate fixtures from the deployment configuration.
  const config = options.realLogin ? {apiBase:'https://api.podnotes.cloud',developmentLogin:false} : {apiBase:'http://127.0.0.1:8010',developmentLogin:true};
  global.wx.login = r=>r.success({code:'wechat-test-code'});
  const module = {exports:{}};
  require('node:vm').runInNewContext(require('node:fs').readFileSync(path.join(root,'utils/api.js'),'utf8'), {module,require:()=>config,wx:global.wx,Date,Math,Promise,Error});
  const apiPath = require.resolve(path.join(root,'utils/api'));
  require.cache[apiPath] = {id:apiPath,filename:apiPath,loaded:true,exports:module.exports};
  return {api:module.exports,storage,calls};
}
test('one login shared by concurrent requests', async()=>{
  const {api,calls}=harness();
  await Promise.all([api.request('/search?q=a'),api.request('/tasks')]);
  assert.equal(calls.filter(c=>c.url.endsWith('/login')).length,1);
  assert.ok(calls.filter(c=>!c.url.endsWith('/login')).every(c=>c.header.Authorization.startsWith('Bearer session-')));
});
test('expired session refreshed once',async()=>{
  const {api,calls}=harness({expire:true});
  await api.request('/tasks');
  assert.equal(calls.filter(c=>c.url.endsWith('/login')).length,2);
});
test('network errors visible and bad downloads rejected',async()=>{
  const {api}=harness({networkFailure:true,downloadStatus:404});
  await assert.rejects(api.request('/tasks'),/无法连接/);
  await assert.rejects(api.download('x'),/文件已删除/);
});
test('release blocks dev credentials and insecure origin',()=>{
  const {api}=harness({release:true}); assert.throws(()=>api.validateConfig(),/发布配置错误/);
});
test('hiding task page stops polling even if request is pending',async()=>{
  const {api}=harness();
  let resolve;
  api.request=()=>new Promise(r=>{resolve=r;});
  let definition;
  global.Page=p=>{definition=p;};
  require(path.join(root,'pages/tasks/tasks'));
  const page={...definition,data:{...definition.data},setData(p){Object.assign(this.data,p);}};
  page.onShow();page.onHide();
  resolve({tasks:[{id:'x',status:'queued'}]});
  await new Promise(r=>setImmediate(r));
  assert.equal(page.visible,false);assert.equal(page.timer,undefined);
});
test('episode confirmation follows WeChat four-character limit and submits selected episode',async()=>{
  const {api}=harness();
  let body,switched=false,definition;
  api.request=async(url,method,data)=>{assert.equal(url,'/tasks');assert.equal(method,'POST');body=data;return {id:'job'};};
  wx.showModal=options=>{
    assert.ok([...options.confirmText].length<=4,'WeChat modal confirmText supports at most four Chinese characters');
    options.success({confirm:true});
  };
  wx.switchTab=()=>{switched=true;};
  global.Page=p=>{definition=p;};
  delete require.cache[require.resolve(path.join(root,'pages/episodes/episodes'))];
  require(path.join(root,'pages/episodes/episodes'));
  const page={...definition,data:{...definition.data},setData(p){Object.assign(this.data,p);}};
  await page.submit({currentTarget:{dataset:{id:'episode-a'}}});
  assert.deepEqual(body,{episode_id:'episode-a',rights_confirmed:true});
  assert.equal(switched,true);assert.equal(page.data.submitting,false);
});
test('modal failure remains visible instead of silently cancelling',async()=>{
  const {api}=harness();
  api.request=()=>{throw new Error('Must not submit after modal failure');};
  wx.showModal=options=>options.fail({errMsg:'test failure'});
  let definition;global.Page=p=>{definition=p;};
  delete require.cache[require.resolve(path.join(root,'pages/episodes/episodes'))];
  require(path.join(root,'pages/episodes/episodes'));
  const page={...definition,data:{...definition.data},setData(p){Object.assign(this.data,p);}};
  await page.submit({currentTarget:{dataset:{id:'episode-a'}}});
  assert.match(page.data.error,/确认窗口/);assert.equal(page.data.submitting,false);
});
test('search refreshes demo indicator after a backend mode/session change',async()=>{
  const {api}=harness();
  api.request=async()=>({results:[{id:'feed',title:'Real result'}]});
  api.session=async()=>({demo:false});
  let definition;global.Page=p=>{definition=p;};
  delete require.cache[require.resolve(path.join(root,'pages/index/index'))];
  require(path.join(root,'pages/index/index'));
  const page={...definition,data:{...definition.data,query:'test',demo:true},setData(p){Object.assign(this.data,p);}};
  await page.search();assert.equal(page.data.demo,false);assert.equal(page.data.results.length,1);
});

function pageHarness(name,extra={}) {
  let definition; global.Page=p=>{definition=p;};
  const file=path.join(root,'pages',name,name);
  delete require.cache[require.resolve(file)]; require(file);
  return {...definition,data:JSON.parse(JSON.stringify({...definition.data,...extra})),setData(p){Object.assign(this.data,p);}};
}
test('release guard rejects a cached session before any request or export',async()=>{
  const {api,storage,calls}=harness({release:true});
  storage.set('miniSession',{token:'old-develop-token'});
  await assert.rejects(api.request('/tasks'),/发布配置错误/);
  await assert.rejects(api.download('private-task'),/发布配置错误/);
  assert.equal(calls.length,0);
});
test('recent searches are deduplicated, bounded and retained when a search fails',async()=>{
  const {api,storage}=harness();
  api.request=async()=>({results:[]}); api.session=async()=>({demo:true});
  const page=pageHarness('index',{query:'  常听节目  ',recent:['a','常听节目','b','c','d','e']});
  await page.search();
  assert.deepEqual(page.data.recent,['常听节目','a','b','c','d','e']);
  assert.deepEqual(storage.get('miniRecentSearches'),page.data.recent);
  api.request=async()=>{throw Error('服务不可用');}; page.data.query='失败关键词';
  await page.search(); assert.equal(page.data.recent.includes('失败关键词'),false);
  page.clear(); assert.equal(page.data.searched,false); assert.equal(page.data.query,'');
  page.clearRecent(); assert.equal(storage.has('miniRecentSearches'),false);
});
test('episode filtering includes subsequent pages without hiding duration limits',async()=>{
  const {api}=harness(); let count=0;
  api.request=async()=>++count===1 ? {title:'节目',has_more:true,episodes:[{id:'a',title:'旅行故事',duration_seconds:65}]} : {title:'节目',has_more:false,episodes:[{id:'b',title:'旅行长篇',duration_seconds:7201},{id:'c',title:'日常',duration_seconds:null}]};
  const page=pageHarness('episodes',{query:'旅行'}); page.feedId='feed';
  await page.loadMore(); await page.loadMore();
  assert.equal(page.data.episodes.length,3); assert.equal(page.data.viewEpisodes.length,2);
  assert.equal(page.data.viewEpisodes[0].durationLabel,'约 2 分钟');
  assert.equal(page.data.viewEpisodes[1].tooLong,true);
  assert.equal(page.data.episodes[2].durationLabel,'时长待检测');
  page.clearFilter(); assert.equal(page.data.viewEpisodes.length,3);
});
test('known overlong episode never opens confirmation or submits a task',async()=>{
  const {api}=harness(); api.request=()=>{throw Error('must not submit');};
  wx.showModal=()=>{throw Error('must not open modal');};
  const page=pageHarness('episodes',{episodes:[{id:'long',title:'长节目',tooLong:true}],maxMinutes:120});
  await page.submit({currentTarget:{dataset:{id:'long'}}});
  assert.match(page.data.error,/超过 120 分钟/); assert.equal(page.data.submitting,false);
});
test('status filters retain the full task collection and correct counts',()=>{
  harness(); const page=pageHarness('tasks',{tasks:[{id:'a',status:'queued'},{id:'b',status:'transcribing'},{id:'c',status:'completed'},{id:'d',status:'failed'}]});
  page.selectFilter({currentTarget:{dataset:{filter:'active'}}});
  assert.deepEqual(page.data.viewTasks.map(t=>t.id),['a','b']);
  assert.equal(page.data.tasks.length,4); assert.equal(page.data.activeCount,2);
  page.selectFilter({currentTarget:{dataset:{filter:'completed'}}});
  assert.deepEqual(page.data.viewTasks.map(t=>t.id),['c']); assert.equal(page.data.failedCount,1);
});
test('reader filtering leaves copy intact and font preference stays within supported sizes',()=>{
  const {storage}=harness(); const full='[00:00] 旅行故事\n\n[01:00] 日常文字\n[02:00] 旅行结束';
  const page=pageHarness('reader',{task:{text:full},query:'旅行'});
  page.filter(); assert.equal(page.data.matchCount,2); assert.equal(page.data.text.includes('日常'),false);
  let copied; wx.setClipboardData=o=>{copied=o.data;}; page.copy(); assert.equal(copied,full);
  page.setFont({currentTarget:{dataset:{size:'36'}}}); assert.equal(storage.get('miniReaderFont'),36);
  page.setFont({currentTarget:{dataset:{size:'999'}}}); assert.equal(page.data.fontSize,36);
  page.clearFilter(); assert.equal(page.data.text,full); assert.equal(page.data.matchCount,0);
});
test('UI limits use server values and reject invalid settings',()=>{
  const ui=require(path.join(root,'utils/presentation'));
  assert.deepEqual(ui.limits({daily_limit:5,max_minutes:90,retention_days:14}),{dailyLimit:5,maxMinutes:90,retentionDays:14});
  assert.deepEqual(ui.limits({daily_limit:-1,max_minutes:'bad',retention_days:0}),{dailyLimit:3,maxMinutes:120,retentionDays:7});
  assert.equal(ui.duration(3600),'约 1 小时'); assert.equal(ui.duration(1),'不足 1 分钟');
});

test('HTTPS configuration uses WeChat login code in release mode',async()=>{
 const {api,calls}=harness({release:true,realLogin:true});
 api.validateConfig();
 await api.request('/tasks');
 assert.equal(calls.find(c=>c.url.endsWith('/login')).data.code,'wechat-test-code');
 assert.ok(calls.every(c=>c.url.startsWith('https://api.podnotes.cloud/mini/')));
});

test('dialogue reader preserves real timestamps, speaker search and full copy',()=>{
 harness();
 const segments=[{start_time:1.25,end_time:3,text:'你好。',speaker:'说话人 1'},{start_time:3601,end_time:3604,text:'欢迎。',speaker:'说话人 2'}];
 const page=pageHarness('reader',{task:{text:'完整带时间戳导出',segments}});
 page.filter();
 assert.equal(page.data.hasSegments,true);
 assert.equal(page.data.segments[0].time,'00:01');
 assert.equal(page.data.segments[1].time,'01:00:01');
 page.input({detail:{value:'说话人 2'}});
 assert.equal(page.data.matchCount,1); assert.equal(page.data.segments[0].text,'欢迎。');
 let copied; wx.setClipboardData=o=>{copied=o.data;}; page.copy();
 assert.equal(copied,'完整带时间戳导出');
 page.input({detail:{value:'不存在'}});
 assert.equal(page.data.hasSegments,true); assert.equal(page.data.segments.length,0);
 page.clearFilter(); assert.equal(page.data.segments.length,2);
 page.data.task={text:'旧版纯文本'}; page.filter();
 assert.equal(page.data.hasSegments,false); assert.equal(page.data.text,'旧版纯文本');
});

test('task timing shows measured values and leaves legacy jobs unknown',()=>{
 const ui=require(path.join(root,'utils/presentation'));
 assert.equal(ui.timingSummary(undefined),'');
 assert.equal(ui.timingSummary({}),'');
 assert.equal(ui.timingSummary({elapsed_seconds:125.8,download_seconds:3,transcription_seconds:120}),'总用时 2 分 5 秒 · 下载 3 秒 · 转写 2 分 0 秒');
 assert.equal(ui.elapsed(3601),'1 小时 1 秒');
 assert.equal(ui.elapsed(-1),'');
});

test('single speaker joins timestamp fragments into complete readable sentences',()=>{
 harness();
 const segments=[{start_time:0,text:'刚刚过去的双节黄金周，',speaker:'说话人 1'},{start_time:2,text:'消费市场分外惹人',speaker:'说话人 1'},{start_time:4,text:'关注。',speaker:'说话人 1'},{start_time:6,text:'这是完整的下一句。',speaker:'说话人 1'}];
 const raw='[00:00] 说话人 1\n碎片化导出';
 const page=pageHarness('reader',{task:{text:raw,segments}});
 page.filter();
 const full='刚刚过去的双节黄金周，消费市场分外惹人关注。这是完整的下一句。';
 assert.equal(page.data.hasSegments,false);assert.equal(page.data.text,full);
 page.input({detail:{value:'惹人关注'}});assert.equal(page.data.matchCount,1);assert.equal(page.data.text,full);
 page.input({detail:{value:'不存在'}});assert.equal(page.data.text,'');
 let copied;wx.setClipboardData=o=>{copied=o.data;};page.copy();assert.equal(copied,full);
 assert.deepEqual(page.data.task.segments,segments);
});

test('single-speaker paragraph breaks wait for complete sentences and retain English spaces',()=>{
 const ui=require(path.join(root,'utils/presentation'));
 const first='这是一句很长但还没有结束的文字'.repeat(12);
 const result=ui.readableTranscript({segments:[{text:first},{text:'，仍在同一句中'},{text:'，现在才结束。'},{text:'Hello'},{text:'world.'}]});
 assert.equal(result.text,first+'，仍在同一句中，现在才结束。\n\nHello world.');
});

test('single-speaker TXT shares complete natural text after authenticated download',async()=>{
 const {api}=harness();let downloaded=false,written,shared;
 api.download=async id=>{assert.equal(id,'single');downloaded=true;return '/tmp/original.txt';};
 wx.env={USER_DATA_PATH:'/user'};wx.canIUse=()=>true;
 wx.getFileSystemManager=()=>({writeFile:o=>{assert.equal(downloaded,true);written=o;o.success();}});
 wx.shareFileMessage=o=>{shared=o;o.success();};
 const page=pageHarness('reader',{task:{text:'原始时间片段',segments:[{text:'一句',speaker:'甲'},{text:'完整的话。',speaker:'甲'}]},query:'不存在'});
 page.taskId='single';page.filter();await page.export();
 assert.equal(written.data,'\ufeff一句完整的话。');assert.equal(shared.filePath,written.filePath);
 assert.equal(page.data.error,'');assert.equal(page.data.exporting,false);
});

test('ETA uses honest ranges, queue count, unknown and overdue states',()=>{
 const ui=require(path.join(root,'utils/presentation'));
 assert.equal(ui.estimateSummary({status:'completed',estimate:{overdue:true}}),'');
 assert.match(ui.estimateSummary({status:'queued'}),/正在估算/);
 assert.match(ui.estimateSummary({status:'queued',estimate:{queue_ahead:2,remaining_lower_seconds:60,remaining_upper_seconds:180,basis:'initial'}}),/前方 2 个任务.*约 1—3 分钟.*初步估算/);
 assert.match(ui.estimateSummary({status:'transcribing',estimate:{remaining_lower_seconds:10,remaining_upper_seconds:45}}),/不足 1 分钟/);
 assert.match(ui.estimateSummary({status:'transcribing',estimate:{remaining_lower_seconds:0,remaining_upper_seconds:0,overdue:true}}),/超出预估，仍在继续/);
 assert.match(ui.estimateSummary({status:'queued',estimate:{remaining_lower_seconds:null,remaining_upper_seconds:null}}),/正在估算/);
 assert.match(ui.estimateSummary({status:'queued',estimate:{remaining_lower_seconds:100,remaining_upper_seconds:50}}),/正在估算/);
});

for(const name of ['tasks','reader']) {
 test(name+' ignores an old response after hide/show and resumes polling once',async()=>{
  const {api}=harness();const pending=[];
  api.request=()=>new Promise(resolve=>pending.push(resolve));
  api.session=async()=>({demo:false});
  const page=pageHarness(name);page.taskId='same-job';
  page.onShow();page.onHide();page.onShow();
  assert.equal(pending.length,2);
  const response=status=>name==='tasks' ? {tasks:[{id:'same-job',status}]} : {id:'same-job',status};
  pending[0](response('completed'));
  await new Promise(r=>setImmediate(r));
  assert.equal(page.data.loading,true,'stale request cannot clear the new busy state');
  assert.equal(page.timer,undefined);
  pending[1](response('transcribing'));
  await new Promise(r=>setImmediate(r));
  assert.equal(name==='tasks'?page.data.tasks[0].status:page.data.task.status,'transcribing');
  assert.ok(page.timer);
  page.onHide();
 });
 test(name+' returns to the same server task completed while away',async()=>{
  const {api}=harness();
  let count=0;
  api.request=async()=>name==='tasks' ? {tasks:[{id:'same-job',status:++count===1?'transcribing':'completed'}]} : {id:'same-job',status:++count===1?'transcribing':'completed',text:'done'};
  api.session=async()=>({demo:false});
  const page=pageHarness(name);page.taskId='same-job';
  page.onShow();await new Promise(r=>setImmediate(r));page.onHide();
  page.onShow();await new Promise(r=>setImmediate(r));
  const task=name==='tasks'?page.data.tasks[0]:page.data.task;
  assert.equal(task.id,'same-job');assert.equal(task.status,'completed');
  assert.equal(name==='tasks'?task.estimateLabel:page.data.estimateLabel,'');
  page.onHide();
 });
}

test('reader retries transient errors only while visible and preserves task',async()=>{
 const {api}=harness();api.request=async()=>{throw Error('连接失败');};
 const page=pageHarness('reader',{task:{id:'kept',status:'transcribing'}});page.taskId='kept';
 page.onShow();await new Promise(r=>setImmediate(r));
 assert.equal(page.data.task.id,'kept');assert.match(page.data.error,/不会取消已提交任务/);assert.ok(page.timer);
 page.onHide();
});



for(const name of ['tasks','reader']) {
 test(name+' does not describe a permanent API error as a network interruption',async()=>{
  const {api}=harness();api.request=async()=>{const e=Error('任务不存在');e.status=404;throw e;};
  const page=pageHarness(name);page.taskId='missing';
  page.onShow();await new Promise(r=>setImmediate(r));
  assert.equal(page.data.error,'任务不存在');assert.equal(page.data.loading,false);assert.equal(page.timer,undefined);
  page.onHide();
 });
}

