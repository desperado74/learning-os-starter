# Learning OS Starter

[中文](#中文) · [English](#english)

## 中文

把AI辅助学习组织成一个可在本地接续的系统：个人目标与偏好、课程层级、材料与模块规划、真实作答、暂停和交接，都保存在自己的Markdown工作区。

这是我持续使用的Learning OS的通用公开版本。我想分享完整方法与实现，让你用自己的Codex或Claude Code建立自己的学习系统。作者的画像、课程、教材、作答和账号配置不在项目中。

**当前为完整系统预览版。** 初始化、控制面、教材读取、可选工具和虚构文件周期有代码测试；真实双客户端学习周期、真实Anki及外部试用尚未验证。详细状态见[验证记录](docs/验证记录.md)。

### 第一次来，从这里开始

需要Python 3.9+，以及自己安装、登录并能操作本地文件的agent。Python工具只用标准库；Anki与PDF渲染属于按需选用的外部工具。

1. 下载这个仓库，或克隆到一个新目录。
2. 用自己的Codex或Claude Code打开项目，发送下面的启动提示。agent会分步讨论课程、目标、爱好、习惯和教材；不知道的内容可以保持未知。
3. 确认课程层级和文件清单后，在仓库外创建新的私人工作区。已有学习系统一律不覆盖。
4. 在自己的私人根目录或具体课程目录打开新聊天，核对材料和实际起点，规划一个模块，再开始学习。

```text
请先读取AGENTS.md、README.md和docs/本地初始化.md。
带我建立自己的Learning OS，先讨论目标、课程与实际起点，再问可选的爱好、学习习惯和教材。
先提出课程层级、独立私人目录与精确写入清单，预览后由我确认再创建。
不要读取或修改我已有的学习系统，不把私人资料写进这个公开仓库。
```

命令安装路径、输入格式和确认步骤见[本地初始化](docs/本地初始化.md)。默认命令只预览，显式`--apply`才创建：

```sh
python3 tools/init_workspace.py --workspace ../my-learning --config ../my-learning-input.json
```

配置文件也留在仓库外，由你和agent根据实际回答填写。初始化不下载教材，不登录账号，不安装hook，不调用模型。

### 一个完整学习周期

**定位 → 核材料与规划 → 接触原材料 → 讲解与作答 → 反馈与记录 → 暂停或收尾 → 新聊天接续。**

以平均数的虚构课程为例，A独立完成、B提示后完成、C未作答。暂停交接保留这三个事实。新聊天先核对B的方法选择，再做C；不能把提示历史删掉或把未作答写成完成。到本模块边界，保存并回读交接、更新主页、给出填好路径的接续提示词，再停止。

[全流程示例](examples/full-cycle/README.md)解释别人怎样使用，并提供可在新目录运行的文件重放：

```sh
python3 examples/full-cycle/demo.py --workspace ../learning-os-demo
# 核对演示清单后，上一条命令加 --apply
```

演示答案全部是脚本生成的虚构数据，不是实际用户作答或模型测试。

### 系统各层负责什么

| 层级 | 职责 | 依据 |
| --- | --- | --- |
| 根控制面 | 个人方向、课程组织与跨域协调 | 自己的画像、方向图与相关证据 |
| manager总管 | 本层课程地图、主线与已授权的综合任务 | 子课程关系及指定证据 |
| leaf课程 | 教学、教材、模块、作答与收尾 | 本课程材料与实际记录 |

分类文件夹不是学习节点。一个简单课程可以直接是leaf；只有需要协调多门课程时才建立manager。普通叶级学习不扫描兄弟课程或全量画像。

[架构与实现](docs/系统架构与实现.md)包含架构图、各部分的代码位置与验证状态。初始化把通用运行时和规则复制到私人工作区，之后独立使用。更新公开仓库不会同步修改已有私人工作区。

### 主要机制与工具

- [学习循环与个性化偏好](templates/system/学习偏好.md)：具体例子、原材料、主动加工与精确反馈；互动节奏由你决定。
- [下一模块规划](templates/system/短期规划协议.md)：承接长期主线和真实交接，核材料、前置与完整题组，再确定自然停止点。
- [教材读取](templates/system/教材读取协议.md)：OCR只辅助定位，题面、公式和图表按需要实际核原图；只读工具不修改教材。
- [作答证据](templates/system/教材题目执行协议.md)：分别记录证据、处置和下一步；AI示范、提示和独立作答不混同。
- [交接与接续](templates/system/模块切换协议.md)：partial恢复未完任务；completed描述范围已处理，不表示长期掌握。
- [可选Anki](templates/system/Anki制卡与导入协议.md)：默认关闭，启用后先预览，明确授权才导入，回读确认；只连接本机，不自动启动应用。
- [可选SQLite索引](templates/system/本地索引说明.md)：只索引文件位置、指纹和元数据；可重建，不复制教材或画像正文，不代替Markdown。

在生成的私人工作区，agent可以使用`learning.py brief`、`overview`、`open`、`plan-context`、`doctor`等入口。结构检查与证据数量不能替代原文核对，也不能证明学会。

### 隐私与使用边界

公开仓库放方法、工具、空白模板和虚构示例；自己的画像、教材引用、课程、答案、交接、卡片和索引留在仓库外的私人目录。初始化拒绝已有目录、符号链接跳转和现有Git checkout内的目标。

私人文件留在本地不代表模型服务永远不会收到内容：agent读取教材或记录后，处理方式取决于你使用的客户端、模型和权限配置。请自行决定提供哪些材料。项目不捆绑密钥或账号配置，也不把任何私人系统作为运行依赖。

Markdown保存的是可核对的过程。AI仍可能误读或错误反馈；一次正确答案、提示后完成或模块收尾都不保证长期掌握。核心详细协议目前以中文为主；本介绍、初始化、架构、索引及全流程说明有英文版本。

### 轻量手动模式

暂时不想生成整个工作区，可以复制[学习主页](templates/学习主页.md)、[当前模块](templates/当前模块.md)和[交接](templates/交接.md)，填写材料与范围，再向AI提供这些文件和[使用说明](AI使用说明.md)。参考[原Starter示例](examples/markdown/README.md)。旧版的一次独立只读接续观察见[测试01](docs/接续测试-01.md)，它不证明完整系统可靠。

### 验证与反馈

```sh
python3 tools/check.py
python3 -m unittest discover -s tests -v
```

文件检查只覆盖必需文件及简单内联本地链接，不检查外部网页、标题锚点或模型行为。测试使用虚构数据与临时目录，不连接真实Anki、不修改已有学习系统。已做与未做检查分别列在[验证记录](docs/验证记录.md)。

欢迎通过[Issues](https://github.com/desperado74/learning-os-starter/issues)反馈具体步骤、结果和卡点；提交前去掉私人材料、作答与账号信息。见[贡献说明](CONTRIBUTING.md)、[来源与设计取舍](docs/来源与设计取舍.md)。本项目采用[MIT许可](LICENSE)。

## English

Organize AI-assisted learning into a local, resumable system: personal goals and preferences, course hierarchy, materials and module planning, actual answers, pauses and handoffs live in your own Markdown workspace.

This is a generalized version of the Learning OS I use and refine. I am sharing the method and implementation so you can build your own system with Codex or Claude Code. My personal profile, courses, materials, answers and account settings are excluded.

**This is a full-system preview.** Code tests cover initialization, routing, read-only materials, optional tools and a fictional file cycle. Actual Codex/Claude learning cycles, real Anki imports and external trials remain unverified. See the [validation record](docs/验证记录.md).

### Start here

You need Python 3.9+ and your own installed, authenticated agent with local file access. Python tools use only the standard library. Anki and PDF rendering are optional external tools.

1. Download or clone this repository into a new directory.
2. Open it in your Codex or Claude Code and send the prompt below. Discuss your goal, course and starting point first, then optional interests, habits and materials. Unknown information can stay unknown.
3. Review the hierarchy and exact write list, then create a NEW private workspace outside this checkout. Existing learning systems are never overwritten.
4. Open the private root or selected course in a new chat. Verify materials and the actual starting point before planning one module and beginning.

```text
Read AGENTS.md, README.md and docs/本地初始化.md first.
Help me set up my own Learning OS. Discuss my goal, course and starting point,
then optional interests, learning habits and materials.
Propose the hierarchy, a separate private directory and the exact write list.
Preview the changes and wait for my confirmation before creating the workspace.
Do not read or modify an existing learning system or put personal data in this checkout.
```

The [setup guide](docs/本地初始化.md) explains the input format and commands. The initializer previews by default; explicit `--apply` creates the workspace. The command in the Chinese section uses a private configuration file outside the checkout. Initialization does not download books, sign in, install hooks or call a model.

### One complete learning cycle

**Locate → verify materials and plan → engage with the material → teaching and answers → feedback and records → pause or close → resume in a new chat.**

In the fictional average-value course, A is answered independently, B with a hint and C remains unanswered. A partial handoff preserves all three facts. A new chat checks B's method selection and processes C without deleting the hint history. At the module boundary, save and read back a handoff, update the overview, deliver a filled-in continuation prompt and stop.

The [complete workflow example](examples/full-cycle/README.md) includes a replay you can run in a new directory using the commands above. All answers are generated fixtures, not real learner evidence or an AI evaluation.

### Architecture

The root coordinates goals and courses. Managers maintain their course maps, long-term routes and authorized cross-course work. Leaves contain teaching, materials, modules, answers and handoffs. A grouping folder is not a learning node. A simple course can be a leaf directly; managers are useful when multiple courses need coordination.

See [architecture and implementation](docs/系统架构与实现.md) for the diagram, code locations and verification status. Initialization copies generic rules and tools into the separate private workspace. It has no dependency on the author's original system. Updating this checkout does not update existing private workspaces.

### Methods and tools

The system keeps a common learning cycle with user-specific preferences. Planning follows the long-term route, verified materials, prerequisites, complete assigned exercises and a natural stopping point. Original material remains the basis for learning; OCR helps locate content but does not replace required visual checks.

Exercise records separate actual evidence, disposition and next action. Hints, demonstrations and independent work remain distinct. A partial handoff resumes unfinished tasks. A completed handoff describes handled scope, not lasting mastery.

Optional Anki is disabled until configured. The adapter previews by default, imports only after explicit authorization and `--apply`, and confirms notes through readback. It connects only to local AnkiConnect and never launches the app. The optional SQLite index stores scoped metadata and hashes, not books or profile bodies. It is rebuildable and never replaces Markdown.

Your agent can use `learning.py brief`, `overview`, `open`, `plan-context` and `doctor` in the generated workspace. These commands locate context and check structure; file counts cannot establish learning.

### Privacy and limitations

This checkout contains generic methods, tools, templates and fictional examples. Keep your profile, material references, courses, answers, handoffs, cards and index in the separate private directory. Initialization refuses existing targets, symlink redirection and targets inside existing Git checkouts.

Local storage does not guarantee that a model service never receives content: an agent may send material it reads according to your client, model and permissions. Decide what to provide. No credentials or account settings are bundled, and no private source system is a runtime dependency.

AI can misread or give incorrect feedback. A correct answer, completion with hints or a closed module does not guarantee mastery. Detailed core protocols currently use Chinese; this introduction and the setup, architecture, index and complete workflow guides include English.

### Manual mode, validation and feedback

For a smaller manual workflow, copy the three [overview](templates/学习主页.md), [module](templates/当前模块.md) and [handoff](templates/交接.md) templates. Supply them with the [AI instructions](AI使用说明.md) and your materials. See the [original example](examples/markdown/README.md). The [single earlier continuation test](docs/接续测试-01.md) does not establish full-system reliability.

Run the validation commands above from this repository. They use fictional data and temporary directories, never real Anki or an existing learning system. The file checker covers required files and simple inline local links, not external URLs, heading anchors or model behavior. See the [validation record](docs/验证记录.md).

Report concrete steps and results through [Issues](https://github.com/desperado74/learning-os-starter/issues), removing private data first. See [contributing](CONTRIBUTING.md) and [sources and design choices](docs/来源与设计取舍.md). The project uses the [MIT License](LICENSE).
