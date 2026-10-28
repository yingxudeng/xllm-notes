from __future__ import annotations

import base64
import difflib
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown
from lxml import etree
from lxml import html as html_parser


REPORT_ROOT = Path(__file__).resolve().parent
NOTES_ROOT = REPORT_ROOT.parents[1]
SOURCE_ROOT = NOTES_ROOT.parent / "xllm-main-cann9-20260911-linear-prefix-cache"
DOCUMENT_ROOT = NOTES_ROOT.parent / "knowledge/20261028_xllm_linear_prefix_cache_pr"
ORIGINAL_COMMIT = "efd1692a3662b654167bc92a5a9cb070a56ec873"
VALIDATION_ROOT = SOURCE_ROOT / (
    ".cann9-20260911-build-runs/"
    "20261028T073858Z-dp-plan-rank-block-zrWZjn"
)
CHAPTERS = [
    ("invalidation", "两个 reset 的必要性", REPORT_ROOT / "invalidation.md"),
    ("overview", "先建立整体认识", DOCUMENT_ROOT / "README.md"),
    ("scope", "PR 差异范围", DOCUMENT_ROOT / "01_diff_scope.md"),
    ("classes", "类关系与所有权", DOCUMENT_ROOT / "02_classes_and_ownership.md"),
    ("calls", "调用链与状态时序", DOCUMENT_ROOT / "03_calls_and_lifecycle.md"),
    ("review", "提 PR 前自查", DOCUMENT_ROOT / "04_pr_checklist.md"),
]

