import type { Metadata } from "next";
import Image from "next/image";

import { ArrowDown, ArrowRight, AudioLines, BookOpen, Check, FileText, Headphones, Mic, PenLine } from "lucide-react";
import OutputPreview from "@/components/landing/OutputPreview";
import styles from "@/components/landing/landing.module.css";

export const metadata: Metadata = {
  title: "播客手账 · 让听过的好内容留下来",
  description: "为播客听众、知识整理者和内容创作者，将播客音频整理成带时间戳的转录、结构化笔记和图文素材。AI 出草稿，你来核对与表达。",
};

const audiences = [
  { icon: Headphones, title: "给认真听播客的你", description: "听到有启发的内容，留下全文和观点笔记。想起一个话题时，有据可查。", result: "从「听过」到「留下来」" },
  { icon: BookOpen, title: "给习惯整理知识的你", description: "把长对话拆成清晰的主题、要点和思考，让零散输入成为可回看的资料。", result: "从零散信息到知识线索" },
  { icon: PenLine, title: "给持续创作内容的你", description: "从播客中寻找选题与表达素材，用文字和图文模板整理草稿，再加入自己的判断。", result: "从内容素材到创作起点" },
];

const steps = [
  { number: "01", title: "找到一段值得留下的声音", description: "搜索播客、通过 RSS 或音频直链获取素材，也可以从已有音频开始。", detail: "音频与素材库" },
  { number: "02", title: "把长对话，整理成清晰的内容", description: "先完成语音转写，再按内容选择笔记模板，提炼观点、关键内容与思考线索。", detail: "转录与 AI 笔记" },
  { number: "03", title: "核对之后，留下你的表达", description: "对照转录阅读、校对笔记，下载文字或图文素材，供后续学习与创作使用。", detail: "核对与下载" },
];

const examples = [
  { image: "minimal-content.png", name: "极简知识感", description: "让观点和重点，成为阅读的主角。", alt: "原项目极简模板示例：白底、琥珀色重点和条目化观点" },
  { image: "vibrant-content.png", name: "活力社交感", description: "更鲜明的色彩，更轻松的阅读节奏。", alt: "原项目活力模板示例：粉紫色调的观点图文" },
  { image: "editorial-cover.png", name: "高级杂志感", description: "用克制的排版，呈现值得深读的主题。", alt: "原项目杂志模板示例：大标题、网格和红色点缀的封面" },
];

const questions = [
  { title: "它更适合用来学习，还是创作内容？", answer: "两者都可以。播客听众可以保留可检索的转录和笔记；知识整理者可以提炼观点与思考；内容创作者可以将它作为选题和图文草稿的整理工具。最终如何取舍和表达，由你决定。" },
  { title: "我会得到哪些形式的内容？", answer: "项目提供转录阅读、文字笔记和图文生成能力。文字内容可按功能导出为 TXT、Markdown 或 JSON，图文可下载为 PNG；部分下载流程支持 ZIP 打包。具体输出取决于所选模板与处理结果。" },
  { title: "生成的笔记，可以直接发布吗？", answer: "建议先核对。语音识别可能出现错字，AI 提炼也可能遗漏上下文。请对照原文校对，补充自己的表达，并确认原播客与素材的使用授权、注明来源后再分享。这里不承诺自动发布或内容完全准确。" },
  { title: "开始使用前，需要准备什么？", answer: "注册个人账号后，配置自己的 DeepSeek 或 OpenAI Key。音频转写还需 ElevenLabs Key；播客搜索可选配 PodcastIndex。也可以通过 RSS 或音频直链导入，处理完成后核对并下载。" },
];

