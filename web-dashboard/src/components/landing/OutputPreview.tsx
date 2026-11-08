"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { FileText, Headphones, ImageIcon, List, Quote } from "lucide-react";
import styles from "./landing.module.css";

const tabs = ["结构化笔记", "时间戳转录", "图文素材"] as const;

export default function OutputPreview() {
  const [selected, setSelected] = useState(0);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    setSelected(next);
    buttons.current[next]?.focus();
  }

  return (
    <div className={styles.preview}>
      <div className={styles.previewHeader}>
        <span><Headphones size={16} aria-hidden="true" /> 一期播客里的好想法</span>
        <span className={styles.exampleLabel}>内容示意</span>
      </div>
      <div className={styles.audioStrip} aria-hidden="true">
        <div className={styles.audioIcon}><Headphones size={19} /></div>
        <div><strong>把好奇心，变成持续学习的动力</strong><span>从一段音频，开始一次整理</span></div>
      </div>
      <div className={styles.previewTabs} role="tablist" aria-label="查看输出示例">
        {tabs.map((label, index) => (
          <button key={label} ref={(element) => { buttons.current[index] = element; }} type="button"
            role="tab" id={`preview-tab-${index}`} aria-selected={selected === index}
            aria-controls={`preview-panel-${index}`} tabIndex={selected === index ? 0 : -1}
            onKeyDown={(event) => navigate(event, index)} onClick={() => setSelected(index)}>{label}</button>
        ))}
      </div>
      <div className={styles.previewBody} id={`preview-panel-${selected}`} role="tabpanel"
        aria-labelledby={`preview-tab-${selected}`} tabIndex={0}>
        {selected === 0 ? <>
          <div className={styles.documentLabel}><List size={13} aria-hidden="true" /> 核心观点</div>
          <h3>让输入，真正成为自己的知识。</h3>
          <p>比起记住每一句话，更值得留下的是：一个观点、它的理由，以及它与你的联系。</p>
          <ol className={styles.notePoints}>
            <li><span>01</span><div><strong>先理解，再记录</strong><p>从谈话中提取问题、观点和解释。</p></div></li>
            <li><span>02</span><div><strong>留下自己的思考</strong><p>把听到的启发，连接到具体的行动。</p></div></li>
          </ol>
          <div className={styles.quote}><Quote size={16} aria-hidden="true" /><p>值得收藏的，不只是信息，还有思考的线索。</p></div>
        </> : selected === 1 ? <>
          <div className={styles.documentLabel}><FileText size={13} aria-hidden="true" /> 转录全文 · 时间戳示意</div>
          <h3>好想法，也能回到谈话现场。</h3>
          <div className={styles.transcript}><span>00:18</span><p>我们每天听到很多东西，但听过和真正理解，其实是两件事。</p></div>
          <div className={styles.transcript}><span>01:42</span><p>可以先问自己：这一段到底在回答什么问题？把问题记下来，再整理它的观点。</p></div>
          <div className={styles.transcript}><span>03:06</span><p>下次遇到相关问题，就能找到当时的讨论，而不只是模糊地记得听过。</p></div>
        </> : <>
          <div className={styles.documentLabel}><ImageIcon size={13} aria-hidden="true" /> 图文输出示意</div>
          <div className={styles.miniCover}><span>PODCAST NOTES</span><h3>好内容，<br />值得再读一次。</h3><div /><p>核心观点 / 内容提炼 / 我的思考</p></div>
          <p className={styles.previewHint}>可将整理后的内容生成图文素材，核对后下载使用。</p>
        </>}
      </div>
      <div className={styles.previewFoot}><span>示例文案，非真实播客转录</span><span>AI 整理 · 人工核对</span></div>
    </div>
  );
}
