# ComfyUI-Mutiny

[English](README.md) | **简体中文**

这是 **ComfyUI-Mutiny**，一个面向 ComfyUI 的非官方 Midjourney 集成插件。

如果你的创作流程同时依赖 Discord 和 ComfyUI，那你大概很清楚这种折腾：素材总是在 Midjourney 聊天窗口或 MJ 网站与 Comfy 工作流之间来回搬运。这样的人不算多，但我确实见过，而这种来回折返会持续浪费大量时间和精力。

ComfyUI-Mutiny 的目标，就是把你的 Midjourney 订阅所提供的强大功能带进 ComfyUI，并通过一组专用节点把云端流程和本地流程串起来。你可以直接用 Midjourney 或 Niji 请求节点生成图像，用扩散放大或基于 SAM 的局部重绘进一步处理，再把结果送回 MJ 做动画。

![Mutiny intro workflow](docs/images/text_to_image.webp)

## Features

 - 通过一组自定义节点将 Midjourney 集成进你的 ComfyUI 工作流中。MJ 的核心概念已经完整映射到 ComfyUI 的使用习惯
 - 支持截至 2026 年 3 月的全部 Discord 版 MJ 功能，包括 Vary by Region 和 Animate
 - 完整支持进度更新和实时预览，使这些节点的使用体验更接近原生 `ksampler` 节点
 - 会记住哪些图像直接来自 Midjourney。这意味着你稍后再回到这些图像时，Mutiny 依然知道哪些 MJ 操作对该图像（或视频）有效
 - 节点控件按不同 MJ 版本提供上下文化配置，更容易理解；你可以直接看到每个模型可用的 MJ 命令范围，而不需要全部死记硬背
 - 完整支持图像提示：只需把图像连接到相关节点的不同图像输入上，就可以用图像参与提示
 - 具备负责的安全姿态：会将你的 Discord token 保存在运行 ComfyUI 的那台机器的操作系统安全凭据存储中。Mutiny 永远不会把你的 token 写进工作流，也不会把它打印到 ComfyUI 控制台日志中

## Installation

**推荐：通过 ComfyUI Manager 安装**

在 ComfyUI 工具栏中打开 **🧩 Manager**，点击 **Custom Nodes Manager**，搜索 **Mutiny**，然后点击 **Install**。安装完成后重启 ComfyUI。

**手动安装**

如果你更愿意手动安装，请将此仓库克隆到 `ComfyUI/custom_nodes/`，激活你的 **ComfyUI venv**，然后安装本节点的依赖。ComfyUI 已经提供了大多数共享运行时依赖；本插件额外需要 `mutiny-sdk` 和 `keyring`。

```powershell
cd ComfyUI\custom_nodes
git clone https://github.com/Artificial-Sweetener/ComfyUI-Mutiny.git
cd ComfyUI-Mutiny
pip install -r requirements.txt
```

## Important Disclaimer

Mutiny 与 Discord 和 Midjourney 的交互方式，可能会被解释为违反它们的服务条款。**我们不对安全性作任何保证。** 使用 Mutiny 可能会导致你的 Discord 账号、Midjourney 账号，或两者同时遭到处理，包括警告、限制或封禁。

尽管如此，Mutiny 的设计目标仍然是礼貌且保守地运行。它并非为了刷屏、猛打接口、规避限制或进行滥用行为。我们并不预计大多数正常用户会因此遇到问题，但我们也无法作出承诺。是否使用，以及要承担哪些风险，必须由你自己判断。

Mutiny 运行时需要你的 **Discord token**。那属于敏感的账户访问资料。处理它本身就带有风险；如果它被泄露或处理不当，其他人就可能获得对你 Discord 账号的访问权限。Mutiny 会采取合理的预防措施，把 token 保存在你的操作系统安全凭据存储中，但任何存储方式都不是零风险，你仍然需要自行负责保护自己的账号。

Mutiny 还需要一个**已付费的 Midjourney 账号**。它不是免费使用 Midjourney 的方式。它也不是为了绕过 Midjourney 的审核系统、付费要求、速率限制或其他平台限制而设计的。它不适用于运行多个账号，也不适用于跨多个账号自动化活动。Mutiny 面向的是单个用户使用自己的账号进行正当使用。

