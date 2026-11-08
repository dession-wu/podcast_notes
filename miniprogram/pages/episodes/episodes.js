const api = require('../../utils/api');
const ui = require('../../utils/presentation');
Page({
  data:{ title:'播客单集', episodes:[], viewEpisodes:[], query:'', page:0, hasMore:true, loading:false, submitting:false, submittingId:'', error:'', demo:false, dailyLimit:3, maxMinutes:120 },
  async onLoad(options) {
    this.feedId=options.id;
    try { const s=await api.request('/session'); this.setData({...ui.limits(s),demo:!!s.demo}); } catch (_) {}
    this.loadMore();
  },
  input(e) { this.setData({query:e.detail.value}); this.filter(); },
  clearFilter() { this.setData({query:''}); this.filter(); },
  filter() { const q=this.data.query.trim().toLowerCase(); this.setData({viewEpisodes:this.data.episodes.filter(ep=>!q || ep.title.toLowerCase().includes(q))}); },
  async loadMore() {
    if(this.data.loading || !this.data.hasMore) return;
    this.setData({loading:true,error:''});
    try {
      const page=this.data.page+1;
      const r=await api.request('/feeds/'+encodeURIComponent(this.feedId)+'/episodes?page='+page);
      const episodes=r.episodes.map(ep=>({...ep,durationLabel:ui.duration(ep.duration_seconds),tooLong:Number(ep.duration_seconds)>this.data.maxMinutes*60}));
      this.setData({title:r.title, episodes:this.data.episodes.concat(episodes), page, hasMore:r.has_more});
      this.filter();
    } catch(e) { this.setData({error:e.message}); }
    finally { this.setData({loading:false}); }
  },
  async submit(e) {
    if(this.data.submitting) return;
    const id=e.currentTarget.dataset.id;
    const ep=this.data.episodes.find(item=>item.id===id);
    if(ep && ep.tooLong) return this.setData({error:`这期节目超过 ${this.data.maxMinutes} 分钟，请选择较短单集`});
    this.setData({submitting:true,submittingId:id,error:''});
    const answer=await new Promise(resolve=>wx.showModal({title:'生成本期文字',content:`${ep ? ep.title+'\n\n' : ''}提交成功后，可切后台或关闭小程序，稍后在“我的文字”查看。
\n请确认你拥有处理该内容所需的权利或授权。结果仅本人可见。每天最多 ${this.data.dailyLimit} 次，单集最长 ${this.data.maxMinutes} 分钟；失败也计入当日额度。`,confirmText:'确认生成',success:resolve,fail:()=>{ this.setData({error:'无法打开确认窗口，请重试'}); resolve({confirm:false}); }}));
    if(!answer.confirm) { this.setData({submitting:false,submittingId:''}); return; }
    try {
      await api.request('/tasks','POST',{episode_id:id,rights_confirmed:true});
      wx.switchTab({url:'/pages/tasks/tasks'});
    } catch(e) { this.setData({error:e.message+'；若提交时网络中断，请先在“我的文字”确认是否已创建任务。'}); }
    finally { this.setData({submitting:false,submittingId:''}); }
  }
});