export default function LandingPage() {
  return (
    <div className={styles.landing}>
      <a href="#main" className={styles.skip}>跳到主要内容</a>
      <header className={`${styles.header} ${styles.container}`}>
        <a href="/" className={styles.brand} aria-label="播客手账首页"><img src="/brand/icon.svg?v=20261103-brand1" width={34} height={34} alt="" className={styles.brandIcon} /><span>播客手账<small>PODCAST JOURNAL</small></span></a>
        <nav aria-label="首页导航" className={styles.navigation}><a href="#features">适合谁用</a><a href="#workflow">如何使用</a><a href="#examples">输出示例</a></nav>
        <a href="/login" className={styles.headerLogin}>登录 <ArrowRight size={15} aria-hidden="true" /></a>
      </header>

      <main id="main">
        <section className={`${styles.hero} ${styles.container}`} aria-labelledby="hero-title">
          <div className={styles.heroCopy}>
            <h1 id="hero-title">好内容，值得留下。</h1>
            <p className={styles.heroDescription}>把播客里的声音，整理成可检索的转录、可回看的笔记，和可二次创作的图文素材。</p>
            <div className={styles.heroActions}><a href="/register" className={styles.primary}>注册，开始整理 <ArrowRight size={17} aria-hidden="true" /></a><a href="#workflow" className={styles.secondary}>了解使用流程 <ArrowDown size={15} aria-hidden="true" /></a></div>
            <p className={styles.heroNote}>AI 帮你整理草稿，内容由你核对与定稿。</p>
            <div className={styles.inputOutput}><AudioLines size={18} aria-hidden="true" /><span>一段音频</span><ArrowRight size={14} aria-hidden="true" /><span>转录 · 笔记 · 图文</span></div>
          </div>
          <OutputPreview />
        </section>

        <section id="features" className={`${styles.section} ${styles.container}`} aria-labelledby="audience-title">
          <div className={styles.sectionHeading}><h2 id="audience-title">听完之后，留下自己的思考。</h2><p>无论是留给自己，还是整理后分享，从一段值得回味的内容开始。</p></div>
          <div className={styles.audiences}>{audiences.map(({ icon: Icon, title, description, result }) => <article key={title}><Icon size={24} strokeWidth={1.5} aria-hidden="true" /><h3>{title}</h3><p>{description}</p><span>{result}</span></article>)}</div>
        </section>

        <section id="workflow" className={styles.workflow} aria-labelledby="workflow-title"><div className={styles.container}>
          <div className={styles.sectionHeading}><h2 id="workflow-title">从声音到笔记，理清每个好想法。</h2><p>转写、提炼、核对与导出，围绕同一份内容，逐步完成。</p></div>
          <ol className={styles.steps}>{steps.map(step => <li key={step.number}><span className={styles.stepNumber}>{step.number}</span><h3>{step.title}</h3><p>{step.description}</p><span className={styles.stepDetail}><Check size={14} aria-hidden="true" />{step.detail}</span></li>)}</ol>
        </div></section>

        <section id="examples" className={`${styles.section} ${styles.container}`} aria-labelledby="examples-title">
          <div className={styles.sectionHeading}><h2 id="examples-title">让好内容，清晰呈现。</h2><p>文字笔记之外，也能整理成适合分享的图文。以下为项目自带的模板示例，点击可查看大图。</p></div>
          <div className={styles.gallery}>{examples.map(example => <figure key={example.name}><a className={styles.imageLink} href={`/landing/${example.image}`} target="_blank" rel="noopener noreferrer" aria-label={`查看${example.name}模板大图（新窗口）`}><picture><source srcSet={`/landing/${example.image}.webp`} type="image/webp" /><Image src={`/landing/${example.image}`} alt={example.alt} width={900} height={1200} sizes="(max-width: 640px) 85vw, (max-width: 1000px) 44vw, 350px" unoptimized /></picture></a><figcaption><h3>{example.name}</h3><p>{example.description}</p></figcaption></figure>)}</div>
          <div className={styles.exportNote}><FileText size={17} aria-hidden="true" /><p>保留可编辑的文字，也保留方便分享的图片。<span>文字导出 / PNG 图文 / 部分流程支持 ZIP 打包</span></p></div>
        </section>

        <section className={`${styles.faqSection} ${styles.container}`} aria-labelledby="faq-title"><div><h2 id="faq-title">开始之前，你可能想知道。</h2><p>工具负责辅助整理，内容判断始终在你手中。</p></div><div className={styles.questions}>{questions.map(question => <details key={question.title}><summary>{question.title}<span aria-hidden="true">+</span></summary><p>{question.answer}</p></details>)}</div></section>

        <section className={`${styles.closing} ${styles.container}`} aria-labelledby="closing-title"><AudioLines size={34} strokeWidth={1.4} aria-hidden="true" /><h2 id="closing-title">下一期播客，留下一份好笔记。</h2><p>留下观点，整理思路，再用自己的方式表达。</p><a href="/register" className={styles.primary}>注册，创建第一份笔记 <ArrowRight size={17} aria-hidden="true" /></a></section>
      </main>

      <footer className={`${styles.footer} ${styles.container}`}><div className={styles.footerBrand}><img src="/brand/icon.svg?v=20261103-brand1" width={24} height={24} alt="" />播客手账<span>听见，理解，留下。</span></div><div><a href="#workflow">使用流程</a><a href="#examples">模板示例</a><a href="/login">进入控制台</a></div><small>© 2026 播客手账</small></footer>
    </div>
  );
}

