const api = require('../../utils/api');
Page({
  data: { query:'', searchedTerm:'', results:[], recent:[], loading:false, searched:false, error:'', demo:false, development:false },
  async onLoad() {
    try {
      const saved = wx.getStorageSync('miniRecentSearches');
      this.setData({recent:Array.isArray(saved) ? saved.filter(q=>typeof q==='string' && q.trim()).slice(0,6) : []});
      const s = await api.request('/session'); this.setData({ demo:s.demo, development:require('../../config').developmentLogin });
    }
    catch(e) { this.setData({ error:e.message }); }
  },
  input(e) { this.setData({ query:e.detail.value }); },
  clear() { if (!this.data.loading) this.setData({query:'',searchedTerm:'',searched:false,results:[],error:''}); },
  useRecent(e) { if(this.data.loading) return; this.setData({query:e.currentTarget.dataset.query}); this.search(); },
  clearRecent() { wx.removeStorageSync('miniRecentSearches'); this.setData({recent:[]}); },
  async search() {
    if (this.data.loading) return;
    const term=this.data.query.trim();
    if (!term) return this.setData({ error:'请输入播客名称' });
    this.setData({ query:term, searchedTerm:term, loading:true, error:'', results:[], searched:true });
    try {
      const result = await api.request('/search?q=' + encodeURIComponent(term)); const session = await api.session();
      const recent=[term,...this.data.recent.filter(q=>q!==term)].slice(0,6);
      wx.setStorageSync('miniRecentSearches',recent);
      this.setData({ results:result.results, demo:session.demo, recent });
    }
    catch(e) { this.setData({ error:e.message }); }
    finally { this.setData({ loading:false }); }
  },
  open(e) { wx.navigateTo({ url:'/pages/episodes/episodes?id=' + encodeURIComponent(e.currentTarget.dataset.id) }); },
  aiSettings() { wx.navigateTo({url:'/pages/ai-settings/ai-settings'}); },
  privacy() {
    wx.showModal({ title:'隐私与使用说明', content:'仅使用账号标识区分你的任务，使用AI提炼时原文会发送至百炼处理，个人API Key在服务器加密保存，平台AI免费额度按账号累计3次，不索取手机号、头像或昵称。任务默认保留7天，可在阅读页删除，以页面实际保留天数为准。最近搜索和字号偏好仅保存在本机。复制与导出均包含全文，请妥善保管文件。请仅处理有权使用的内容。当前本地开发版尚未正式发布，运营主体、联系方式和处理方式需上线前定稿。', showCancel:false });
  }
});