STYLE = r"""
:root{--bg:#eceff4;--surface:#fff;--ink:#1b2130;--muted:#5a6478;--line:#d6dbe6;--indigo:#3b4bd8;--deep:#232a52;--terra:#c1583b;--green:#17664b;--code:#f5f6f8}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:130px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.8 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif}
a{color:var(--indigo);text-decoration:none}a:hover{text-decoration:underline}button,select,input{font:inherit}button{cursor:pointer}a:focus-visible,button:focus-visible,summary:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--terra);outline-offset:3px}
h1,h2,h3,h4,.brand{font-family:Georgia,"Times New Roman","Songti SC","SimSun",serif}h1{font-size:clamp(30px,4vw,46px);line-height:1.2;margin:12px 0 18px;color:var(--deep)}h2{font-size:27px;line-height:1.4;margin:0 0 20px;color:var(--deep)}h3{font-size:23px;line-height:1.4;margin:42px 0 14px;color:var(--terra)}h4{font-size:19px;line-height:1.5;margin:26px 0 12px;color:var(--deep)}
.skip-link{position:fixed;top:-100px;left:16px;z-index:100;background:white;padding:12px}.skip-link:focus{top:12px}.topbar{background:var(--deep);border-bottom:3px solid var(--terra);position:sticky;top:0;z-index:20}.topbar-inner{max-width:1160px;margin:auto;padding:12px 24px;display:flex;gap:18px;align-items:center}.brand{color:#fff;font-size:18px;font-weight:700}.topbar .crumb{color:#c8cde0;font-size:13px}.page{max-width:1160px;padding:0 24px 64px;margin:auto}.intro{padding:34px 0 28px;border-bottom:2px solid var(--deep)}.eyebrow{color:var(--terra);font-size:12px;font-weight:700;letter-spacing:.12em}.subtitle{font-size:18px;color:var(--muted);max-width:920px;margin:0}.meta{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 0}.tag{font-size:13px;background:white;border:1px solid var(--line);padding:3px 10px;border-radius:2px;overflow-wrap:anywhere}.tag.good{color:var(--green);border-color:#a6cdbc;background:#f0f8f3}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.action{background:white;border:1px solid var(--line);padding:7px 12px;border-radius:3px;color:var(--deep);font-weight:600;font-size:14px}.action.primary{background:var(--deep);border-color:var(--deep);color:white}.notice{border-left:4px solid var(--terra);background:#fff8f2;padding:15px 20px;margin:20px 0;color:#553828}.notice p{margin:0}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:24px 0 0;border:1px solid var(--line);background:white}.metric{padding:12px 18px;border-right:1px solid var(--line)}.metric:last-child{border:0}.metric strong{display:block;font-size:26px;line-height:1.2;font-family:Georgia,serif;color:var(--deep)}.metric span{font-size:12px;color:var(--muted)}
.toc{position:sticky;top:59px;z-index:15;display:flex;gap:5px;overflow-x:auto;background:var(--bg);border:1px solid var(--line);padding:9px;margin:20px 0;white-space:nowrap}.toc a{font-size:13px;font-weight:600;color:var(--muted);padding:5px 9px}.toc a:hover,.toc a[aria-current=true]{background:var(--deep);color:white;text-decoration:none}.chapter{padding:30px 34px;margin:22px 0;background:white;border:1px solid var(--line);border-left:4px solid var(--indigo);border-radius:3px;min-width:0}.chapter:first-child{border-left-color:var(--terra)}.chapter-label{font-size:12px;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;display:block;margin-bottom:9px}.section-index{background:#f7f8fb;padding:12px 17px;margin:16px 0 24px;border:1px solid var(--line);font-size:14px}.section-index summary{cursor:pointer;font-weight:600;color:var(--deep)}.section-index ol{columns:2;column-gap:30px;margin:10px 0 0;padding-left:22px}.section-index li{break-inside:avoid;margin:4px 0}.back-top{display:block;text-align:right;font-size:13px;margin-top:26px}.chapter p,.chapter li{overflow-wrap:anywhere}.chapter p{margin:12px 0}.chapter ul,.chapter ol{padding-left:24px}.chapter li{margin:5px 0}.chapter strong{font-weight:700}blockquote{margin:18px 0;padding:10px 18px;border-left:3px solid var(--line);background:#f7f8fa;color:var(--muted)}blockquote p{margin:5px 0!important}hr{border:0;border-top:1px solid var(--line);margin:28px 0}
code,pre,.source-location{font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace}code{font-size:.87em;background:#f0f2f6;border:1px solid #e1e5ed;border-radius:3px;padding:1px 4px;overflow-wrap:anywhere}pre{background:var(--code);color:#24304a;border:1px solid #dde2ec;padding:17px 19px;overflow:auto;font-size:13px;line-height:1.7;tab-size:2;max-width:100%}pre code{background:none;border:0;padding:0;font-size:inherit;white-space:pre;overflow-wrap:normal}.table-wrap{overflow:auto;max-width:100%;margin:18px 0;border:1px solid var(--line);border-radius:2px}table{border-collapse:collapse;font-size:14px;line-height:1.65;width:100%;min-width:540px}th{text-align:left;background:#f0f2f7;color:var(--deep);font-weight:700}th,td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}td{overflow-wrap:anywhere}tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#fbfcfe}table code{font-size:12px}.figure{margin:26px 0;border:1px solid var(--line);padding:12px;background:white;break-inside:avoid}.figure-open{display:block;width:100%;padding:0;border:0;background:white}.figure-open img{display:block;width:100%;height:auto}.figure figcaption{border-top:1px solid var(--line);margin-top:12px;padding-top:9px;color:var(--muted);font-size:13px}.figure-hint{color:var(--indigo);font-weight:600;margin-left:8px}.source-link{border-bottom:1px dotted #a2acc3}#figures ul{columns:2;column-gap:30px}.footer{color:var(--muted);font-size:13px;margin-top:28px;border-top:1px solid var(--line);padding-top:20px}
dialog{padding:0;border:1px solid var(--line);border-radius:4px;width:min(1440px,calc(100vw - 36px));max-width:none;height:calc(100vh - 40px);max-height:none;background:white;color:var(--ink)}dialog::backdrop{background:rgba(17,24,42,.76)}.dialog-header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px 18px;background:var(--deep);color:white}.dialog-header h2{font:600 15px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:white;margin:0;overflow-wrap:anywhere}.dialog-header button{border:1px solid #8b94ae;background:transparent;color:white;padding:5px 11px;border-radius:2px;font-size:14px}.dialog-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 18px;border-bottom:1px solid var(--line);background:#f7f8fb;font-size:13px}.dialog-tools button{padding:5px 10px;background:white;border:1px solid var(--line);color:var(--deep);border-radius:2px}.diagram-scroll{height:calc(100% - 126px);overflow:auto;background:#f0f2f6;padding:16px}.diagram-scroll img{display:block;background:white;max-width:none;height:auto;margin:0 auto}.source-tools select{min-width:160px;max-width:70%;flex:1;padding:5px;border:1px solid var(--line);background:white}.source-tools input{width:86px;padding:5px;border:1px solid var(--line)}.source-location{font-size:12px;color:var(--muted);overflow-wrap:anywhere;padding:6px 18px;background:#fafbfc;border-bottom:1px solid var(--line)}.source-scroll{height:calc(100% - 158px);overflow:auto;background:white;font-size:12px;line-height:1.7}.source-lines{margin:0;padding:12px 0 30px;counter-reset:line;min-width:max-content;list-style:none}.source-lines li{display:flex;white-space:pre;min-height:20px;counter-increment:line}.source-lines li::before{content:counter(line);display:inline-block;flex:0 0 64px;width:64px;padding:0 12px;text-align:right;color:#7c8698;background:#f5f6f9;border-right:1px solid var(--line);user-select:none}.source-lines code{background:none;border:0;font-size:12px;padding:0 18px;white-space:pre;overflow-wrap:normal}.source-lines .selected{background:#fff1cf}.source-lines .selected::before{background:#ffe7ad;color:#563610}.empty-state{padding:20px;color:var(--muted)}
@media(max-width:740px){body{font-size:15px}.page{padding:0 14px 44px}.topbar-inner{padding:11px 14px}.topbar .crumb{display:none}.intro{padding-top:24px}h1{font-size:31px}h2{font-size:24px}h3{font-size:21px}.subtitle{font-size:16px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.metric:nth-child(2){border-right:0}.metric:nth-child(-n+2){border-bottom:1px solid var(--line)}.metric{padding:11px 14px}.toc{top:56px}.chapter{padding:23px 18px}.section-index ol,#figures ul{columns:1}.figure{padding:5px;margin-left:-8px;margin-right:-8px}pre{font-size:12px;padding:13px}.source-tools select{max-width:100%;flex-basis:100%}.source-scroll{height:calc(100% - 197px)}dialog{width:calc(100vw - 16px);height:calc(100vh - 16px)}.dialog-tools{gap:7px;padding:9px}.dialog-header{padding:11px}.source-lines code{padding:0 10px}.source-lines li::before{flex-basis:48px;width:48px;padding:0 8px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{@page{size:A4;margin:15mm}body{background:white;font-size:10pt;line-height:1.55}.topbar,.toc,.actions,.back-top,.section-index,.figure-hint,dialog,.skip-link{display:none!important}.page{max-width:none;padding:0}.intro{padding:0 0 15px}.chapter{border:0;border-top:1px solid #bbc1ce;margin:18px 0;padding:18px 0}.chapter-label{font-size:9pt}h1{font-size:25pt}h2{font-size:19pt}h3{font-size:15pt;break-after:avoid}h4{font-size:12pt;break-after:avoid}.subtitle{font-size:12pt}.metrics{margin-top:16px}.metric strong{font-size:20pt}.figure{break-inside:avoid;padding:5px}.figure-open img{max-height:225mm;object-fit:contain}.table-wrap{overflow:visible;border:0}table{min-width:0;font-size:9pt}thead{display:table-header-group}tr{break-inside:avoid}th,td{padding:6px}pre{font-size:8pt;white-space:pre-wrap;overflow:visible;break-inside:auto}pre code{white-space:pre-wrap;overflow-wrap:anywhere}code{font-size:8.5pt}.notice{padding:10px 13px}a{color:inherit;text-decoration:none}.source-link{border:0}}
@media print{.metrics{display:table;width:100%;table-layout:fixed}.metric{display:table-cell;width:25%;vertical-align:top;padding:10px 12px}.metric strong{font-size:18pt;white-space:nowrap}.metric span{display:block;font-size:8pt;line-height:1.5;margin-top:5px}h2 code,h3 code,h4 code{font-size:.83em}}
"""

