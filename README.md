# xLLM Notes

围绕 xLLM 推理框架的**特性设计报告、PR 评审与知识沉淀**。每篇是一个自包含 HTML(样式内联),可离线双击打开、可打印导出 PDF,也能单独发给别人。

## 目录结构

```
xllm-notes/
├── index.html                     # 首页:分类导航 + 条目 card 列表(手动维护)
├── README.md                      # 本文件
├── _template/
│   └── report.html                # 新报告起手模板(复制它改内容)
├── reports/                       # 一次性快照:特性设计、PR 评审
│   └── <slug>/index.html
└── notes/                         # 持续沉淀:原理、踩坑、方法论
    └── <slug>/index.html
```

顶层保持浅:以后要扩只加**平级**目录(如 `benchmarks/`、`adr/`),不往深里套。
`_template/` 下划线开头,不作为内容条目。

## 命名约定(全站小写 kebab-case)

| 分区 | slug 规则 | 例 |
|------|-----------|-----|
| `reports/` | `<特性>-pr<编号>`,无 PR 就 `<特性>` | `qwen35-linear-prefix-cache-pr1839` |
| `notes/` | `<主题>`,**不加**日期前缀 | `linear-state-prefix-cache` |

- 每个条目是「一个目录 + `index.html`」,URL 干净不带 `.html`(`/reports/<slug>/`)。
- 条目要配图片/附件时,直接丢进它自己的目录,不污染别人。
- 目录名即 URL,**改名会断链**——排序交给首页,不靠目录名。

## 加一篇新报告

```bash
slug=my-feature-pr2001
mkdir -p reports/$slug
cp _template/report.html reports/$slug/index.html
# 编辑 reports/$slug/index.html:改 <title>、面包屑 slug、标题、各 section
```

然后在 `index.html` 对应分区(设计报告 或 知识沉淀)**复制一张 card**,改 href / 标题 / 摘要 / 徽章即可。

Mermaid 图小贴士:节点或连线 label 里如果有 `()`、`/`、空格,**用双引号包住**,例如 `node["文本 (备注)"]`、`A -- "min(x, y)" --> B`,否则解析器会报错。

## 本地预览

别直接双击(`file://` 下 Mermaid 的 ESM import 会被 CORS 拦)。起个静态服务:

```bash
cd xllm-notes
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000/
```

## 发布到 GitHub Pages

```bash
git init && git add . && git commit -m "docs: init xllm-notes"
git remote add origin git@github.com:<你的用户名>/xllm-notes.git
git push -u origin main
```

仓库 Settings → Pages → Source 选 **Deploy from a branch**,Branch 选 `main` / `(root)`,保存。
一两分钟后访问:

```
https://<你的用户名>.github.io/xllm-notes/
https://<你的用户名>.github.io/xllm-notes/reports/<slug>/
```
