# 从首次设置到再次接续 / A complete file workflow

## 中文

这里演示完整流程：下载 → agent询问 → 建立私人工作区 → 核材料与规划 → 学习与作答 → 暂停 → 新聊天恢复 → 正式收尾 → 可选卡片/索引 → 下一模块待规划。

课程、教材、答案和用户习惯全部为虚构示例。脚本重放证明文件和工具能配合，不是AI教学测试，也不是实际用户学会的证据。

### 别人实际怎样使用

1. 下载项目并在自己的Codex或Claude Code打开它，发送：“请读AGENTS.md和本地初始化说明，带我建立自己的学习工作区，先不要写文件。”
2. agent先问目标、课程和起点，再问可选的爱好、习惯、时间和教材。用户选择私人目录，确认manager/leaf层级与生成清单；然后执行初始化。
3. 在生成的私人课程目录打开新聊天，发送：“先读本节点入口、主页和规则索引，核对我提供的材料。定位后规划一个模块，未核清的信息保留草案。”这里的平均数材料为原创纯文字，不涉及PDF核图；真实PDF仍按教材协议处理。
4. 学习过程中，A独立完成；B得到提示才完成；C尚未作答。用户说暂停，agent保存唯一模块状态、partial交接和准确下一步。它不能把三题都写成完成。
5. 新聊天只靠文件定位，首先独立核对B的方法选择，再做C；B的首次提示记录必须保留。缺文件或实际作答时明确询问，不凭编号猜进度。
6. 全部指定任务处理并反馈后，保存completed交接、更新主页、回读文件，交出填好路径的接续提示词。completed只描述范围已处理，不意味着长期掌握。
7. Anki未启用时只保留候选；启用并授权后才预览和导入。索引可按需重建，失败不影响Markdown。下一模块默认在新聊天核材料后规划，不自动开始。

### 本地重放

从公开项目根目录运行，选择一个不存在的独立目录：

```sh
python3 examples/full-cycle/demo.py --workspace ../learning-os-demo
# 核对虚构演示的文件清单后，再创建：
python3 examples/full-cycle/demo.py --workspace ../learning-os-demo --apply
```

默认预览不写入。脚本在新目录中按顺序写入虚构暂停状态、从磁盘读取、写入收尾状态、保存卡片候选、重建可选索引，并运行结构检查。保留暂停交接及首次提示历史。不调用模型，不连接Anki，不读取原作者工作区。

演示目录中最后状态可以用自己的agent检查，但不要把脚本生成的作答当成实际用户证据。开始自己的课程请走初始化流程，使用自己的教材与真实作答。

## English

The workflow is: download → agent-led intake → separate private workspace → verified materials and one module → learning and answers → partial handoff → file-based resumption → completed handoff → optional cards/index → next module planning.

All preferences, materials and answers here are fictional. The replay tests file and tool compatibility, not AI teaching or a learner's mastery.

Open the repository in your own Codex or Claude Code and ask it to read the setup instructions before writing anything. Discuss your goal, course and starting point, then optional habits and material references. Confirm the node hierarchy, private directory and write preview. Open the generated course and ask the agent to read its instructions, verify the supplied materials and plan one module.

In the demonstration, A is answered independently, B with a hint, and C is unanswered. Pausing saves a partial handoff. A new chat must retain this distinction, independently check B's method selection and then process C. It must keep the original hint history rather than overwrite it.

Once the assigned work and feedback are handled, save and read back a completed handoff, update the overview and deliver a filled-in continuation prompt. Completion describes the scope handled, not lasting mastery. Anki is optional and requires explicit configuration and authorization. The rebuildable index is also optional. Plan the next module in a new chat after checking materials.

Run the commands above to preview or create an isolated fictional replay. The script writes and reads fixture files, retains the partial handoff, saves a card candidate, builds the metadata index and checks structure. It invokes no model, connects to no Anki instance and accesses no original private system. Use your own materials and actual answers when setting up a real course.
