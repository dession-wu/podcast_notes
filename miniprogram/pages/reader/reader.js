const api = require('../../utils/api');
const ui = require('../../utils/presentation');
const labels={queued:'正在排队',downloading:'正在下载音频',transcribing:'正在转写',completed:'文字已就绪',failed:'处理失败'};
Page({
  data:{task:null,text:'',segments:[],hasSegments:false,query:'',matchCount:0,charCount:0,fontSize:32,error:'',loading:false,exporting:false,removing:false,demo:false,statusLabel:'',statusHint:'',createdLabel:'',expiresLabel:'',timingLabel:'',estimateLabel:'',aiView:'original',aiStatus:'none',aiResult:null,aiError:'',aiSettings:null,aiSubmitting:false},
  onLoad(options) { this.taskId=options.id; },
  onShow() { this.visible=true; this.requestGeneration=(this.requestGeneration || 0)+1; this.setData({loading:false}); const font=wx.getStorageSync('miniReaderFont'); if([28,32,36].includes(font)) this.setData({fontSize:font}); this.load(); },
  onHide() { this.visible=false; this.requestGeneration=(this.requestGeneration || 0)+1; clearTimeout(this.timer); clearTimeout(this.aiTimer); this.setData({loading:false}); },
  onUnload() { this.visible=false; this.requestGeneration=(this.requestGeneration || 0)+1; clearTimeout(this.timer); clearTimeout(this.aiTimer); this.setData({loading:false}); },
  async load() {
    if(this.visible===false || this.data.loading) return;
    const generation=this.requestGeneration || 0;
    clearTimeout(this.timer); this.setData({loading:true,error:''});
    try {
      const task=await api.request('/tasks/'+encodeURIComponent(this.taskId));
      const s=await api.session();
      if(!this.visible || generation!==(this.requestGeneration || 0)) return;
      this.setData({task,text:task.text || '',demo:s.demo,statusLabel:labels[task.status] || task.status,statusHint:ui.hints[task.status] || '',charCount:(task.text || '').replace(/\s/g,'').length,createdLabel:ui.date(task.created),expiresLabel:ui.date(Number(task.created)+ui.limits(s).retentionDays*86400),timingLabel:ui.timingSummary(task.timing),estimateLabel:ui.estimateSummary(task)});
      this.filter();
      if(task.status==='completed') this.loadAI();
    } catch(e) { if(this.visible && generation===(this.requestGeneration || 0)) { this.retryLoad=!e.status || e.status>=500 || e.status===429; this.setData({error:e.message+(this.retryLoad ? '；网络异常不会取消已提交任务，可稍后回来查看。' : '')}); } }
    finally {
      if(generation===(this.requestGeneration || 0)) {
        this.setData({loading:false});
        if(this.visible && (this.data.error ? this.retryLoad : (this.data.task && ui.active.includes(this.data.task.status)))) this.timer=setTimeout(()=>this.load(),5000);
      }
    }
  },
  aiSettings() { wx.navigateTo({url:'/pages/ai-settings/ai-settings'}); },
  selectAI(e) { this.setData({aiView:e.currentTarget.dataset.view}); },
  async loadAI() {
    if(!this.visible || this.aiLoading) return;
    this.aiLoading=true; this.aiRetry=false;
    const generation=this.requestGeneration || 0;
    clearTimeout(this.aiTimer);
    try {
      const [result,settings]=await Promise.all([api.request('/tasks/'+encodeURIComponent(this.taskId)+'/ai'),api.request('/ai/settings')]);
      if(!this.visible || generation!==(this.requestGeneration || 0)) return;
      this.setData({aiStatus:result.status || 'none',aiResult:result.result || null,aiError:result.error || '',aiSettings:settings});
    } catch(e) { if(this.visible && generation===(this.requestGeneration || 0)) { this.aiRetry=!e.status || e.status>=500 || e.status===429; this.setData({aiError:e.message}); } }
    finally {
      this.aiLoading=false;
      if(this.visible && generation===(this.requestGeneration || 0) && (this.data.aiError ? this.aiRetry : ['queued','running'].includes(this.data.aiStatus))) this.aiTimer=setTimeout(()=>this.loadAI(),5000);
      else if(this.visible && generation!==(this.requestGeneration || 0)) this.loadAI();
    }
  },
  async generateAI() {
    if(this.data.aiSubmitting || ['queued','running'].includes(this.data.aiStatus)) return;
    const s=this.data.aiSettings;
    if(s && !s.personal_configured && s.trial_remaining===0) return this.aiSettings();
    const answer=await new Promise(resolve=>wx.showModal({title:'生成AI精简版',content:'原文将发送至百炼，生成精简正文、摘要和核心观点。'+(s && s.personal_configured ? '使用你的个人Key并由你的账号计费。' : '成功消耗1次免费额度，失败不扣。')+'原文保持可阅读，AI结果请对照核验。',confirmText:'确认生成',success:resolve,fail:()=>resolve({confirm:false})}));
    if(!answer.confirm)return;
    this.setData({aiSubmitting:true,aiError:''});
    try {
      const result=await api.request('/tasks/'+encodeURIComponent(this.taskId)+'/ai','POST',{});
      this.setData({aiStatus:result.status,aiResult:result.result || null,aiError:result.error || ''});
      this.loadAI();
    } catch(e) { this.setData({aiError:e.message});if(e.status===402)this.aiSettings(); }
    finally { this.setData({aiSubmitting:false}); }
  },
  copyAI() {
    const r=this.data.aiResult;if(!r)return;
    const text=this.data.aiView==='condensed' ? r.condensed_text : r.summary+'\n\n'+r.key_points.map((p,i)=>(i+1)+'. '+p).join('\n');
    wx.setClipboardData({data:text,fail:()=>this.setData({aiError:'复制失败，请重试'})});
  },
  input(e) { this.setData({query:e.detail.value}); this.filter(); },
  clearFilter() { this.setData({query:''}); this.filter(); },
  setFont(e) { const font=Number(e.currentTarget.dataset.size); if(![28,32,36].includes(font)) return; wx.setStorageSync('miniReaderFont',font); this.setData({fontSize:font}); },
  filter() {
    if(!this.data.task) return;
    const q=this.data.query.trim().toLowerCase();
    const reading=ui.readableTranscript(this.data.task);
    const full=reading.text;
    if(reading.singleSpeaker) {
      const paragraphs=full.split(/\n\s*\n/).filter(Boolean);
      const matches=q ? paragraphs.filter(p=>p.toLowerCase().includes(q)) : paragraphs;
      this.setData({hasSegments:false,segments:[],text:matches.join('\n\n'),matchCount:q ? matches.length : 0,charCount:full.replace(/\s/g,'').length});
      return;
    }
    const segments=(this.data.task.segments || []).map((s,index)=>{
      const total=Math.max(0,Math.floor(Number(s.start_time) || 0));
      const pad=n=>String(n).padStart(2,'0');
      const time=(total>=3600 ? pad(Math.floor(total/3600))+':' : '')+pad(Math.floor(total/60)%60)+':'+pad(total%60);
      return {...s,index,time};
    });
    if(segments.length) {
      const visible=q ? segments.filter(s=>(s.text+' '+(s.speaker || '')+' '+s.time).toLowerCase().includes(q)) : segments;
      this.setData({hasSegments:true,segments:visible,text:full,matchCount:q ? visible.length : 0});
      return;
    }
    const matches=q ? full.split('\n').filter(line=>line.trim() && line.toLowerCase().includes(q)) : [];
    this.setData({hasSegments:false,segments:[],text:q ? matches.join('\n\n') : full,matchCount:matches.length});
  },
  copy() { wx.setClipboardData({data:ui.readableTranscript(this.data.task).text,fail:()=>this.setData({error:'复制失败，请重试'})}); },
  async export() {
    if(this.data.exporting) return;
    this.setData({exporting:true,error:''});
    try {
      let path=await api.download(this.taskId);
      const reading=ui.readableTranscript(this.data.task);
      if(reading.singleSpeaker) {
        path=wx.env.USER_DATA_PATH+'/podcast-'+encodeURIComponent(this.taskId)+'.txt';
        await new Promise((resolve,reject)=>wx.getFileSystemManager().writeFile({filePath:path,data:'\ufeff'+reading.text,encoding:'utf8',success:resolve,fail:()=>reject(new Error('文字文件保存失败，请重试'))}));
      }
      if(!wx.canIUse('shareFileMessage')) throw new Error('当前微信版本不支持文件分享，请升级微信或复制全文');
      await new Promise((resolve,reject)=>wx.shareFileMessage({filePath:path,fileName:'播客转文字.txt',success:resolve,fail:e=>reject(new Error(e.errMsg.includes('cancel')?'已取消分享':'分享失败，请重试'))}));
    } catch(e) { if(e.message==='已取消分享') wx.showToast({title:'已取消分享',icon:'none'}); else this.setData({error:e.message}); }
    finally { this.setData({exporting:false}); }
  },
  async remove() {
    if(this.data.removing) return;
    this.setData({removing:true});
    const choice=await new Promise(resolve=>wx.showModal({title:'删除这份文字？',content:'任务和文字将无法再查看，已导出的文件不受影响。',success:resolve,fail:()=>resolve({confirm:false})}));
    if(!choice.confirm) { this.setData({removing:false}); return; }
    try { await api.request('/tasks/'+encodeURIComponent(this.taskId),'DELETE'); wx.switchTab({url:'/pages/tasks/tasks'}); }
    catch(e) { this.setData({error:e.message}); }
    finally { this.setData({removing:false}); }
  },
  returnToTasks() { wx.switchTab({url:'/pages/tasks/tasks'}); },
  search() { wx.switchTab({url:'/pages/index/index'}); }
});

