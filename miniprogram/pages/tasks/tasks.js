const api = require('../../utils/api');
const ui = require('../../utils/presentation');
Page({
  data:{tasks:[],viewTasks:[],filter:'all',activeCount:0,completedCount:0,failedCount:0,loading:false,error:'',demo:false,retentionDays:7},
  onShow() { this.visible=true; this.requestGeneration=(this.requestGeneration || 0)+1; this.setData({loading:false}); this.refresh(); },
  onHide() { this.visible=false; this.requestGeneration=(this.requestGeneration || 0)+1; clearTimeout(this.timer); this.setData({loading:false}); },
  onUnload() { this.visible=false; this.requestGeneration=(this.requestGeneration || 0)+1; clearTimeout(this.timer); this.setData({loading:false}); },
  selectFilter(e) { this.setData({filter:e.currentTarget.dataset.filter}); this.filterTasks(); },
  filterTasks() {
    const filter=this.data.filter, tasks=this.data.tasks;
    this.setData({activeCount:tasks.filter(t=>ui.active.includes(t.status)).length, completedCount:tasks.filter(t=>t.status==='completed').length, failedCount:tasks.filter(t=>t.status==='failed').length, viewTasks:tasks.filter(t=>filter==='all' || (filter==='active' ? ui.active.includes(t.status) : t.status===filter))});
  },
  async refresh() {
    clearTimeout(this.timer);
    if(this.visible===false || this.data.loading) return;
    const generation=this.requestGeneration || 0;
    this.setData({loading:true,error:''});
    try {
      const r=await api.request('/tasks'); const s=await api.session();
      if(!this.visible || generation!==(this.requestGeneration || 0)) return;
      this.setData({tasks:r.tasks.map(t=>({...t,label:ui.labels[t.status] || t.status,hint:ui.hints[t.status] || '',createdLabel:ui.date(t.created),timingLabel:ui.timingSummary(t.timing),estimateLabel:ui.estimateSummary(t)})),demo:s.demo,...ui.limits(s)});
      this.filterTasks();
    } catch(e) { if(this.visible && generation===(this.requestGeneration || 0)) { this.retryLoad=!e.status || e.status>=500 || e.status===429; this.setData({error:e.message+(this.retryLoad ? '；网络异常不会取消已提交任务，可稍后回来查看。' : '')}); } }
    finally {
      if(generation!==(this.requestGeneration || 0)) return;
      this.setData({loading:false});
      if(this.visible && ((this.data.error ? this.retryLoad : this.data.tasks.some(t=>ui.active.includes(t.status))))) this.timer=setTimeout(()=>this.refresh(),5000);
    }
  },
  open(e) { wx.navigateTo({url:'/pages/reader/reader?id='+encodeURIComponent(e.currentTarget.dataset.id)}); },
  search() { wx.switchTab({url:'/pages/index/index'}); }
});

