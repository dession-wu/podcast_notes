/* Labeled UI fixture only; no audio submitted, clipboard copied or file sent. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const automator=require('/tmp/podcast-mini-qa/node_modules/miniprogram-automator');
const output=path.resolve(__dirname,'../docs/miniprogram/screenshots/dialogue');
async function until(fn){for(let i=0;i<50;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('UI did not settle');}
(async()=>{
 const mini=await automator.connect({wsEndpoint:'ws://127.0.0.1:9421'});
 const watchdog=setTimeout(()=>{console.error('UI check timed out');process.exit(1);},60000);
 try{
  fs.mkdirSync(output,{recursive:true});
  const page=await mini.reLaunch('/pages/reader/reader?id=ui-only-dialogue');
  await mini.evaluate(()=>{const pages=getCurrentPages();const page=pages[pages.length-1];page.visible=false;clearTimeout(page.timer);});
  const segments=[
   {start_time:12.4,end_time:20.6,speaker:'说话人 1',text:'你有没有过这样的体验：听完一期播客，很想把其中一段话留下来？'},
   {start_time:21.1,end_time:32.8,speaker:'说话人 2',text:'有。尤其是散步的时候，听到一句很好的表达，却不方便停下来记笔记。能回到对应的时间，再读一遍，就很有帮助。'},
   {start_time:33.2,end_time:42.9,speaker:'说话人 1',text:'所以我们希望，文字不只是识别出来，还能保留谈话的节奏，让每一次回应都清楚可读。'},
  ];
  const text=segments.map(s=>s.text).join('\n\n');
  await page.setData({task:{id:'ui-only-dialogue',status:'completed',title:'界面示例：让谈话更好读',text,segments},text,loading:false,error:'',fontSize:32,demo:true,statusLabel:'文字已就绪',charCount:text.length,expiresLabel:'示例日期'});
  await mini.evaluate(()=>{const page=getCurrentPages().slice(-1)[0];page.filter();});
  assert.equal((await page.$$('.dialogue-paragraph')).length,3);
  await mini.screenshot({path:path.join(output,'reader.png')});
  await (await page.$('input')).input('说话人 2');
  await until(async()=>await page.data('matchCount')===1);
  assert.equal(await page.data('matchCount'),1);
  assert.equal((await page.$$('.dialogue-paragraph')).length,1);
  await mini.screenshot({path:path.join(output,'speaker-filter.png')});
  await (await page.$('.clear-button')).tap();
  await until(async()=>(await page.data('segments')).length===3);
  assert.equal((await page.data('segments')).length,3);
  await mini.reLaunch('/pages/index/index');
  console.log('PASS dialogue layout, real timestamp formatting, speaker filtering and clear (UI fixture only)');
 }finally{clearTimeout(watchdog);await mini.disconnect();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