SCRIPT = r"""
const sourceData = JSON.parse(document.getElementById('source-data').textContent);
const sourceDialog = document.getElementById('source-dialog');
const sourceSelect = document.getElementById('source-select');
const sourceLineInput = document.getElementById('source-line-input');
const sourceLocation = document.getElementById('source-location');
const sourceLines = document.getElementById('source-lines');
let renderedSource = '';
for (const sourceKey of Object.keys(sourceData).sort()) {
  const option = document.createElement('option');
  option.value = sourceKey;
  option.textContent = sourceKey;
  sourceSelect.append(option);
}
function renderSource(sourceKey, requestedLine = 1) {
  if (!Object.hasOwn(sourceData, sourceKey)) return;
  const lines = sourceData[sourceKey].split('\n');
  const lineNumber = Math.max(1, Math.min(lines.length, Number(requestedLine) || 1));
  sourceSelect.value = sourceKey;
  sourceLineInput.max = String(lines.length);
  sourceLineInput.value = String(lineNumber);
  sourceLocation.textContent = `${sourceKey}:${lineNumber} · 提交 {{HEAD_SHORT}} 的源码快照 / 本页构建证据`;
  if (renderedSource !== sourceKey) {
    const fragment = document.createDocumentFragment();
    for (const line of lines) {
      const item = document.createElement('li');
      const code = document.createElement('code');
      code.textContent = line || ' ';
      item.append(code);
      fragment.append(item);
    }
    sourceLines.replaceChildren(fragment);
    renderedSource = sourceKey;
  }
  sourceLines.querySelector('.selected')?.classList.remove('selected');
  const selected = sourceLines.children[lineNumber - 1];
  selected?.classList.add('selected');
  if (!sourceDialog.open) sourceDialog.showModal();
  requestAnimationFrame(() => selected?.scrollIntoView({block:'center',inline:'start'}));
}
document.addEventListener('click', event => {
  const link = event.target.closest('[data-source]');
  if (!link) return;
  event.preventDefault();
  renderSource(link.dataset.source, link.dataset.line || 1);
});
sourceSelect.addEventListener('change', () => renderSource(sourceSelect.value, 1));
document.getElementById('source-go').addEventListener('click', () => renderSource(sourceSelect.value, sourceLineInput.value));
sourceLineInput.addEventListener('keydown', event => {
  if (event.key === 'Enter') renderSource(sourceSelect.value, sourceLineInput.value);
});
const figureDialog = document.getElementById('figure-dialog');
const figureImage = document.getElementById('figure-image');
const figureViewport = document.getElementById('figure-viewport');
const figureScale = document.getElementById('figure-scale');
let scale = 1;
function setFigureScale(nextScale) {
  scale = Math.min(5, Math.max(.15, nextScale));
  figureImage.style.width = `${figureImage.naturalWidth * scale}px`;
  figureScale.textContent = `${Math.round(scale * 100)}%`;
}
function fitFigure() {
  setFigureScale(Math.min(1, (figureViewport.clientWidth - 32) / figureImage.naturalWidth));
}
document.querySelectorAll('.figure-open').forEach(trigger => {
  trigger.addEventListener('click', event => {
    event.preventDefault();
    const image = trigger.querySelector('img');
    document.getElementById('figure-title').textContent = image.alt;
    figureImage.alt = image.alt;
    figureImage.onload = fitFigure;
    figureImage.src = image.src;
    figureDialog.showModal();
    if (figureImage.complete && figureImage.naturalWidth) fitFigure();
  });
});
document.getElementById('figure-in').addEventListener('click', () => setFigureScale(scale * 1.25));
document.getElementById('figure-out').addEventListener('click', () => setFigureScale(scale / 1.25));
document.getElementById('figure-fit').addEventListener('click', fitFigure);
document.getElementById('figure-original').addEventListener('click', () => setFigureScale(1));
document.querySelectorAll('[data-close]').forEach(button => {
  button.addEventListener('click', () => document.getElementById(button.dataset.close).close());
});
document.querySelectorAll('dialog').forEach(dialog => {
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
});
document.getElementById('print-report').addEventListener('click', () => window.print());
if ('IntersectionObserver' in window) {
  const chapterLinks = new Map([...document.querySelectorAll('.toc a')].map(link => [link.hash.slice(1), link]));
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting || !chapterLinks.has(entry.target.id)) continue;
      chapterLinks.forEach(link => link.removeAttribute('aria-current'));
      chapterLinks.get(entry.target.id).setAttribute('aria-current', 'true');
    }
  }, {rootMargin:'-120px 0px -68% 0px'});
  document.querySelectorAll('.chapter').forEach(chapter => observer.observe(chapter));
}
"""

TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="当前 LINEAR 热点前缀缓存 PR 的调用链、类关系、状态所有权，以及 DP 与 reset 缓存失效分析。内嵌图解与源码快照，可离线阅读。">
  <title>LINEAR 热点前缀缓存 · PR 图解与失效分析 · xLLM Notes</title>
  <style>{{STYLE}}</style>
</head>
<body id="top">
  <a class="skip-link" href="#invalidation">跳到正文</a>
  <div class="topbar"><div class="topbar-inner"><a class="brand" href="../../index.html">xLLM Notes</a><span class="crumb">PR 图解 / LINEAR 热点前缀缓存</span></div></div>
  <div class="page">
    <header class="intro">
      <span class="eyebrow">CODE WALKTHROUGH · 2026-10-28</span>
      <h1>LINEAR 热点前缀缓存<br>把 PR 改动、调用链与状态关系讲清楚</h1>
      <p class="subtitle">从“为什么要额外停一下”到“谁拥有 checkpoint、何时发布、何时失效”。包含本次 DP setter 调整，以及你刚才问的两个 reset 的作用与必要性。</p>
      <div class="meta"><span class="tag">HEAD <code>{{HEAD_SHORT}}</code></span><span class="tag">对比 <code>xllm_ai_xllm/main</code></span><span class="tag good">240 项单测通过</span><span class="tag">离线自包含 · 无外部脚本</span></div>
      <div class="metrics"><div class="metric"><strong>20</strong><span>PR 改动文件 · +1450 / −18</span></div><div class="metric"><strong>9</strong><span>可放大图解 · 调用 / 类 / 时序</span></div><div class="metric"><strong>{{SOURCE_COUNT}}</strong><span>源码文件快照 · 点击定位行号</span></div><div class="metric"><strong>63 + 177</strong><span>缓存与调度单测 · 非端到端验收</span></div></div>
      <div class="actions"><a class="action primary" href="#invalidation">先看两个 reset</a><a class="action" href="#overview">从头梳理 PR</a><button class="action" data-source="evidence/pr.diff">查看完整 diff</button><button class="action" data-source="evidence/validation.txt">查看验证记录</button><button class="action" id="print-report">打印 / 导出 PDF</button></div>
    </header>
    <div class="notice"><p><strong>阅读边界：</strong>原有 Markdown 图解已同步到 <code>{{HEAD_SHORT}}</code>：DP setter 恢复直接赋值，rank 校验移入计划缓存。下面两个 reset <strong>尚未删除</strong>。单测通过不等于模型精度、并发性能或合并后的全量验收通过。</p></div>
    <nav class="toc" aria-label="章节导航">{{NAVIGATION}}</nav>
    <main>{{CHAPTERS}}</main>
    <section class="chapter" id="figures"><h2>图解索引</h2><p>点击图像可全屏查看并放大；所有 SVG 都已经嵌入本文件，不需要网络或 Mermaid。</p><ul>{{FIGURE_LINKS}}</ul></section>
    <section class="chapter" id="source-reference"><h2>源码与验证快照</h2><p>正文中的源码链接会打开本页内置的只读源码查看器，并高亮对应行；不是跳到可能已经变化的远端分支。源码来自 <code>{{HEAD}}</code>，与本页分析版本一致。</p><div class="actions"><button class="action" data-source="xllm/core/framework/request/sequence.cpp" data-line="995">查看 Sequence::reset()</button><button class="action" data-source="evidence/manifest.json">Git 快照元数据</button><button class="action" data-source="evidence/validation.txt">240 项单测记录</button><button class="action" data-source="evidence/last_commit.diff">本次 DP 优化提交</button></div><noscript><p>正文和图解无需 JavaScript。源码弹窗与缩放按钮需要启用 JavaScript；关闭脚本时仍可用页面文本中的源码路径在编辑器定位。</p></noscript></section>
    <footer class="footer">当前分支 <code>{{BRANCH}}</code> · 目标跟踪分支快照 <code>{{TARGET_SHORT}}</code> · 本次仅生成文档，不修改 xLLM 源码，不发布或推送任何仓库。<br>原始 Markdown 保留在 knowledge；本报告可单独保存、双击打开或打印。<a href="../../index.html">返回知识库</a></footer>
  </div>
  <dialog id="figure-dialog" aria-labelledby="figure-title"><div class="dialog-header"><h2 id="figure-title">图解</h2><button data-close="figure-dialog" aria-label="关闭图解">关闭 ×</button></div><div class="dialog-tools"><button id="figure-out" aria-label="缩小图解">− 缩小</button><button id="figure-in" aria-label="放大图解">＋ 放大</button><button id="figure-fit">适应宽度</button><button id="figure-original">原始尺寸</button><output id="figure-scale" aria-live="polite">100%</output><span>滚动查看 · Esc 关闭</span></div><div class="diagram-scroll" id="figure-viewport"><img id="figure-image" alt=""></div></dialog>
  <dialog id="source-dialog" aria-labelledby="source-title"><div class="dialog-header"><h2 id="source-title">只读源码 / 验证证据</h2><button data-close="source-dialog" aria-label="关闭源码">关闭 ×</button></div><div class="dialog-tools source-tools"><label for="source-select">文件</label><select id="source-select"></select><label for="source-line-input">行号</label><input id="source-line-input" type="number" min="1" value="1"><button id="source-go">定位</button></div><div class="source-location" id="source-location"></div><div class="source-scroll"><ol class="source-lines" id="source-lines"></ol></div></dialog>
  <script type="application/json" id="source-data">{{SOURCE_DATA}}</script>
  <script>{{SCRIPT}}</script>
