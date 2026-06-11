---
name: quiz-builder
description: >
  把任意学习材料（讲义/笔记/教材/PDF/PPT/Markdown/网页/转写稿）做成一个单文件、
  可离线打开、可反复刷的 HTML 互动习题库：5 种题型（单选/多选/判断/填空/闪卡）、
  即时判分 + 解析、按单元/题型筛选、错题本快照、进度本地保存、中英双语一键切换。
  当用户说"做习题库 / 刷题网页 / 把笔记做成练习题 / 互动题库 / 错题本 / 期末练习题 /
  generate a quiz / make a practice quiz / turn notes into flashcards"时触发。
  区别于 cheatsheet-generator（把材料压成一张速查表）——本 skill 产出的是可作答、
  可反复练的题库。
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Quiz Builder — 学习材料 → 单文件 HTML 互动习题库

把任意学习材料变成一个 **自包含、可离线打开、可反复刷** 的 HTML 习题库。最终产物
是 **一个 `.html` 文件**：双击即用、零依赖、进度存在浏览器本地、可发给同学或丢进
网盘。适用于备考、刷题、记忆类自学。

- 模板：`${CLAUDE_SKILL_DIR}/templates/quiz_template.html`（完整引擎，5 个占位符）
- 可运行示例：`${CLAUDE_SKILL_DIR}/examples/demo.html`（5 种题型 + 中英双语，先打开它看成品）
- 辅助脚本：`${CLAUDE_SKILL_DIR}/scripts/`（仅在处理 PPT 导出 PDF 时才需要，见 Phase 2）
- 姊妹 skill：`cheatsheet-generator`（同样"材料 → 复习产物"，但产出 LaTeX 速查表）

技能目录是 `${CLAUDE_SKILL_DIR}`。工作目录默认当前目录，除非 `$ARGUMENTS` 指定路径。
按顺序执行下面四个阶段。

---

## Phase 1 — 收集材料 & 确认配置

1. **扫描材料**：用 Glob 找 `**/*.{pdf,pptx,md,txt,docx,ipynb,html}` 和图片
   `**/*.{png,jpg,jpeg}`。也接受用户直接粘贴的文本 / 一个网址。
2. **用 AskUserQuestion 一次问清**（给出默认值，能推断的就别问）：
   - **题库标题**（+ 是否要中英双语标题）。
   - **怎么分组**（`groups`）：按章节 / 周 / 主题，默认一章一组。
   - **题量与配比**：每组多少题；"官方/原文题"（`type:"official"`，来自材料原文）
     vs "自拟练习题"（`type:"practice"`）的比例。默认：原文里的例题全收 + 每组补
     4-6 道练习题。
   - **题型**（`kind`，可混用）：单选 `single` / 多选 `multi` / 判断 `tf` /
     填空 `fill` / 闪卡 `flash`。默认以单选为主，按材料性质点缀其它题型
     （概念记忆→闪卡，定义→填空，"对错辨析"→判断，多个正确项→多选）。
   - **语言**：UI 与解析默认语言（`zh`/`en`）。模板本身支持运行时一键切换，且题目
     文本字段可写成 `{zh, en}` 双语；先问清是否要双语出题（双语出题工作量更大）。

---

## Phase 2 — 把材料读成"带出处的干净文本"（按类型分支，不要一刀切）

目标：拿到可靠的文本，并尽量保留出处（页码/章节）以便每题标 `source`。**按材料
类型选路径，绝大多数材料用不到去动画那一步：**

- **Markdown / txt / 网页 / 用户粘贴文本** → 直接 Read，无需任何依赖。
- **DOCX / ipynb** → 直接 Read。
- **普通 PDF（教材、讲义、试卷）** → 优先用 Read 工具直接读 PDF；需要更精确的
  逐页文本时再用 `pdftotext -layout file.pdf out.txt`（macOS 自带 / poppler）。
- **图片笔记 / 拍照讲义** → 用 Read 直接视觉读取。
- **⚠️ 仅当材料是 PPT 导出的 PDF 且带逐条飞入动画**（同一页文字重复 4-5 次、
  页码对不上）→ 才用下面两个脚本先去重，否则同一张 slide 会被反复出题：
  ```bash
  python "${CLAUDE_SKILL_DIR}/scripts/dedup_pdf.py" --glob "week*/module*.pdf"      # 去动画 build，保留最后一帧
  python "${CLAUDE_SKILL_DIR}/scripts/extract_text.py" --glob "week*/*_dedup.pdf" --out _module_text  # 逐页抽文本，带 PAGE N 标记
  ```
  这两个脚本依赖 `pymupdf`（`pip install pymupdf`）。**装不上不要卡住**：退回到
  `pdftotext` 或直接 Read PDF 即可，只是页码引用会粗一些。

**读完所有要用到的内容再出题**——出题只能基于真正读到的文本，`source` 的页码/章节
必须来自材料本身，**绝不臆造**。

---

## Phase 3 — 出题（写 QUESTIONS 数组）

题目 schema 见模板顶部注释。所有题型共有：`id` / `group` / `source` / `type` /
`kind` / `question` / `explanation`；各题型附加字段：

