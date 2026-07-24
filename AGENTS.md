# Git 分支与推送仓库

本项目的 Git remote 名称为 `origin`，地址为：

```text
https://github.com/EXphinx/manhuagui-downloader.git
```

`main` 和 `release` 当前使用同一个公开 GitHub 仓库，但必须推送到各自对应的远程分支：

- `main`
  - 用途：完整开发分支，包含项目开发资料和全部源文件。
  - 推送仓库：`https://github.com/EXphinx/manhuagui-downloader.git`
  - 远程分支：`main`
  - 推送命令：`git push origin main`
- `release`
  - 用途：公开发布分支，只保留编译、使用和发布需要的内容。
  - 推送仓库：`https://github.com/EXphinx/manhuagui-downloader.git`
  - 远程分支：`release`
  - 推送命令：`git push origin release`

创建版本标签和 GitHub Release 时，标签必须指向 `release` 分支中对应的发布提交，不要从 `main` 创建发布标签。

推送前必须检查当前分支和 push URL：

```bash
git branch --show-current
git remote get-url --push origin
```

不要把 `main` 推送到远程 `release`，也不要把 `release` 推送到远程 `main`。
