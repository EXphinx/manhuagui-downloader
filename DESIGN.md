---
name: 漫画柜下载器
description: 一个安静、紧凑、完全保存在本地的漫画下载工作台
colors:
  primary: "oklch(0.45 0.086 230)"
  primary-hover: "oklch(0.39 0.09 230)"
  primary-soft: "oklch(0.945 0.025 230)"
  canvas: "oklch(1 0 0)"
  surface: "oklch(0.978 0.004 230)"
  surface-raised: "oklch(0.995 0.002 230)"
  ink: "oklch(0.205 0.018 230)"
  ink-soft: "oklch(0.39 0.018 230)"
  muted: "oklch(0.505 0.016 230)"
  border: "oklch(0.895 0.009 230)"
  success: "oklch(0.46 0.095 156)"
  warning: "oklch(0.55 0.12 76)"
  danger: "oklch(0.5 0.16 25)"
  white: "oklch(1 0 0)"
typography:
  headline:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "clamp(1.35rem, 2vw, 1.625rem)"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 680
    lineHeight: 1.35
    letterSpacing: "-0.015em"
  subtitle:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 680
    lineHeight: 1.3
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  interface:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  control:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 580
    lineHeight: 1
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 620
    lineHeight: 1
    letterSpacing: "normal"
  caption:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 560
    lineHeight: 1.45
    letterSpacing: "normal"
  micro:
    fontFamily: "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 650
    lineHeight: 1
    letterSpacing: "normal"
rounded:
  xs: "0.25rem"
  sm: "0.375rem"
  md: "0.5rem"
  lg: "0.75rem"
  pill: "999px"
spacing:
  xs: "0.375rem"
  sm: "0.625rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "0 0.875rem"
    height: "2.5rem"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink-soft}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "0 0.875rem"
    height: "2.5rem"
  input:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 0.875rem"
    height: "2.625rem"
  state-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    rounded: "{rounded.lg}"
    padding: "0.25rem 0.5rem"
---

# Design System: 漫画柜下载器

## Overview

**Creative North Star: "安静的下载台"**

界面像一张整理过的桌面：链接、章节和队列各在明确的位置，信息密度高，但每个动作都有足够空间。视觉语言接近 Notion、shadcn/ui 与 Radix，使用熟悉的表格、复选框、进度条和确认对话框。

这是一个长时间运行的本地工具，不是展示页面。强调色只表示关键操作和活动状态；其余层级依靠排版、冷白表面、细分隔线与紧凑间距形成。系统明确拒绝传统下载器的拥挤感、重度影音管理器的复杂感，以及发光深色仪表盘的装饰。

**Key Characteristics:**

- 单一深港蓝强调色，只出现在关键操作与进行中状态。
- 紧凑的章节表格和独立队列，始终显示序号、状态与进度。
- 平面优先，以背景明度和 1px 分隔线组织层级。
- 控件保持标准行为，完整支持键盘焦点和减少动态效果。

## Colors

色彩以冷白纸面和石墨文字为主，深港蓝提供少量而明确的交互信号。

### Primary

- **深港蓝**：用于主要按钮、选中复选框、活动进度和品牌标记。
- **浅港雾**：用于已选择行、读取完成徽标与主色焦点外围。

### Secondary

- **完成绿**：仅表示任务或章节完成。
- **验证琥珀**：仅表示需要用户完成人机验证。
- **故障红**：仅表示失败、错误和有破坏性的确认动作。

### Neutral

- **冷白画布**：主内容背景，保持阅读区域清楚。
- **雾面表层**：工具栏、队列和表头背景，用明度区分区域。
- **石墨墨色**：标题和主要内容。
- **柔墨灰**：正文次要内容和控件文字。
- **细雾边界**：所有表格、面板和区域分隔线。

**The One Accent Rule.** 单个屏幕中，深港蓝只用于当前最重要的动作和活动状态；不要把它铺满大面积容器。

**The Semantic Color Rule.** 绿、琥珀和红只能表达状态，不能作为装饰主题色。

## Typography

**Display Font:** Inter / 系统无衬线字体  
**Body Font:** Inter / 系统无衬线字体  
**Label Font:** Inter / 系统无衬线字体

**Character:** 单一无衬线字族提供熟悉、直接的桌面工具感。层级来自字号、字重和间距，不依赖装饰字形。

### Hierarchy