## First-Time Setup

ComfyUI-Mutiny 在正式起航之前需要做一点配置。

打开 ComfyUI Settings，找到 **Mutiny** 部分。在这里配置：

- **Guild ID**：Mutiny 应该使用的 Discord 服务器。
- **Channel ID**：Mutiny 应该提交任务所使用的 Discord 频道。
- **Discord Token**：Discord 用来识别并验证你当前登录会话的私密账户凭据。**这实际上等同于把你的用户名和密码合并成一个值**。Mutiny 会把你提供的 token 保存到操作系统的安全凭据存储中。
> 本项目**不会**提供如何获取 Discord token 的说明。在决定是否将 token 与 Mutiny 一起使用之前，请先阅读上面的免责声明。
- **User Agent** 和 **API Endpoint**：面向高级场景的可选覆盖项。大多数情况下你可以保持默认。
- **Artifact Cache RAM** 和 **Artifact Disk**：控制 Mutiny 为识别先前 Midjourney 输出而保留多少上下文。
- **Task Timeout Minutes**：控制 ComfyUI 在运行中的任务超时之前等待多久。

缓存的重要性比一开始听上去更高。Mutiny 会使用缓存中的识别数据来判断图像或视频是否来自先前的 Midjourney 任务，而这正是 **Upscale**、**Variation**、**Pan**、**Zoom** 和 **Extend** 这类后续操作能够表现得像真正延续，而不是盲目猜测的基础。

## The Nodes

这一组节点的目标，是覆盖完整的 Midjourney 流程，从第一次提示一直到后续操作。

### Prompt Captains

请求节点就是你用来根据提示词提交 Midjourney 或 Niji 任务的节点。

Mutiny 为 **Midjourney v4、v5、v6、v7**，以及 **Niji 4、5、6、7** 都提供了专门的请求节点。每一个节点都围绕该版本的真实规则来设计，所以控件会对应那个版本实际支持的能力。你看到的不是一个通用提示表单再套一个版本下拉框，而是会随着模型变化而变化的输入界面。

这很重要，因为这些版本并不都支持相同的宽高比规则、质量控制、风格控制、参考图特性或其他提示参数。版本专用的请求节点会把这些差异处理掉，这样你只会看到适用于所选版本的控件。

这些请求节点中的大多数还提供了一个 **custom args** 输入。它是一个直接的逃生口，让你可以传入 Mutiny 还没有做成一等控件、但 Midjourney 本身已经支持的参数。

Mutiny 另外还包含：

- **Midjourney v8 Alpha Request**：面向当前 v8 alpha 界面的更精简节点
- **Midjourney Custom Request**：当你想自己填写版本字符串、更手动地构造请求，或者在 Midjourney 已经支持某项能力但 Mutiny 还没来得及做出专用控件时使用的兜底节点

简短地说：这些请求节点的存在，就是为了让你不必死记硬背不同 Midjourney 或 Niji 版本到底支持哪些参数；而在你需要更多控制时，仍然可以退回到 **custom args** 或 **Custom Request**。

### Reference Keepers

这些节点会为图像附加 Midjourney 特有的语义，让请求节点保持整洁，也让你的工作流更易读。

- **Midjourney Image Prompt**：附加一张提示图像，并可选设置 image-weight。
- **Midjourney Style Reference**：附加风格参考图、可选 style weight、可选 style version，以及可选的逐图倍率。
- **Midjourney Character Reference**：附加一张或多张角色参考图，并可选设置 character weight。
- **Midjourney Omni Reference**：附加一张 Omni 参考图，并可选设置 Omni weight。
> 提示：想一次用多张图来做提示？只要 Midjourney 本身支持，Mutiny 就支持；不过你需要先把这些图像整理成一个批次集合。能做到这一点的节点有很多，你可以按自己顺手的方式来选。

这些是胶水节点。它们本身不会单独生成图片，但能让工作流的其他部分以正确的 Midjourney 方式交流。

