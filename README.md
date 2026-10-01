# Learning OS Starter

[中文](#中文) · [English](#english)

## 中文

用 Markdown 保存 AI 辅助学习的当前位置、实际作答和下一步，帮助你在新聊天中接着学。

## 为什么分享这个项目

这个项目来自我持续使用和调整的个人学习工作区 Learning OS。我希望把实际用到的学习方法、文档和小工具整理出来，让其他使用 AI 学习的人也能尝试，并根据使用反馈继续改进。

第一版从一个具体问题开始：一轮学习结束后，怎样留下可核对的进度，让下一次聊天知道从哪里接上。记录里既保留做过什么，也保留得到过哪些帮助；提示后完成的题，仍然需要一次独立验证。

你可以先用一门课试一轮：确定范围、保留作答、整理交接，再在新聊天中继续。下面提供空白模板、完整示例和检查工具。

当前为早期版本。一次独立 Codex 聊天的显式文件接续测试通过；完整学习周期和外部试用尚未验证。

## 先看看用起来是什么样

打开 [完整示例](examples/markdown/README.md)，你会看到同一轮学习的开始状态、作答记录和交接状态。

示例里，练习 A 独立完成，练习 B 根据提示完成，练习 C 尚未作答。新聊天应当从 B 的独立验证开始，同时保留 C 为待做任务。一次测试观察到了这个行为，完整输入和输出见 [接续测试 01](docs/接续测试-01.md)。

## 开始自己的课程

阅读和填写模板只需要文本编辑器。Markdown 是可以直接阅读的文本文件，也可以用支持 Markdown 的编辑器预览。

1. 把 [学习主页](templates/学习主页.md)、[当前模块](templates/当前模块.md) 和 [交接](templates/交接.md) 复制到自己的课程目录，保留这三个文件名。自己的课程目录由你选择，留在私人工作区即可。
2. 在学习主页填上课程名称和材料入口；在当前模块填本轮范围、任务和停止位置。首次使用时，交接写“首次学习，暂无交接”，并清除其余尚无依据的占位内容。
3. 给 AI 提供这三个文件、[AI 使用说明](AI使用说明.md)和所需材料，请它从本轮范围开始。文件中的“待填写”不是学习证据，应在使用前填写或明确写“未知”。
4. 学习过程中，将原始作答、得到的提示和反馈保存到当前模块；结束时检查记录，再更新学习主页和交接。
5. 新开聊天，提供更新后的文件、AI 使用说明和相关材料，再发送下面的接续提示。

```text
请先读取 AI 使用说明、学习主页、当前模块和交接。
先说清当前位置和下一步，再从那里继续。
以实际作答记录区分独立完成、提示后完成和未完成。
记录或材料读取不到时，明确说明缺什么；不要把缺失证据补成已完成。
```

AI 能读取本地目录时，请明确指定课程目录和使用说明文件。普通聊天则附上这些文件或粘贴文本，具体方式取决于所用工具。不要假设 AI 已自动读过文件。

## 文件各管什么

| 文件 | 内容 |
| --- | --- |
| 学习主页 | 当前材料、模块和简短续学位置 |
| 当前模块 | 本轮范围、题目、实际作答与待做任务 |
| 交接 | 本次收尾结果、剩余问题和下一次入口 |
| AI 使用说明 | 读取、反馈和记录的共同约定 |

逐题状态只在当前模块维护。主页和交接指向它，避免复制三份题目表。模块终止时先收尾，下一模块另行规划。

## 适用范围与当前限制

适合希望用 AI 辅助学习、愿意保存少量文件并核对学习记录的人。第一版关注一门课的一轮学习与接续。

资料由使用者提供，AI 仍可能误读、遗漏或错误反馈。记录帮助你检查过程，不能保证学会。一次正确作答只描述当次表现。

当前没有声称支持某一平台的自动加载，也没有外部试用结果。[验证记录](docs/验证记录.md)列出已做检查与未验证项。

## 检查文件

可选的 [检查工具](tools/check.py) 需要 Python 3.9 或以上，只使用标准库。从本项目目录运行：

```sh
python3 tools/check.py
python3 -m unittest discover -s tests -v
```

工具检查公开样稿的必需文件和简单内联本地链接；它不用于检查任意私人课程目录，也不证明 AI 接续可靠。链接目标中的标题锚点、外部网址、引用式链接和 HTML 不在检查范围；内联链接使用简单的路径写法。

## 反馈与来源

参考 [贡献说明](CONTRIBUTING.md)提供具体步骤、实际结果与期望结果。可以在 [Issues](https://github.com/desperado74/learning-os-starter/issues) 提供反馈。

设计参考见 [来源与设计取舍](docs/来源与设计取舍.md)。本项目采用 [MIT 许可](LICENSE)。

## English

Save your current learning position, actual answers, and next steps in Markdown so you can continue AI-assisted learning in a new chat.

### Why I’m sharing this project

This project grew out of Learning OS, a personal learning workspace I continue to use and refine. I’m sharing the methods, documents, and small tools I use so that others learning with AI can try them and help improve them through feedback.

The first version addresses a specific problem: how to leave a checkable record after a learning session so the next chat knows where to resume. The record keeps both what you did and what help you received. An exercise completed with hints still needs an independent check.

Start with one course: define the scope, keep your answers, write a handoff, and resume in a new chat. This repository includes blank templates, a worked example, and a file checker. The templates and supporting documents currently use Chinese; this English introduction explains how to use them, retaining the original filenames.

This is an early release. One explicit file-based continuation test in a separate Codex chat passed. A complete learning cycle and external user trials have not been validated.

### See an example

Open the [worked example](examples/markdown/README.md) to compare the starting state, answer record, and handoff from the same session.

In this fictional example, exercise A was completed independently, B with hints, and C remains unanswered. The next chat should begin with an independent check of B and keep C as pending. One test observed this behavior; see the full input and output in [continuation test 01](docs/接续测试-01.md).

### Start your own course

You only need a text editor to read and fill in the templates. Markdown is readable plain text; an editor with Markdown support can also render it.

1. Copy [学习主页.md — course overview](templates/学习主页.md), [当前模块.md — current module](templates/当前模块.md), and [交接.md — handoff](templates/交接.md) into a course directory of your choice. Keep these filenames. Your course directory can stay in your private workspace.
2. Fill in the course name and material references in the overview, and the session scope, tasks, and stopping point in the current module. For your first session, write “首次学习，暂无交接” (“First session; no previous handoff”) in the handoff and remove other unsupported placeholders.
3. Give the AI these three files, the [AI usage instructions](AI使用说明.md), and the required materials. Ask it to begin within the defined scope. Replace placeholders before use, or explicitly mark unknown information; a placeholder is not learning evidence.
4. During the session, save your original answers, hints received, and feedback in the current module. Review the record before updating the overview and handoff.
5. In a new chat, provide the updated files, usage instructions, and relevant materials, then send this continuation prompt:

```text
First read the AI usage instructions, course overview, current module, and handoff.
State the current position and next step, then continue from there.
Use actual answer records to distinguish independent completion, completion with hints,
and unfinished work.
If a record or material is unavailable, say what is missing. Do not treat missing
evidence as completed work.
```

If your AI tool can read local files, explicitly specify the course directory and usage instructions. In a regular chat, attach the files or paste their text as your tool allows. Do not assume the AI has already read them.

### File responsibilities

| File | Purpose |
| --- | --- |
| 学习主页 — course overview | Current materials, module, and a brief resumption point |
| 当前模块 — current module | Session scope, exercises, actual answers, and pending tasks |
| 交接 — handoff | Session outcome, remaining questions, and the next entry point |
| AI使用说明 — AI usage instructions | Shared rules for reading, feedback, and record keeping |

Maintain exercise-level status only in the current module. The overview and handoff refer to it rather than duplicating the exercise table. Close out a module before planning the next one.

### Scope and limitations

This is for people who want to learn with AI and are willing to keep a few files and check their records. The first version focuses on one course and its session-to-session continuation.

You supply the learning materials. AI can still misread, omit information, or give incorrect feedback. Records help you inspect the process; they do not guarantee learning. A correct answer describes that particular attempt.

Automatic loading on any platform is not claimed, and there are no external user trial results. The [validation record](docs/验证记录.md) lists completed checks and unvalidated areas. The English continuation prompt above is a translation and has not been separately tested.

### Check the files

The optional [file checker](tools/check.py) requires Python 3.9 or later and uses only the standard library. Run from this project directory:

```sh
python3 tools/check.py
python3 -m unittest discover -s tests -v
```

It checks required preview files and simple inline local links. It is not a checker for arbitrary private course directories and does not establish reliable AI continuation. Heading anchors, external URLs, reference-style links, and HTML are outside its scope. Use simple paths for inline links.

### Feedback and sources

See the [contribution guide](CONTRIBUTING.md) for how to report steps, observed results, and expected results. You can report feedback through [Issues](https://github.com/desperado74/learning-os-starter/issues).

Design references are documented in [sources and design choices](docs/来源与设计取舍.md). This project is available under the [MIT License](LICENSE).
