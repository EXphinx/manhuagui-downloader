# 漫画柜下载器

[English](README.md)

漫画柜下载器是一个本地运行的 ManhuaGui 下载应用。界面使用 React 和
Tauri，随应用打包的下载服务使用 Python 标准库。

## 功能

- 支持 `m.manhuagui.com` 和 `www.manhuagui.com` 漫画详情页；
- 读取带序号的完整章节列表；
- 可按序号范围、搜索结果、状态、最近章节或全部未下载章节选择；
- 章节依次进入任务队列，并显示图片下载和 ZIP 打包进度；
- 复用已下载图片和 `.part` 文件，中断后可以继续；
- 把任务状态保存在所选下载目录中；
- 每章完成后自动创建并校验 ZIP；
- 遇到人机验证时打开单独窗口，完成验证后重试；
- 同时提供桌面界面和命令行入口。

## 下载和使用

请从
[GitHub Releases](https://github.com/EXphinx/manhuagui-downloader/releases/latest)
下载最新安装包。

- **Windows x64：** 使用 `.exe` 安装程序；
- **Apple Silicon Mac：** 使用文件名含 `aarch64` 的 DMG；
- **Intel Mac：** 使用文件名含 `x64` 的 DMG。

`0.0.1` 安装包没有受信任的发布者证书，也没有经过 Apple 公证。Windows
SmartScreen 可能要求确认；macOS 如果阻止双击打开，可在第一次启动时右键
应用并选择“打开”。macOS 应用使用临时签名，Apple Silicon 可以检查应用内部
文件是否完整。

启动应用后：

1. 选择下载目录；
2. 粘贴 ManhuaGui 漫画链接；
3. 读取章节并选择要下载的章节；
4. 加入队列，完成的章节会保存为 ZIP。

## 下载目录

应用会把下载内容和可恢复任务状态保存在所选目录：

```text
所选目录/
├── .manhuagui/
│   └── tasks.json
└── 漫画名/
    ├── 001_章节名.zip
    └── .manhuagui-work/
```

重新选择同一目录时，未完成任务会继续。已经存在且非空的 ZIP 不会重复下载。

## 从源码编译

### 通用依赖

- Python 3.10 或更高版本
- Node.js 20 或更高版本
- pnpm 11
- Rust stable 工具链

安装 JavaScript 依赖：

```bash
corepack enable
pnpm install --frozen-lockfile
```

### Windows 编译依赖

请先安装：

- Visual Studio 2022 Build Tools，并选择 **Desktop development with C++**
- Windows 10 或 Windows 11 SDK
- Microsoft Edge WebView2 Runtime

在 PowerShell 中创建 Python 构建环境：

```powershell
py -3 -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip pyinstaller
pnpm desktop:build
```

安装包生成在：

```text
src-tauri\target\release\bundle\nsis\
```

### macOS 编译依赖

安装 Xcode Command Line Tools：

```bash
xcode-select --install
```

创建 Python 构建环境并打包：

```bash
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip pyinstaller
pnpm desktop:build
```

DMG 生成在：

```text
src-tauri/target/release/bundle/dmg/
```

PyInstaller 会创建当前处理器架构的 sidecar，因此两种 macOS 安装包需要在
对应架构的机器上分别编译。本项目的发布工作流会使用 Windows x64、macOS
Intel 和 macOS Apple Silicon 的 GitHub 托管运行器分别构建。

## 本地开发

启动浏览器开发模式：

```bash
pnpm dev
```

浏览器打开 `http://127.0.0.1:1420/`。启动 Tauri 桌面开发窗口：

```bash
pnpm desktop
```

本地接口只监听 `127.0.0.1:48135`。

## 命令行模式

```bash
python3 -m manhuagui_downloader \
  "https://m.manhuagui.com/comic/1325/" \
  --select 1-3
```

常用参数：

```text
-s, --select RANGE   章节范围，例如 1-5、1,3,8-10 或 all
-o, --output DIR     输出目录，默认 ./downloads
-j, --workers N      单章节图片并发数，默认 4
--list               只显示章节列表
```

## 测试

```bash
python -m unittest discover -v
pnpm test
pnpm build:web
```

请只下载你有权保存的内容，并遵守网站条款和当地法律。

## 许可证

[MIT](LICENSE)
