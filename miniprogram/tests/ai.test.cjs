const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function page(name,api,wx={}) {
 let definition;const timers=[];
 vm.runInNewContext(fs.readFileSync(path.join(root,'pages',name,name+'.js'),'utf8'),{
  require:n=>n.endsWith('/api')?api:require(path.join(root,'utils/presentation')),
  Page:p=>definition=p,wx:{getStorageSync:()=>null,...wx},Promise,Error,Number,String,
  setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{}
 });
 return {page:{...definition,data:{...definition.data},setData(p){Object.assign(this.data,p);}},timers};
}
test('exhausted trial routes to personal settings without posting or altering original',async()=>{
 let route;const {page:p}=page('reader',{request:()=>{throw Error('must not call');}},{navigateTo:x=>route=x.url});
 p.data.aiSettings={personal_configured:false,trial_remaining:0};p.data.text='original transcript';
 await p.generateAI();assert.match(route,/ai-settings/);assert.equal(p.data.text,'original transcript');
});
test('AI confirmation explains one shared free operation and preserves transcript',async()=>{
 let content;const {page:p}=page('reader',{}, {showModal:o=>{content=o.content;o.success({confirm:false});}});
 p.data.aiSettings={personal_configured:false,trial_remaining:2};p.data.text='original';await p.generateAI();
 assert.match(content,/成功消耗1次免费额度/);assert.match(content,/失败不扣/);assert.match(content,/原文保持可阅读/);assert.equal(p.data.text,'original');
});
test('personal key confirmation describes personal billing',async()=>{
 let content;const {page:p}=page('reader',{}, {showModal:o=>{content=o.content;o.success({confirm:false});}});
 p.data.aiSettings={personal_configured:true,trial_remaining:0};await p.generateAI();assert.match(content,/个人Key.*计费/);
});
test('hiding reader while AI requests pending prevents polling and stale result',async()=>{
 let resolveResult,resolveSettings;
 const {page:p,timers}=page('reader',{request:url=>new Promise(r=>url==='/ai/settings'?resolveSettings=r:resolveResult=r)});
 p.visible=true;p.taskId='id';p.data.text='original';const pending=p.loadAI();p.onHide();
 resolveResult({status:'running'});resolveSettings({trial_remaining:2});await pending;
 assert.equal(timers.length,0);assert.equal(p.data.aiStatus,'none');assert.equal(p.data.text,'original');assert.equal(p.visible,false);
});
test('readable 403 AI error does not replace original reading error',async()=>{
 const error=Object.assign(new Error('API 未获模型权限，请检查地域和模型开通'),{status:403});
 const {page:p,timers}=page('reader',{request:async()=>{throw error;}});p.visible=true;p.taskId='id';p.data.text='original';await p.loadAI();
 assert.match(p.data.aiError,/模型权限/);assert.equal(p.data.error,'');assert.equal(p.data.text,'original');
 assert.equal(timers.length,0,'permission failures must not automatically poll');
});
test('personal key input clears on hide and unload',()=>{
 const {page:p}=page('ai-settings',{});p.input({detail:{value:'fake-key'}});p.onHide();assert.equal(p.data.apiKey,'');p.input({detail:{value:'fake-key'}});p.onUnload();assert.equal(p.data.apiKey,'');
});
test('failed personal key save clears input and shows readable permission failure',async()=>{
 const {page:p}=page('ai-settings',{request:async()=>{throw Object.assign(new Error('检查地域和模型权限'),{status:403});}});
 p.data.apiKey='fake-key';await p.save();assert.equal(p.data.apiKey,'');assert.equal(p.data.saving,false);assert.match(p.data.error,/模型权限/);
});
test('successful personal save clears input and retains server quota',async()=>{
 let body;const {page:p}=page('ai-settings',{request:async(url,method,data)=>{body=data;return {personal_configured:true,trial_remaining:1};}});
 p.data.apiKey=' fake-key ';await p.save();assert.equal(body.api_key,'fake-key');assert.equal(p.data.apiKey,'');assert.equal(p.data.settings.trial_remaining,1);
});
test('original reader branch and quota instruction remain present',()=>{
 const html=fs.readFileSync(path.join(root,'pages/reader/reader.wxml'),'utf8');assert.match(html,/aiView === 'original'/);assert.match(html,/复制全文/);assert.match(html,/免费剩余/);assert.match(html,/配置个人API继续/);
});