</body>
</html>
"""


def git_output(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(SOURCE_ROOT), *arguments], text=True
    ).rstrip("\n")


def refresh_document(text: str, head: str) -> str:
    replacements = {
        ORIGINAL_COMMIT: head,
        "+1453 / -19": "+1450 / -18",
        "1453 insertions(+), 19 deletions(-)": "1450 insertions(+), 18 deletions(-)",
        "当前分支独有 44 个提交": "当前分支独有 45 个提交",
        "| +34 / -1 |": "| +31 / -0 |",
        "DP 变化时失效计划": "计划携带 DP，读取时检查；不改 DP setter",
        "本次最后一个提交为什么必要？": "共享状态写保护为什么必要？",
        "源码中 `set_dp_rank()` 只清计划，不清计票标记，测试也明确约束这一点。":
            "`set_dp_rank()` 已恢复直接赋值；读取计划时会比较所属 DP，拒绝跨 DP 复用，不清计票标记。",
        "generation：这个计划是基于哪一代策略":
            "generation：这个计划是基于哪一代策略\ndp_rank：该计划属于哪个 DP 的热点表",
        "`nullopt` = 未规划，或者缓存代号已过期。":
            "`nullopt` = 未规划，或者缓存代号 / 计划所属 DP 不匹配。",
        "{0, generation}": "{0, generation, dp_rank}",
        "{H, generation}": "{H, generation, dp_rank}",
        "{checkpoint, generation}": "{checkpoint, generation, dp_rank}",
        "{token_count, generation}": "{token_count, generation, dp_rank}",
        "本轮计划停点 + generation": "本轮计划停点 + generation + dp_rank",
        "先查 Sequence 的同代计划": "先查 Sequence 的同 DP、同代计划",
        "已有同代结果时重复规划": "已有同 DP、同代结果时重复规划",
        "| 第二次调用规划 | 同代直接复用 |":
            "| 第二次调用规划 | 同 DP、同代直接复用 |",
        "| DP rank 改变 | 清掉 | **保留** | 各 DP 仍各自持有 | 此 setter 本身不搬 Block |":
            "| DP rank 改变 | 读取时因 DP 不匹配而失效；setter 不清字段 | **保留** | 各 DP 仍各自持有 | setter 只赋值，不搬 Block |",
        "| C++ 编译、gtest | 本轮未执行 |":
            "| C++ 编译、gtest | DP 缓存调整后，block_test 63 项、scheduler_test 177 项通过 |",
        "| 测试代码包含哪些断言 | 已阅读相关用例；不是测试执行通过报告 |":
            "| 测试代码包含哪些断言 | 已阅读相关用例；执行结果仅覆盖上述两组，不能外推到全部测试 |",
        "渲染和链接检查结果见 `evidence/validation.json`":
            "SVG 已嵌入 HTML；生成后单独检查本页结构与定位链接",
        "本轮没有改 C++，也没有替你重排已有改动。":
            "`bc6440e24` 中修改的 sequence.h 已通过 clang-format 20.1.6；未重排其他文件。",
        "想独立打开或修改图片": "想集中查找图解",
        "SVG 成图 + 同名 DOT 源文件": "本页图解索引；原始 DOT 仍保留在 knowledge",
        "已 fetch 的 `xllm_ai_xllm/main`":
            "此前已 fetch 的本地跟踪分支 `xllm_ai_xllm/main`",
    }
    for before, after in replacements.items():
        text = text.replace(before, after)
    return text


def main() -> None:
    head = git_output("rev-parse", "HEAD")
    target = git_output("rev-parse", "xllm_ai_xllm/main")
    metadata = {
        "head": head,
        "target_ref": "xllm_ai_xllm/main",
        "target": target,
        "merge_base": git_output("merge-base", "xllm_ai_xllm/main", "HEAD"),
        "branch": git_output("branch", "--show-current"),
        "head_committed_at": git_output("show", "-s", "--format=%ci", "HEAD"),
        "diff_scope": git_output("diff", "--shortstat", "xllm_ai_xllm/main...HEAD").strip(),
        "original_markdown_commit": ORIGINAL_COMMIT,
        "target_refresh": "This HTML generation did not fetch or change the target ref.",
        "html_scope": "Documentation only; no xLLM source changes.",
    }
    if head != "bc6440e245d2c1157f4e2bae2c181f599d0c34dc":
        raise RuntimeError("This report is pinned to bc6440e24; review content before changing its snapshot.")
    manifest_text = (VALIDATION_ROOT / "manifest.env").read_text()
    manifest = dict(line.split("=", 1) for line in manifest_text.splitlines() if "=" in line)
    header = git_output("show", f"{head}:xllm/core/framework/request/sequence.h") + "\n"
    if hashlib.sha256(header.encode()).hexdigest() != manifest["source_sha256"]:
        raise RuntimeError("Committed header does not match the validated source.")
    if manifest["exit_code"] != "0" or manifest["followup_exit_code"] != "0":
        raise RuntimeError("Expected both targeted test runs to pass.")
    validation_parts = [manifest_text]
    for log_name in ("build_output.txt", "scheduler_test_output.txt"):
        selected = [
            line for line in (VALIDATION_ROOT / log_name).read_text().splitlines()
            if re.search(r"\[==========\]|\[  PASSED  \]|\[       OK \].*(HotFront|PromptHashInvalidation|SequenceResetAndDp)", line)
        ]
        validation_parts.append(log_name + "\n" + "\n".join(selected))
    sources = {
        "evidence/manifest.json": json.dumps(metadata, ensure_ascii=False, indent=2),
        "evidence/pr.diff": git_output("diff", "xllm_ai_xllm/main...HEAD"),
        "evidence/last_commit.diff": git_output("show", "--format=fuller", "HEAD"),
        "evidence/validation.txt": "\n\n".join(validation_parts),
    }
    chapter_ids = {path.name: slug for slug, _, path in CHAPTERS}
    figures = {}
    line_mappers = {}

    def add_source(source_key: str) -> None:
        if source_key not in sources:
            sources[source_key] = git_output("show", f"{head}:{source_key}") + "\n"

    def current_line(source_key: str, old_line: int) -> int:
        if source_key not in line_mappers:
            original_lines = git_output("show", f"{ORIGINAL_COMMIT}:{source_key}").splitlines()
            new_lines = sources[source_key].splitlines()
            mapping = {}
            matcher = difflib.SequenceMatcher(None, original_lines, new_lines, autojunk=False)
            for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
                for position in range(old_start, old_end):
                    mapping[position + 1] = (
                        new_start + position - old_start + 1
                        if operation == "equal"
                        else min(new_start + 1, len(new_lines))
                    )
            line_mappers[source_key] = mapping
        return line_mappers[source_key].get(old_line, old_line)

    def embed_diagram(image: etree._Element) -> None:
        image_path = DOCUMENT_ROOT / image.attrib["src"]
        source_dot = image_path.with_suffix(".dot").read_text()
        source_dot = source_dot.replace("{H, generation}", "{H, generation, dp_rank}")
        source_dot = source_dot.replace("efd1692a366", head[:10])
        source_dot = source_dot.replace("2026-10-28 14:13 +0800", metadata["head_committed_at"])
        source_dot = source_dot.replace("+1453 / -19", "+1450 / -18")
        svg_bytes = subprocess.check_output(["dot", "-Tsvg"], input=source_dot.encode())
        etree.fromstring(svg_bytes)
        image.attrib["src"] = "data:image/svg+xml;base64," + base64.b64encode(svg_bytes).decode()
        image.attrib["loading"] = "lazy"
        image.attrib["decoding"] = "async"
        caption = image.attrib.get("alt", image_path.stem)
        figure_id = "diagram-" + image_path.stem
        figures[figure_id] = caption
        wrapper = etree.Element("figure", {"class": "figure", "id": figure_id})
        opener = etree.SubElement(wrapper, "a", {
            "class": "figure-open", "href": "#" + figure_id, "aria-haspopup": "dialog",
            "aria-label": "放大查看：" + caption,
        })
        parent = image.getparent()
        parent.replace(image, wrapper)
        opener.append(image)
        label = etree.SubElement(wrapper, "figcaption")
        label.text = caption
        hint = etree.SubElement(label, "span", {"class": "figure-hint"})
        hint.text = "点击放大"
        if parent.tag == "p" and len(parent) == 1 and not (parent.text or "").strip():
            grandparent = parent.getparent()
            parent.remove(wrapper)
            grandparent.replace(parent, wrapper)

    def render_chapter(slug: str, label: str, path: Path, number: int) -> str:
        text = refresh_document(path.read_text(), head)
        rendered = markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists", "toc"])
        root = html_parser.fragment_fromstring(rendered, create_parent="div")
        for image in list(root.iter("img")):
            embed_diagram(image)
        for table in list(root.iter("table")):
            parent = table.getparent()
            wrapper = etree.Element("div", {"class": "table-wrap", "tabindex": "0", "role": "region", "aria-label": "可横向滚动的数据表"})
            parent.replace(table, wrapper)
            wrapper.append(table)
        for link in root.iter("a"):
            href = link.attrib.get("href", "")
            parsed = urlsplit(href)
            source_key = None
            old_line = int(parsed.fragment[1:]) if re.fullmatch(r"L\d+", parsed.fragment) else 1
            line_number = old_line
            if parsed.scheme == "source":
                source_key = parsed.path
            elif parsed.scheme == "evidence":
                source_key = "evidence/" + parsed.path
            elif href.startswith("../../xllm-main-cann9-20260911-linear-prefix-cache/"):
                source_key = unquote(parsed.path.split("linear-prefix-cache/", 1)[1])
                add_source(source_key)
                line_number = current_line(source_key, old_line)
            elif href in chapter_ids:
                link.attrib["href"] = "#" + chapter_ids[href]
            elif href == "diagrams/":
                link.attrib["href"] = "#figures"
            elif href.startswith("evidence/"):
                source_key = parsed.path
            if source_key:
                add_source(source_key)
                if line_number > len(sources[source_key].splitlines()):
                    raise RuntimeError(f"Line out of range: {source_key}:{line_number}")
                link.attrib.update({
                    "href": "#source-reference", "class": "source-link",
                    "data-source": source_key, "data-line": str(line_number),
                    "title": f"打开内嵌源码：{source_key}:{line_number}",
                })
                if link.text and old_line != line_number:
                    link.text = link.text.replace(f":{old_line}", f":{line_number}")
        subheadings = []
        for heading in root.xpath(".//h1|.//h2|.//h3|.//h4"):
            level = int(heading.tag[1:])
            anchor = slug + "--" + heading.attrib.get("id", str(len(subheadings)))
            heading.attrib["id"] = anchor
            heading.tag = "h" + str(min(5, level + 1))
            if level == 2:
                subheadings.append(f'<li><a href="#{html.escape(anchor)}">{html.escape("".join(heading.itertext()))}</a></li>')
        contents = "".join(etree.tostring(child, encoding="unicode", method="html") for child in root)
        summary = '<details class="section-index"><summary>本章目录</summary><ol>' + "".join(subheadings) + "</ol></details>"
        first_heading_end = contents.find("</h2>") + len("</h2>")
        contents = contents[:first_heading_end] + summary + contents[first_heading_end:]
        return (
            f'<section class="chapter" id="{slug}"><span class="chapter-label">'
            f'{number:02d} / {html.escape(label)}</span>{contents}'
            '<a class="back-top" href="#top">返回顶部 ↑</a></section>'
        )

    rendered_chapters = [render_chapter(slug, label, path, number) for number, (slug, label, path) in enumerate(CHAPTERS, 1)]
    source_count = sum(not key.startswith("evidence/") for key in sources)
    metadata["embedded_source_files"] = source_count
    metadata["embedded_diagrams"] = len(figures)
    sources["evidence/manifest.json"] = json.dumps(metadata, ensure_ascii=False, indent=2)
    source_json = json.dumps(sources, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    replacements = {
        "STYLE": STYLE,
        "HEAD": head,
        "HEAD_SHORT": head[:9],
        "BRANCH": html.escape(metadata["branch"]),
        "TARGET_SHORT": target[:9],
        "SOURCE_COUNT": str(source_count),
        "NAVIGATION": "".join(f'<a href="#{slug}">{number:02d} {html.escape(label)}</a>' for number, (slug, label, _) in enumerate(CHAPTERS, 1)),
        "CHAPTERS": "\n".join(rendered_chapters),
        "FIGURE_LINKS": "".join(f'<li><a href="#{figure_id}">{html.escape(caption)}</a></li>' for figure_id, caption in figures.items()),
        "SOURCE_DATA": source_json,
        "SCRIPT": SCRIPT.replace("{{HEAD_SHORT}}", head[:9]),
    }
    output = TEMPLATE
    for name, value in replacements.items():
        output = output.replace("{{" + name + "}}", value)
    output_path = REPORT_ROOT / "index.html"
    relative_output = output_path.relative_to(NOTES_ROOT)
    if output_path.exists():
        previous = output_path.read_text()
        diff_lines = list(difflib.unified_diff(previous.splitlines(), output.splitlines(), lineterm=""))[2:]
        if not diff_lines:
            return
        patch_lines = ["*** Begin Patch", f"*** Update File: {relative_output}"]
        patch_lines.extend("@@" if line.startswith("@@") else line for line in diff_lines)
    else:
        patch_lines = ["*** Begin Patch", f"*** Add File: {relative_output}"]
        patch_lines.extend("+" + line for line in output.splitlines())
    patch_lines.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(patch_lines) + "\n", text=True, cwd=NOTES_ROOT, check=True)
    print(json.dumps({"output": str(output_path), "source_files": source_count, "diagrams": len(figures), "bytes": len(output.encode())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