### Follow-Up Actions

这部分是 Mutiny 在 ComfyUI 里开始变得特别顺手的地方。

这些节点作用于 **已识别的 Midjourney 输出**，借助 Mutiny 的缓存和任务上下文，把正确的后续操作提交到正确的来源对象上。

- **Midjourney Upscale**：对已识别的 Midjourney 结果执行 Standard、Subtle 或 Creative 放大模式。
- **Midjourney Variation**：对已识别的 Midjourney 网格分块提交 Standard、Subtle 或 Strong variation 操作。
- **Midjourney Pan**：将已识别的 Midjourney 图像向某个方向继续扩展。
- **Midjourney Zoom**：把已识别的 Midjourney 图像提交到 Zoom，支持精确缩放因子和可选提示文本。
- **Midjourney Vary Region**：使用新的提示词编辑已识别 Midjourney 图像中的蒙版区域。

这一点很重要：这些不是通用图像滤镜。如果你给它们的图像无法被 Mutiny 识别为其缓存 Midjourney 历史的一部分，它们会明确失败，而不是假装可以处理。

### Signals and Motion

Midjourney 的输出不止一种，这些节点补全了整套能力。

- **Midjourney Describe**：把任意图像发送给 Midjourney Describe，并取回提示词文本。
- **Midjourney Animate**：把起始帧转换为原生 ComfyUI `VIDEO`，可选结束帧、提示词、负向提示词和批处理控制。
- **Midjourney Extend**：基于已识别的 Midjourney 视频，按你选择的运动强度继续延展。

这些节点组合起来，可以让你在图像提示、提示词恢复和短视频工作流之间切换，而无需离开工作流图。

## A Note on Recognition

Mutiny 会跟踪 Midjourney 任务，以便后续操作始终绑定到真实的来源上下文。因此，有些节点会非常依赖来源信息。

- **Request** 和 **Describe** 节点可以从全新的输入开始。
- **Upscale**、**Variation**、**Pan**、**Zoom** 和 **Extend** 依赖 Mutiny 从缓存中识别输入图像或视频。
- **Vary Region** 使用一张已识别的 Midjourney 源图像和一个蒙版，以便通过正确的 Midjourney 路径提交编辑。

如果你把这些操作节点理解成“继续处理我已经做出来的那个 Midjourney 结果”，那你的理解就是完全正确的。

## License

**ComfyUI-Mutiny** 采用 GNU Affero General Public License v3.0（**AGPL-3.0**）许可。请阅读本仓库附带的完整 [LICENSE](LICENSE)。AGPL-3.0 是一种强 copyleft 许可证。如果你分发本软件，就必须提供对应源代码；如果你让用户通过网络与修改后的版本交互，你也必须提供该修改版本对应的源代码。

## From the Developer 💖

告诉你一个小秘密……我其实自己并不怎么用 Midjourney！我之所以做这些节点，是因为我有很多很棒的朋友在用，而我知道像这样的东西对他们会很有帮助。另外，这个挑战本身也挺有意思。

我研究过很多不同的方案，但最后还是决定自己做一个 [Python library](https://github.com/Artificial-Sweetener/Mutiny-SDK)，然后围绕它来构建这些节点。如果我当时不这么做，现在这个项目会比现在笨重得多。

话虽如此，因为我并不是常规的 MJ 用户，而且它也不是免费的，所以这个项目后续能不能持续维护，很大程度上取决于我是否负担得起继续做下去。Mutiny 由于其本质原因天生就比较脆弱，将来非常有可能出现损坏并需要维护。

如果这个项目对你有帮助，而你也负担得起，可以考虑在 [Ko-Fi](https://ko-fi.com/artificial_sweetener) 请我喝杯咖啡，或者在 [Patreon](https://www.patreon.com/ArtificialSweetener) 支持我。

如果你暂时做不到这些，但仍然想帮忙，我也非常欢迎你在社交媒体上支持我。你可以在 [我的网站](https://artificialsweetener.ai) 找到我的链接。如果你能在 GitHub 上给这个项目点一个 star，我也会非常感激。

谢谢！
