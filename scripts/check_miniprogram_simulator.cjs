/* Official WeChat simulator QA; local demo only. Never uploads or sends files. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const automator = require(process.env.MINI_AUTOMATOR_MODULE || '/tmp/podcast-mini-qa/node_modules/miniprogram-automator');
const output = path.resolve(__dirname, '../docs/miniprogram/screenshots');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, label, timeout = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const result = await fn();
    if (result) return result;
    await sleep(250);
  }
  throw new Error('Timed out: ' + label);
}
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const health = await fetch('http://127.0.0.1:8010/mini/health').then(r=>r.json());
  assert.ok(health.development && health.demo, 'This check only supports the local DEMO service');
  const mini = await automator.connect({ wsEndpoint:'ws://127.0.0.1:9421' });
  const exceptions = [];
  const consoleErrors = [];
  mini.on('console', event => { if (event.type === 'error' || event.level === 'error') consoleErrors.push({type:event.type || event.level, message:String(event.message || event.text || 'Console error').slice(0,300)}); });
  mini.on('exception', e => exceptions.push(e));
  const report = { mode:'local-demo', screenshots:[], checks:[], exceptions, consoleErrors };
  const shot = async name => {
    await mini.screenshot({ path:path.join(output,name+'.png') });
    report.screenshots.push(name+'.png');
  };
  const pageAt = wanted => until(async()=>{
    const p=await mini.currentPage(); return p && p.path===wanted ? p : null;
  },'page '+wanted);
  const ready = page => until(async()=>{
    const d=await page.data();
    if(d.error) throw new Error('Page error: '+d.error);
    return !d.loading;
  },'page ready');
  const timeout = setTimeout(()=>{ console.error('Simulator QA exceeded 120 seconds'); process.exit(1); },120000);
  try {
    let page = await mini.reLaunch('/pages/index/index');
    await until(async()=>await page.data('demo'), 'demo session');
    await shot('01-search');
    const input = await page.$('input');
    await input.input('演示播客');
    await (await page.$('button.primary')).tap();
    await until(async()=>{const d=await page.data();if(d.error)throw new Error(d.error);return d.results.length>0 && !d.loading;},'search results');
    await shot('02-results');
    report.checks.push('Search input and result render');
    await (await page.$('.row')).tap();
    page=await pageAt('pages/episodes/episodes');
    await until(async()=>{const d=await page.data();if(d.error)throw new Error(d.error);return d.episodes.length>0 && !d.loading;},'episode list');
    await shot('03-episodes');
    await (await page.$('button.primary')).tap();
    await sleep(300);
    await mini.native().confirmModal();
    page=await pageAt('pages/tasks/tasks');
    await ready(page);
    await shot('04-tasks');
    report.checks.push('Episode selection, confirmation and task creation');
    const submittedId=(await page.data('tasks'))[0].id;
    await until(async()=>{const d=await page.data();if(d.error)throw new Error(d.error);return d.tasks.some(t=>t.id===submittedId && t.status==='completed');},'newly submitted task completes');
    const data=await page.data();
    const task=data.tasks.find(t=>t.id===submittedId);
    await (await page.$$('.row'))[(await page.data('tasks')).findIndex(t=>t.id===task.id)].tap();
    page=await pageAt('pages/reader/reader');
    await until(async()=>{const d=await page.data();if(d.error)throw new Error(d.error);return d.task && d.task.status==='completed';},'transcript');
    assert.match(await page.data('text'),/演示内容/);
    await shot('05-reader');
    const readerInput=await page.$('input');
    await readerInput.input('不存在的关键词QA');
    await until(async()=>await page.data('text')==='', 'empty keyword result');
    await readerInput.input('文字');
    await until(async()=>{const text=await page.data('text');return text && text.includes('文字');},'keyword match');
    await readerInput.input('');
    report.checks.push('Transcript render and keyword filtering');
    const session=await mini.callWxMethod('getStorageSync','miniSession');
    const download=await mini.callWxMethod('downloadFile',{
      url:'http://127.0.0.1:8010/mini/tasks/'+task.id+'/export',
      header:{Authorization:'Bearer '+session.token}
    });
    assert.equal(download.statusCode,200);
    const text=await mini.evaluate(file=>wx.getFileSystemManager().readFileSync(file,'utf8'),download.tempFilePath);
    assert.match(text,/演示内容/);
    report.checks.push('Authenticated TXT download and file contents; no file sent');
    await mini.switchTab('/pages/tasks/tasks');
    page=await pageAt('pages/tasks/tasks');
    await ready(page);
    assert.ok((await page.data('tasks')).some(t=>t.id===task.id));
    report.checks.push('Completed task survives navigation away and back');
    await (await page.$$('.row'))[(await page.data('tasks')).findIndex(t=>t.id===task.id)].tap();
    await pageAt('pages/reader/reader');
    assert.equal(exceptions.length,0,'Unexpected simulator exceptions');
    assert.equal(consoleErrors.length,0,'Unexpected simulator console errors');
    report.status='passed';
    console.log(JSON.stringify({status:report.status,checks:report.checks,screenshots:report.screenshots},null,2));
  } catch (error) {
    report.status='failed'; report.error=error.message;
    try { await shot('failure'); } catch (_) {}
    throw error;
  } finally {
    clearTimeout(timeout);
    fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify(report,null,2));
    await mini.disconnect();
  }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
