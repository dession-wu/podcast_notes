const active = ['queued', 'downloading', 'transcribing'];
const labels = { queued:'排队中', downloading:'下载音频中', transcribing:'正在转写', completed:'文字已就绪', failed:'处理失败' };
const hints = { queued:'等待开始处理，可稍后回来查看', downloading:'正在获取音频，完成后开始转写', transcribing:'正在识别音频，长节目需要更多时间', completed:'打开阅读、复制或导出全文', failed:'打开记录查看原因和重试方式' };
function limits(session = {}) {
  const positive = (value, fallback) => Number.isFinite(Number(value)) && Number(value) > 0 ? Number(value) : fallback;
  return { dailyLimit:positive(session.daily_limit,3), maxMinutes:positive(session.max_minutes,120), retentionDays:positive(session.retention_days,7) };
}
function duration(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return '时长待检测';
  if (value < 60) return '不足 1 分钟';
  const minutes = Math.ceil(value / 60);
  return minutes < 60 ? `约 ${minutes} 分钟` : `约 ${Math.floor(minutes / 60)} 小时${minutes % 60 ? ' ' + minutes % 60 + ' 分钟' : ''}`;
}
function date(seconds) {
  if (!Number.isFinite(Number(seconds)) || Number(seconds) <= 0) return '';
  const d = new Date(Number(seconds) * 1000);
  const pad = v => String(v).padStart(2,'0');
  return `${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function elapsed(seconds) {
  if(!Number.isFinite(seconds) || seconds < 0) return '';
  if(seconds > 0 && seconds < 1) return '不足 1 秒';
  const total=Math.floor(seconds),hours=Math.floor(total/3600),minutes=Math.floor(total/60)%60,rest=total%60;
  return `${hours ? hours+' 小时 ' : ''}${minutes ? minutes+' 分 ' : ''}${rest} 秒`;
}
function timingSummary(timing) {
  if(!timing || !Number.isFinite(timing.elapsed_seconds)) return '';
  return [['总用时',timing.elapsed_seconds],['下载',timing.download_seconds],['转写',timing.transcription_seconds]]
    .filter(([,value])=>Number.isFinite(value) && value>=0).map(([label,value])=>label+' '+elapsed(value)).join(' · ');
}
function readableTranscript(task) {
  const segments = task.segments || [];
  const speakers = new Set(segments.map(s=>s.speaker).filter(Boolean));
  const singleSpeaker = segments.length > 0 && speakers.size <= 1;
  if (!singleSpeaker) return {singleSpeaker:false,text:task.text || ''};
  const paragraphs = [];
  let paragraph = '';
  for (const segment of segments) {
    const text = String(segment.text || '').trim();
    if (!text) continue;
    // Rejoin model chunks without inserting spaces into Chinese words.
    const separator = /[A-Za-z0-9]$/.test(paragraph) && /^[A-Za-z0-9]/.test(text) ? ' ' : '';
    paragraph += (paragraph ? separator : '') + text;
    // Paragraph breaks occur only after a complete sentence, never at a timestamp.
    if (paragraph.length >= 160 && /[。！？.!?][”’"'）)\]】]*$/.test(paragraph)) {
      paragraphs.push(paragraph); paragraph = '';
    }
  }
  if (paragraph) paragraphs.push(paragraph);
  return {singleSpeaker:true,text:paragraphs.join('\n\n')};
}
function estimateSummary(task) {
  if (!task || !active.includes(task.status)) return '';
  const estimate=task.estimate || {};
  const ahead=Number.isInteger(estimate.queue_ahead) && estimate.queue_ahead>0 ? `前方 ${estimate.queue_ahead} 个任务 · ` : '';
  if (estimate.overdue) return ahead+'处理时间超出预估，仍在继续';
  const low=estimate.remaining_lower_seconds, high=estimate.remaining_upper_seconds;
  if (typeof low!=='number' || typeof high!=='number' || !Number.isFinite(low) || !Number.isFinite(high) || low<0 || high<=0 || low>high) return ahead+'正在估算剩余时间';
  const lower=Math.max(1,Math.ceil(low/60)), upper=Math.max(lower,Math.ceil(high/60));
  const range=high<60 ? '不足 1 分钟' : `约 ${lower===upper ? upper : lower+'—'+upper} 分钟`;
  return ahead+'预计还需'+range+(estimate.basis==='initial' ? '（初步估算）' : '');
}
module.exports = { estimateSummary, active, labels, hints, limits, duration, date, elapsed, timingSummary, readableTranscript };