| kind | 附加字段 | 判分 |
|------|---------|------|
| `single` | `options[]`, `correct`(索引) | 选项 == correct |
| `tf` | `correct`(0/1)；`options` 可省→默认 正确/False | 同单选 |
| `multi` | `options[]`, `correct`([索引…]) | 选中集合 == correct 集合（提交制） |
| `fill` | `answer`(字符串 或 可接受变体数组) | 忽略大小写/空格匹配任一变体 |
| `flash` | `back`(答案面) | 自评：会/不会（不会→进错题本） |

文本字段（`question`/`explanation`/`options`/`back`/`label`/`title`）都支持
**纯字符串**（中英共用）或 **`{zh, en}`** 双语对象。题干可含内联 HTML
（`<code>`/`<pre>`/`<strong>`），计算题可在解析里用 `<pre>` 写分步推导。

出题准则：
- **原文题（official）逐字照搬** 材料里的例题/习题，`source` 写明出处页码或章节
  （如 `"Ch.3 p.42"` / `"M2 课件 P13"`）——这是题库可信度的锚。
- **练习题（practice）同风格自拟**，覆盖该单元核心概念，`source` 写 `"练习题"`。
- 干扰项要"像真的"：用常见混淆点；并在 `explanation` 里**逐项点破**每个错误选项
  错在哪，而不只是说正确答案。
- `id` 以组前缀编号（`u1-1`、`u1-2`…），`group` 必须能在 `CONFIG.groups` 找到。

### ✅ 准确性自检（公开给别人用，这一步是信任的命门，必须做）
出完题后，**逐题回到原文核对**，再交付：
1. 每道 `official` 题的答案/选项确实出自所标 `source`；标不出处的题改成
   `practice` 或删掉，绝不挂"官方"标签。
2. 每道题的 `correct` / `answer` / `back` 与材料一致，解析里没有与原文矛盾的断言。
3. 拿不准的题宁可不出。可以把"低置信度"的题单独放一个 group 让用户复核。
对题量较大的课，分单元批次出题 + 批次自检，避免一次性糊弄出几道就收尾。

---

## Phase 4 — 填模板，产出单文件 HTML，并实测

1. 复制 `${CLAUDE_SKILL_DIR}/templates/quiz_template.html`，替换 5 个占位符：
   - `{{TITLE}}` — `<title>` 用的纯文本标题。
   - `{{STORAGE_KEY}}` — 唯一 localStorage key，建议 `"<课程代号>-quiz-v1"`；
     以后想强制清空所有人进度就把 `-vN` 递增。
   - `{{DEFAULT_LANG}}` — `"zh"` 或 `"en"`。
   - `{{TITLE_JSON}}` / `{{SUBTITLE_JSON}}` — 标题/副标题，写成 `"..."` 或
     `{zh:"...", en:"..."}`（注意这里是 JS 字面量，不是字符串占位）。
   - `{{GROUPS}}` — `CONFIG.groups` 数组项，按顺序：
     `{key:"u1", label:{zh:"第1章",en:"Unit 1"}}, …`。
   - `{{QUESTIONS}}` — Phase 3 的全部题目对象，逗号分隔。
   - 参考 `examples/demo.html` 的填法（它就是模板填好的成品）。
2. **填完做静态自检**（任选其一，别跳过）：
   - 抽出 `<script>` 用 `node --check` 验语法（占位符没转义/引号没闭合会在这里暴雷）；
   - 校验：每个 `question.group` 都能在 `CONFIG.groups` 找到 key；每个 `correct`
     是合法索引；`id` 全局唯一。
3. 输出文件放材料同目录，命名 `Quiz.html`。
4. **用浏览器打开实测**（见 [[feedback_verify_visual_output]]：UI 产物先 render-and-read
   再说"完成"）。可用 chrome-devtools：覆盖每种用到的题型——答题→判分变色→出解析、
   筛选计数、错题本筛选、保存快照→重做、语言切换、导出、**刷新后进度仍在**。控制台
   不能有报错。确认无误再交付。

---

## 给大众的：怎么用 & 怎么分享

- **用**：双击 `Quiz.html` 用任意浏览器打开即可，纯前端、不联网、不收集数据，
  答题进度只存在你自己浏览器的 localStorage。
- **分享**：直接把这个 `.html` 文件发给别人 / 丢网盘；或推到 GitHub Pages /
  任意静态托管，发链接即可。每个人的进度互相独立。
- **重置**：页面里"重置主进度"按钮，或换浏览器/清缓存即清空。

## 成品自带功能（模板已实现，无需重写）

单文件零依赖离线、移动端自适应；中英一键切换（记住选择）；5 种题型即时判分 + 解析；
按单元/题型/错题本筛选并显示题数；统计条（已答/正确/错误/正确率）；进度
localStorage 自动保存；**错题本快照**（把当前错题存成命名集合，单独刷、重做、删除，
与主进度互不干扰）；导出错题为纯文本；键盘快捷键（`1-5` 选项、`Enter` 提交/翻面、
`←/→` 翻题）。

## 适用 / 不适用

- ✅ 选择/多选/判断/填空/记忆卡 自学题库。
- ⚠️ 需要打分计时的"正式考试模式"、随机组卷、服务端记录成绩 → 本模板是纯自学
   工具，需另行扩展。
- ❌ 只想要一张压缩复习表 → 用 `cheatsheet-generator`。
