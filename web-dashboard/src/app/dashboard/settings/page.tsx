"use client";
import { useEffect, useState, type FormEvent } from "react";
import { KeyRound, Mic, Search, Save, ArrowUpRight } from "lucide-react";
import { getApplicationSettings, saveApplicationSettings } from "@/lib/api";

export default function SettingsPage() {
  const [loaded,setLoaded]=useState(false),[busy,setBusy]=useState(false);
  const [error,setError]=useState(""),[message,setMessage]=useState("");
  const [configured,setConfigured]=useState<Record<string,boolean>>({});
  const [voice,setVoice]=useState(""),[searchKey,setSearchKey]=useState(""),[searchSecret,setSearchSecret]=useState("");
  async function load(){
    setError("");
    try { const result=await getApplicationSettings();setConfigured(result.configured);setLoaded(true); }
    catch {setError("设置加载失败，请重试。");}
  }
  useEffect(()=>{void load();},[]);
  async function save(event:FormEvent){
    event.preventDefault();setBusy(true);setError("");setMessage("");
    try {
      const result=await saveApplicationSettings({llm_provider:"openai",llm_api_key:"",stt_engine:"elevenlabs",stt_api_key:voice,podcastindex_key:searchKey,podcastindex_secret:searchSecret});
      setConfigured(result.configured);setVoice("");setSearchKey("");setSearchSecret("");setMessage("个人配置已保存。");
    } catch(error) {setError(error instanceof Error?error.message:"保存失败，请重试。");}
    finally{setBusy(false);}
  }
  const field=(label:string,value:string,change:(value:string)=>void,configuredKey:string)=><label>{label}<input type="password" autoComplete="off" spellCheck={false} value={value} onChange={event=>change(event.target.value)} placeholder={configured[configuredKey]?"已配置，留空保留":"填写你自己的 Key"} disabled={!loaded||busy}/></label>;
  return <main className="personal-settings">
    <style>{`.personal-settings{max-width:850px;margin:0 auto;padding:32px 22px 64px;color:#352c25}.personal-settings h1{font-size:28px;font-weight:600}.personal-settings>p{margin:12px 0 28px;color:#756a5f}.personal-settings section{background:#fffdf8;border:1px solid #e4d8c9;border-radius:10px;padding:24px;margin:18px 0}.personal-settings h2{display:flex;gap:10px;align-items:center;font-size:18px}.personal-settings section p{margin:12px 0;color:#756a5f;font-size:14px;line-height:1.7}.personal-settings a{color:#986131;display:inline-flex;align-items:center;gap:8px}.personal-settings label{display:block;font-size:14px;margin-top:18px}.personal-settings input{display:block;width:100%;margin-top:8px;padding:12px;border:1px solid #ccbca9;border-radius:5px;background:white;color:#352c25}.personal-settings button{display:inline-flex;gap:8px;align-items:center;padding:12px 20px;border-radius:5px;background:#986131;color:white}.personal-settings button:disabled{opacity:.5}.personal-settings :is(input,button,a):focus-visible{outline:2px solid #986131;outline-offset:3px}.personal-settings .status{padding:12px 0;color:#56674c}.personal-settings .error{padding:12px 0;color:#a3372d}`}</style>
    <h1>个人服务设置</h1><p>配置自己的服务，整理自己的内容。</p>
    <section><h2><KeyRound size={20}/> AI 笔记模型</h2><p>默认百炼 qwen3.7-flash，每账号累计3次AI体验；已有个人 Key 时优先使用个人服务。用尽后可配置百炼（北京）、DeepSeek 或 OpenAI，查看剩余额度和处理中状态。规则分析、转写和查看缓存不扣AI次数。</p><a href="/account">管理我的 AI 模型 <ArrowUpRight size={16}/></a></section>
    <form onSubmit={save}>
      <section><h2><Mic size={20}/> 语音转写</h2><p>使用 ElevenLabs Scribe 转写音频，费用由你的服务账号承担。</p>{field("ElevenLabs API Key",voice,setVoice,"stt_api_key")}</section>
      <section><h2><Search size={20}/> 播客搜索</h2><p>搜索需要 PodcastIndex 配置。通过 RSS 或音频直链导入时可先跳过。</p>{field("PodcastIndex API Key",searchKey,setSearchKey,"podcastindex_key")}{field("PodcastIndex API Secret",searchSecret,setSearchSecret,"podcastindex_secret")}</section>
      <p className="status" role="status">{message||(!loaded&&!error?"正在加载个人配置…":"")}</p>
      {error&&<div className="error" role="alert">{error} {!loaded&&<button type="button" onClick={()=>void load()}>重新加载</button>}</div>}
      <button disabled={!loaded||busy} type="submit"><Save size={16}/>{busy?"保存中…":"保存个人配置"}</button>
    </form>
    <section><p>文件保存在你的独立工作空间，下载时由浏览器选择本机位置。</p><p>服务 Key 加密保存在服务器，不会显示在页面中；留空不会覆盖已有配置。</p></section>
  </main>;
}
