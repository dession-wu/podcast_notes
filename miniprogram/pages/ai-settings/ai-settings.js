const api=require('../../utils/api');
Page({
 data:{settings:null,apiKey:'',regions:['中国内地（北京）','国际（新加坡）'],regionIndex:0,loading:false,saving:false,error:'',message:''},
 onShow(){this.load();},
 onHide(){this.setData({apiKey:''});},
 onUnload(){this.setData({apiKey:''});},
 async load(){if(this.data.loading)return;this.setData({loading:true,error:''});try{const settings=await api.request('/ai/settings');this.setData({settings,regionIndex:settings.region==='singapore'?1:0});}catch(e){this.setData({error:e.message});}finally{this.setData({loading:false});}},
 input(e){this.setData({apiKey:e.detail.value,message:''});},
 region(e){this.setData({regionIndex:Number(e.detail.value),message:''});},
 async save(){
  if(this.data.saving)return;
  const key=this.data.apiKey.trim();if(!key)return this.setData({error:'请输入自己的百炼 API Key'});
  this.setData({saving:true,error:'',message:''});
  try{const settings=await api.request('/ai/settings','PUT',{api_key:key,region:this.data.regionIndex===1?'singapore':'beijing'});this.setData({settings,apiKey:'',message:'验证通过，已加密保存。后续AI操作优先使用你的Key。'});}
  catch(e){this.setData({apiKey:'',error:e.message});}finally{this.setData({saving:false});}
 },
 async remove(){
  if(this.data.saving)return;
  const choice=await new Promise(resolve=>wx.showModal({title:'删除个人Key？',content:'不影响已有结果，也不会重置已使用的免费次数。',success:resolve,fail:()=>resolve({confirm:false})}));
  if(!choice.confirm)return;
  this.setData({saving:true,error:'',message:''});
  try{const settings=await api.request('/ai/settings','DELETE');this.setData({settings,apiKey:'',message:'个人Key已删除。'});}catch(e){this.setData({error:e.message});}finally{this.setData({saving:false});}
 },
 copyGuide(){wx.setClipboardData({data:'https://bailian.console.aliyun.com/'});}
});