- **Headline**（700，`clamp(1.35rem, 2vw, 1.625rem)`，1.25）：页面任务标题。
- **Title**（680，`1.125rem`，1.35）：漫画名称、对话框和主要分区标题。
- **Subtitle**（680，`1.25rem`，1.3）：启动和错误状态标题。
- **Body**（400，`1rem`，1.5）：说明和较长内容，行宽控制在约 65ch。
- **Interface**（650，`0.9375rem`，1.35）：应用品牌与队列标题。
- **Control**（580，`0.875rem`，1）：默认按钮、输入内容和表格行。
- **Label**（620，`0.8125rem`，1）：字段标签、按钮和紧凑工具栏。
- **Caption**（560，`0.75rem`，1.45）：摘要、次要说明和路径。
- **Micro**（650，`0.6875rem`，1）：进度数值和状态标签。

**The Quiet Hierarchy Rule.** 一个区域只允许一个最高层级标题；不要用多个大字号争夺注意力。

## Elevation

系统以平面表面和明度差组织层级。常驻区域不使用阴影；菜单、工具提示、通知和模态对话框在覆盖其他内容时，才使用低对比度的环境阴影。

### Shadow Vocabulary

- **浮层阴影**：用于下拉菜单、工具提示和通知，边缘轻、扩散范围大。
- **对话框阴影**：用于模态窗口，配合半透明遮罩建立唯一的顶层焦点。
- **启动面板阴影**：只在首次选择目录的单一面板使用极浅环境阴影。

**The Flat by Default Rule.** 静态表格、工具栏、页头和队列一律依靠 1px 边线或表面明度区分，不使用卡片阴影。

## Components

组件的共同特征是熟悉、紧凑和可核对；任何视觉变化都要对应真实状态。

### Buttons

- **Shape:** 轻度圆角（`0.5rem`），默认高度 `2.5rem`，紧凑工具按钮高度 `2.125rem`。
- **Primary:** 深港蓝背景、白色文字，只用于读取章节、创建任务和确认重试等主要动作。
- **Hover / Focus:** 悬停只加深背景；键盘焦点使用 2px 深港蓝轮廓。
- **Secondary / Ghost / Danger:** 次要按钮使用细边框，Ghost 只在悬停时出现雾面背景，Danger 只用于已确认的取消操作。

### Chips

- **Style:** 药丸形状态标签，小号字重，使用浅色语义背景和深色语义文字。
- **State:** 标签必须同时显示文字；不能只用颜色区分等待、下载、完成、失败或验证。

### Cards / Containers

- **Corner Style:** 大容器使用 `0.75rem`，常规控件使用 `0.5rem`。
- **Background:** 主区域为冷白画布，工具区域为雾面表层。
- **Shadow Strategy:** 常驻容器没有阴影，遵循 Elevation 章节。
- **Border:** 单一 1px 细雾边界。
- **Internal Padding:** 紧凑区域为 `0.625rem–1rem`，启动面板为 `2.25rem`。

### Inputs / Fields

- **Style:** 白色表面、1px 中性边线、`0.5rem` 圆角，标签始终位于字段外。
- **Focus:** 边线切换为深港蓝，并出现 3px 浅港雾外围。
- **Error / Disabled:** 错误使用故障红文字和浅红背景；禁用态降低不透明度，但保留可读标签。

### Navigation

应用页头高度固定，左侧显示品牌，右侧显示队列摘要和下载目录。窄屏时目录与队列摘要分成两行，不隐藏当前目录入口。

### Chapter Table and Task Queue

章节表头固定，序号使用等宽数字，选中行使用浅港雾。任务队列是独立的右侧栏，进度、状态、错误和人机验证入口均属于同一任务行；窄屏时队列移动到章节区域下方。

## Do's and Don'ts

### Do:

- **Do** 使用序号、标题、文字状态和已选数量，让章节选择可以逐项核对。
- **Do** 把主色限制在主要按钮、活动进度、选中控件和焦点轮廓。
- **Do** 使用 1px 分隔线和冷白表面组织高密度内容。
- **Do** 保持复选框、表格、进度条和确认对话框的标准交互。
- **Do** 在窄屏中把队列移到主内容下方，并保持最小 44px 触控目标。

### Don't:

- **Don't** 做成“信息拥挤的传统下载器”；每一行只显示执行任务所需的信息。
- **Don't** 做成“重度影音管理器”；不增加封面墙、媒体资料面板或多层导航。
- **Don't** 做成“充满发光效果的深色仪表盘”；禁止霓虹、玻璃拟态、渐变文字和装饰性发光。
- **Don't** “为了显得独特而改造复选框、表格、进度条和确认对话框等标准控件”。
- **Don't** 给常驻面板添加宽阴影、厚彩色侧边线或大面积主色背景。
