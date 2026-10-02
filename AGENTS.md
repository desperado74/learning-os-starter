# Learning OS 公开项目入口 / Public project entry

## 新用户初始化 / New-user setup

如果用户希望开始使用学习系统，先读 README.md 和 docs/本地初始化.md。当前完整系统仍为候选，不把初始化组件说成整套系统已完成。

分步询问目标、课程与实际起点，再问可选的爱好、习惯、时间和教材。用户可跳过，不问密钥，不扫描电脑寻找私人信息。不从模板或初始化推断掌握，不默认读旧工作区。

说明 manager 与 leaf 的职责，提出课程层级和独立私人目录；将用户确认的配置写在本公开仓库之外。先运行 init_workspace.py 的默认预览，展示准确写入清单，得到用户对清单的确认后才加 --apply。已有系统不初始化、不覆盖、不迁移。只记录用户提供的材料引用，不自动复制或上传教材。

创建后让用户在生成的私人目录或指定叶节点使用自己的 agent；核对入口确已读取，再核材料与学习起点。私人数据不得写入本公开仓库。

For setup requests, read README.md and docs/本地初始化.md. Discuss goals and courses first, then optional preferences and material references. Use a separate new private directory. Review the dry-run file list with the user before applying. Never modify an existing learning system or put private data in this repository. The full system is still a candidate.

## 项目开发 / Development

开发请求直接处理对应代码或文档，不向贡献者重复询问个人学习信息。相关检查：python3 tools/check.py 和 python3 -m unittest discover -s tests -v。只使用虚构测试数据，不运行任何现有私人系统的写入命令，不修改 agent 的全局配置或登录。

For development requests, work on the requested component and run relevant checks. Use fictional fixtures and isolated temporary workspaces. Never modify an active private system or global agent settings.
