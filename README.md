---

# Cloudflare IP 优选工具

[![GitHub stars](https://img.shields.io/github/stars/xinyitang3/cfnb?style=social)](https://github.com/xinyitang3/cfnb/stargazers)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Last Commit](https://img.shields.io/github/last-commit/xinyitang3/cfnb?label=Last%20Commit)](https://github.com/xinyitang3/cfnb/commits)
[![Repo Size](https://img.shields.io/github/repo-size/xinyitang3/cfnb?label=Repo%20Size)](https://github.com/xinyitang3/cfnb)
[![Telegram](https://img.shields.io/badge/Telegram-@MiaChatChannel-26A5E4?logo=telegram)](https://t.me/MiaChatChannel)

> ⭐ **如果觉得好用，点个 Star 支持一下～**

这是一个全自动的 **Cloudflare CDN 节点优选工具**。它通过 **TCP 延迟筛选** + **IP 可用性二次检测** + **HTTP检测** + **真实带宽测速** 四重机制，从多个公开数据源中聚合节点，自动识别并解析任意格式（标准代码、中文名、emoji国旗、JSON等），筛选出当前网络环境下速度最快、可用性最高的 Cloudflare IP，并支持**自动更新至 Cloudflare DNS** 以及**同步至 GitHub 仓库**，同时支持微信实时通知。

> [!IMPORTANT]
> **跨平台支持**：本工具同时兼容 **Windows** 和 **Linux** 操作系统。
> - Windows 自动推送依赖 PowerShell 脚本 `git_sync.ps1`
> - Linux 自动推送依赖 Bash 脚本 `git_sync.sh`

---

### 📍 快速导航
- 🚀 [我要部署](#-部署步骤)（Windows / Linux 命令对照）
- 🔐 [我要获取 Token](#-获取必要令牌重要)（GitHub / Cloudflare / WxPusher 三合一教程）
- ⚙️ [我要调整参数](#%EF%B8%8F-配置说明完整参数详解)
- ☁️ [我要配置 Cloudflare DNS](#%EF%B8%8F-配置-cloudflare-dns-自动更新)
- 📤 [我要配置 GitHub 同步](#-配置-github-自动同步)
- 🔧 [Fork 后无法推送？一键修复](#-fork-后无法推送一键修复)
- 🔗 [对接 EdgeTunnel 指南](#-%E5%AF%B9%E6%8E%A5-edgetunnel-20-%E6%8C%87%E5%8D%97)
- ❓ [常见问题](#-常见问题)

---

## ✨ 功能特性

| 模块 | 说明 |
| :--- | :--- |
| 🌐 **多模式筛选** | 全局最优 TopN / 分国家最优 TopN |
| ⚡ **TCP 连接测试** | 并发测延迟，可设成功率阈值 |
| 🔍 **可用性二次检测** | API 验证代理能力 |
| 🔍 **HTTP检测** | 探测 HTTP 响应头，过滤非Cloudflare节点，提升代理兼容性 |
| 📶 **真实带宽测速** | curl 下载测速，实测吞吐量 |
| 🧩 **多源自适应聚合** | 支持多个数据源，自动识别并解析任意格式（标准代码、中文名、emoji国旗、JSON等），统一转换为标准格式 |
| ⚙️ **前置过滤（按序执行）** | TCP 测试前按序：端口过滤 → 黑名单过滤 → 白名单过滤（均可开关） |
| 🚫 **DNS 黑名单** | DNS 更新时剔除指定国家节点（**仅作用于 DNS 更新环节**） |
| 🛡️ **IPv6 落地过滤** | 过滤落地仅 IPv6 的节点，保留 IPv4/双栈节点（**仅作用于 DNS 更新环节**） |
| 🔍 **IP 风险等级过滤** | 仅允许低风险节点，高危自动回退（**仅作用于 DNS 更新环节**） |
| ☁️ **Cloudflare DNS 更新** | 原子批量替换同名 A 记录 |
| 📬 **微信实时通知** | 集成 WxPusher，异常/结果推送 |
| 🔄 **定时自动运行** | Windows 计划任务 / Linux cron，每 5 分钟 |
| 🚀 **一键部署** | `setup.ps1` / `setup.sh` 自动安装依赖并配置 |
| 📤 **GitHub 自动同步** | `ip.txt` 推送至仓库，方便订阅 |
| 🔒 **隐私保护** | `.gitignore` 忽略敏感文件 |
| 🖥️ **跨平台兼容** | 同时支持 Windows 和 Linux |
| 🔧 **Fork 修复** | 内置 `update_fork.ps1` / `update_fork.sh`，解决 fork 后的历史冲突与认证问题 |

---

## 📦 文件清单

| 文件 | 说明 |
| :--- | :--- |
| `main.py` | 核心优选程序（抓取、测试、筛选、更新、推送） |
| `config.json` | 所有运行参数的配置文件（含详细注释） |
| `git_sync.ps1` | Windows 推送脚本（强制推送 `ip.txt` 到 GitHub） |
| `git_sync.sh` | Linux 推送脚本（强制推送 `ip.txt` 到 GitHub） |
| `setup.ps1` | Windows 一键部署脚本（安装依赖并配置计划任务） |
| `setup.sh` | Linux 一键部署脚本（安装依赖并配置 cron） |
| `ip.txt` | 最终优选节点列表（每次运行覆盖） |
| `update_fork.ps1` | Windows 仓库修复脚本（解决 fork 后冲突/认证） |
| `update_fork.sh` | Linux 仓库修复脚本（解决 fork 后冲突/认证） |

---

## 🖥️ 系统要求

- **操作系统**：Windows 10+ / Windows Server 2016+ 或 Linux（Ubuntu/Debian/CentOS 等）
- **必备软件**：
  - **Python 3.7+**
  - **Git**
  - **curl**（需在系统 PATH 中可用）
- **Python 依赖**：`requests` 库

---

## 🚀 部署步骤

### 通用前置步骤

1. **获取项目文件**  
   - **方式一（推荐）**：点击本仓库页面的绿色 `Code` 按钮 → `Download ZIP`，下载压缩包后解压到本地。  
   - **方式二（熟悉 Git 的用户）**：使用命令行克隆仓库：
     ```bash
     git clone https://github.com/你的用户名/仓库名.git
     cd 仓库名
     ```

2. **配置各项令牌（见下一节）**  
   根据需求获取并填写 GitHub Token、Cloudflare API Token 和 WxPusher 凭证。

> 💡 部署脚本会自动安装依赖、创建 `.gitignore` 并配置定时任务（每 5 分钟整点运行）。

---

### 🔐 获取必要令牌（重要）

若你希望启用 GitHub 自动推送、Cloudflare DNS 更新或微信通知，请参考下表获取对应令牌。

| GitHub Personal Access Token | Cloudflare API Token | WxPusher 微信通知 |
| :---: | :---: | :---: |
| **1.** 登录 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) | **1.** 进入域名概览页，点击右侧API栏的获取您的 API 令牌 | **1.** 访问 [WxPusher 后台](https://wxpusher.zjiecode.com/admin/)，微信扫码登录 |
| **2.** Generate new token (classic)，Note 任意填 | **2.** 点击 创建令牌 → 选择 **编辑区域 DNS** 模板 | **2.** 左侧菜单“应用管理”→“应用信息”→“新增应用”，填写名称后创建 |
| **3.** **Expiration 必须选 `No expiration`** | **3.** 权限已自动填好（区域 - DNS - 编辑），区域资源选择你的域名 | **3.** 复制保存 AppToken（仅显示一次） |
| **4.** Select scopes: 仅勾选 **repo**（自动勾全） | **4.** 点击 继续以显示摘要 → 创建令牌 | **4.** 左侧“关注应用”→微信扫码关注公众号 |
| **5.** Generate token，保存 | **5.** 立即复制并保存令牌（仅显示一次） | **5.** 公众号菜单“我的”→“我的UID”获取 UID |
| 填入 `git_sync.ps1` / `git_sync.sh` 的 `github_token` | 填入 `config.json` 的 `CF_API_TOKEN` 和 `CF_ZONE_ID` | 填入 `config.json` 的 `WXPUSHER_APP_TOKEN` 和 `WXPUSHER_UIDS` |

> 💡 若不需要某项功能，可跳过对应步骤或在配置中关闭开关：  
> - 无需微信通知：`config.json` 中设 `ENABLE_WXPUSHER: false`  
> - 无需 GitHub 推送：`config.json` 中设 `GITHUB_SYNC_MAX_RETRIES: 0`  
> - 无需 Cloudflare DNS 更新：`config.json` 中设 `CF_ENABLED: false`

---

### Windows 部署

以管理员身份打开 **PowerShell**，逐行执行以下命令：

```powershell
# 1. 进入项目目录
cd "C:\你的项目路径\cfnb"

# 2. 若提示脚本禁用，临时绕过（可选）
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. 运行部署脚本
.\setup.ps1

# 4. 编辑推送脚本，填入 GitHub 令牌等信息
notepad git_sync.ps1

# 5. 测试运行
python main.py
```

### Linux 部署

在终端中逐行执行以下命令：

```bash
# 1. 进入项目目录
cd /path/to/cfnb

# 2. 赋予执行权限
chmod +x setup.sh

# 3. 运行部署脚本（需要 sudo 安装软件包）
sudo ./setup.sh

# 4. 编辑推送脚本，填入 GitHub 令牌等信息
nano git_sync.sh

# 5. 测试运行
python3 main.py
```

<details>
<summary>📝 手动部署详细步骤（点击展开）</summary>

#### Windows 手动部署

1. 安装 [Python 3](https://www.python.org/downloads/)（勾选 “Add Python to PATH”）。
2. 安装 [Git](https://git-scm.com/download/win) 和 [curl](https://curl.se/windows/)（curl 需加入 PATH）。
3. 在项目目录打开命令提示符，安装依赖：
   ```cmd
   pip install requests
   ```
4. （可选）手动创建计划任务：
   - 按 `Win + R`，输入 `taskschd.msc` 打开任务计划程序。
   - 创建任务，名称 `Cloudflare IP 优选`，勾选“不管用户是否登录都要运行”和“使用最高权限运行”。
   - 触发器：新建 → 开始任务“按预定计划” → 设置“一次”，开始时间为下一个整5分钟时刻；高级设置中勾选“重复任务间隔”，选择“5分钟”，持续时间“无限期”。
   - 操作：新建 → 操作“启动程序”，程序填写 `python.exe` 路径，参数填写 `main.py` 完整路径，起始于填写项目目录。
   - 在 **“设置”** 选项卡中，将 **“优先级”** 下拉框设为 **“高”**。
   - 点击确定，输入 Windows 登录密码保存。

#### Linux 手动部署

1. 安装系统依赖（以 Debian/Ubuntu 为例）：
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip git curl
   ```
2. 安装 Python 依赖：
   ```bash
   pip3 install requests
   ```
3. 赋予推送脚本执行权限（如果需要）：
   ```bash
   chmod +x git_sync.sh
   ```
4. （可选）添加 cron 任务：
   ```bash
   (crontab -l 2>/dev/null; echo "*/5 * * * * cd $(pwd) && nice -n -10 /usr/bin/python3 $(pwd)/main.py >> $(pwd)/cron.log 2>&1") | crontab -
   ```
5. 验证：`crontab -l`

</details>

---

## 🔧 Fork 后无法推送？一键修复

**适用于 fork 或修改远程仓库后，出现以下任一问题的情况：**

- `git pull` 报错：`fatal: refusing to merge unrelated histories`
- 推送时每次弹出浏览器要求登录

**运行对应平台的一键修复脚本即可**（前提：已按前文填写好 `config.json` 与推送脚本中的令牌）

| 平台 | 命令 |
| :--- | :--- |
| Windows PowerShell | `.\update_fork.ps1` |
| Linux | `chmod +x update_fork.sh && ./update_fork.sh` |

脚本会自动完成：
- 备份现有配置文件（可随时恢复）
- 设置免认证远程地址
- 强制对齐本地与远程仓库
- 将你的令牌安全注入最新版本的文件（不覆盖其他参数）

> 💡 运行成功后，`main.py` 即可正常自动推送，不再有任何冲突或弹窗。

---

## 🕒 定时自动运行说明

| 平台 | 方式 | 行为 |
| :--- | :--- | :--- |
| Windows | 计划任务 `Cloudflare IP 优选` | 从下一个整 5 分钟开始，之后每 5 分钟**永久重复** |
| Linux | cron 定时任务 | 分钟字段为 `*/5`，整点对齐 |

**日志查看**：
- Windows：任务计划程序中查看历史记录。
- Linux：`tail -f cron.log`

---

## ⚙️ 配置说明（完整参数详解）

> [!NOTE]
> 默认参数基于 **2核2G 云服务器** 测试通过。若在 **软路由、树莓派或低配 PC** 上运行，建议适当降低 `MAX_WORKERS`、`HTTP_TEST_WORKERS`、`BANDWIDTH_WORKERS`。

所有参数均位于 `config.json`，以下为逐项说明。

### 筛选模式与数量控制

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `USE_GLOBAL_MODE` | `boolean` | `true` | `true`=全局优选；`false`=分国家优选 |
| `GLOBAL_TOP_N` | `int` | `15` | 全局模式保留节点数 |
| `PER_COUNTRY_TOP_N` | `int` | `1` | 分国家模式每国保留节点数 |
| `BANDWIDTH_CANDIDATES` | `int` | `90` | 进入测速的候选节点数 |
| `DNS_UPDATE_TARGET_COUNT` | `int` | `15` | DNS 更新时写入的最大 IP 数量，独立于筛选模式 |

### TCP 连接测试参数

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `TCP_PROBES` | `int` | `3` | 每个节点 TCP 测试次数 |
| `MIN_SUCCESS_RATE` | `float` | `1.0` | 最低成功率阈值（0.0~1.0） |
| `TIMEOUT` | `float` | `2.0` | 单次 TCP 连接超时（秒） |
| `SOCKET_DEFAULT_TIMEOUT` | `int` | `3` | 全局 Socket 默认超时（秒），防止永久阻塞 |
| `PROGRESS_PRINT_INTERVAL` | `float` | `1` | 进度打印刷新间隔（秒），避免频繁 I/O |

### 前置过滤参数（TCP 测试前生效）

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `PRE_FILTER_PORT_ENABLED` | `boolean` | `true` | 是否启用前置端口过滤 |
| `PRE_FILTER_PORTS` | `array` | `[443]` | TCP 测试前允许的端口列表（可多个） |
| `PRE_FILTER_BLOCKED_ENABLED` | `boolean` | `true` | 是否启用前置黑名单过滤 |
| `PRE_FILTER_BLOCKED_COUNTRIES` | `array` | `["CN"]` | 前置黑名单国家代码列表（TCP 测试前剔除） |
| `FILTER_COUNTRIES_ENABLED` | `boolean` | `false` | 是否启用前置白名单过滤 |
| `ALLOWED_COUNTRIES` | `array` | `["US"]` | 前置白名单国家代码列表（仅在开关开启时生效） |

> 💡 过滤执行顺序：**前置端口过滤 → 前置黑名单 → 前置白名单**。  
> 所有前置过滤均在 TCP 测试前完成，可大幅减少无效测试。

### DNS 黑名单参数（仅作用于 DNS 更新环节）

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `FILTER_BLOCKED_COUNTRIES_ENABLED` | `boolean` | `true` | DNS 更新时是否启用黑名单过滤 |
| `BLOCKED_COUNTRIES` | `array` | `BD, BI, BY, CD, CF, CN, CU, DE, ET, HK,`<br>`IR, KP, LY, MO, NG, NL, PK, RU, SD, SO,`<br>`SY, TH, TW, UA, VE, VN, YE, ZW` | DNS 更新时需要剔除的国家代码列表（共 28 个） |
| DNS_IP_RISK_FILTER_ENABLED | `boolean` | `false` | 是否启用 IP 风险等级过滤 |
| DNS_IP_RISK_MAX_LEVEL | `string` | `高风险` | 允许的最高风险等级（可选：极度纯净、纯净、轻微风险、高风险、极度危险） |

> **说明**：  
> - 该过滤**仅作用于 Cloudflare DNS 批量更新环节**，不会影响 `ip.txt` 的内容和 GitHub 推送。  
> - DNS 更新时会**同时应用以下条件**，只有全部满足的节点才会写入 DNS：  
>   - 端口必须为 `443`  
>   - 落地不能仅为 IPv6（即保留 IPv4 或双栈节点，需开启 `FILTER_IPV6_AVAILABILITY`）  
>   - 国家不在 `BLOCKED_COUNTRIES` 黑名单中（需开启 `FILTER_BLOCKED_COUNTRIES_ENABLED`）  
>   - IP 风险等级不高于设定阈值（需开启 `DNS_IP_RISK_FILTER_ENABLED`，若过滤后无节点则自动回退到未过滤列表）

### 微信通知（WxPusher）参数

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `ENABLE_WXPUSHER` | `boolean` | `true` | 是否启用微信通知 |
| `WXPUSHER_APP_TOKEN` | `string` | `"your_app_token_here"` | **【必填】** WxPusher 的 APP_TOKEN |
| `WXPUSHER_UIDS` | `array` | `["your_uid_here"]` | **【必填】** 接收通知的用户 UID 列表 |
| `WXPUSHER_API_URL` | `string` | `"https://wxpusher.zjiecode.com/api/send/message"` | 消息发送 API 地址 |
| `NOTIFY_TIMEOUT` | `int` | `3` | 微信通知 API 读取超时（秒） |
| `NOTIFY_CONNECT_TIMEOUT` | `int` | `3` | 微信通知 API 连接超时（秒） |

> 💡 若不需要通知，将 `ENABLE_WXPUSHER` 设为 `false` 即可。

### Cloudflare DNS 批量更新参数

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `CF_ENABLED` | `boolean` | `true` | 是否启用 DNS 自动更新 |
| `CF_API_TOKEN` | `string` | `"your_CF_API_TOKEN"` | Cloudflare API 令牌（Zone:DNS:Edit 权限） |
| `CF_ZONE_ID` | `string` | `"your_CF_ZONE_ID"` | 域名区域 ID |
| `CF_DNS_RECORD_NAME` | `string` | `"your_CF_DNS_RECORD_NAME"` | 完整子域名 |
| `CF_TTL` | `int` | `60` | DNS 记录 TTL（秒） |
| `CF_PROXIED` | `boolean` | `false` | 是否启用 Cloudflare CDN 代理 |
| `CF_DNS_CONNECT_TIMEOUT` | `int` | `3` | Cloudflare API 连接超时（秒） |
| `CF_DNS_READ_TIMEOUT` | `int` | `3` | Cloudflare API 读取超时（秒） |
| `DNS_RECORD_TYPE` | `string` | `"TXT"` | DNS 记录类型（A 或 TXT） |

> 💡 若不需要 DNS 更新，将 `CF_ENABLED` 设为 `false` 即可。

### 节点数据源与获取配置

> [!NOTE]
> 本工具支持**多个数据源同时使用**，并内置了**完全自适应的解析引擎**。无论数据源是标准 `IP:端口#代码` 格式，还是中文标签、emoji国旗、JSON数组/对象，甚至是混合无关文字的标签，程序都能自动识别并统一转换为标准格式。添加新数据源只需在 `ADDITIONAL_SOURCES` 数组中新增一个对象，无需任何代码修改。

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `ADDITIONAL_SOURCES` | `array` | `[]` | 所有数据源列表，每个对象包含 `url`（必填）和 `enabled`（可选，默认true）。程序会自动识别并解析任何常见格式（标准代码/中文/emoji/JSON等） |
| `FETCH_MAX_RETRIES` | `int` | `3` | 获取节点列表失败时的最大重试次数 |
| `FETCH_RETRY_DELAY` | `int` | `3` | 获取节点列表重试间隔（秒） |
| `FETCH_TIMEOUT` | `int` | `3` | 获取节点列表读取超时（秒） |
| `FETCH_CONNECT_TIMEOUT` | `int` | `3` | 获取节点列表连接超时（秒） |
| `OUTPUT_FILE` | `string` | `"ip.txt"` | 最终结果保存文件名 |
| `ENABLE_LOGGING` | `boolean` | `false` | 是否启用运行日志（每次运行覆盖 LOG_FILE） |
| `LOG_FILE` | `string` | `"cfnb.log"` | 运行日志文件名（仅在启用日志时生效） |

<details>
<summary>🔧 高级参数（可用性 /HTTP / 带宽 / 并发 / 重试 / 广告/ 输出）</summary>

**可用性检测参数**

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `TEST_AVAILABILITY` | `boolean` | `true` | 是否进行可用性二次筛选 |
| `AVAILABILITY_CHECK_API` | `string` | `"https://api.090227.xyz/check"` | 可用性检测 API 地址 |
| `AVAILABILITY_TIMEOUT` | `int` | `3` | 可用性 API 读取超时（秒） |
| `AVAILABILITY_CONNECT_TIMEOUT` | `int` | `3` | 可用性 API 连接超时（秒） |
| `AVAILABILITY_RETRY_MAX` | `int` | `2` | 可用性检测最大重试轮数 |
| `AVAILABILITY_RETRY_DELAY` | `int` | `3` | 可用性检测重试间隔（秒） |
| `AVAILABILITY_INNER_RETRY_ENABLED` | `boolean` | `true` | 可用性检测是否启用单节点内部重试 |
| `AVAILABILITY_INNER_RETRY_MAX` | `int` | `2` | 可用性检测单节点内部最大重试次数 |
| `AVAILABILITY_INNER_RETRY_DELAY` | `int` | `3` | 可用性检测单节点内部重试间隔（秒） |
| `FILTER_IPV6_AVAILABILITY` | `boolean` | `true` | **仅作用于 DNS**：是否过滤落地仅 IPv6 的节点（`ipv6_only`） |

> 💡 IPv6 过滤逻辑：通过 API 返回的 `inferred_stack` 判断，仅淘汰 `ipv6_only` 节点，保留 `ipv4_only` 和 `dual_stack` 节点。

**HTTP 检测参数**

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `HTTP_TEST_ENABLED` | `boolean` | `true` | 是否启用 HTTP检测（过滤 HTTP 响应头非Cloudflare 的节点） |
| `HTTP_TEST_TIMEOUT` | `int` | `3` | 单次 HTTP 请求读取超时（秒） |
| `HTTP_TEST_CONNECT_TIMEOUT` | `int` | `3` | HTTP 检测的连接超时（秒），与读取超时分离 |
| `HTTP_TEST_INNER_RETRY_ENABLED` | `boolean` | `true` | HTTP 检测是否启用单节点内部重试 |
| `HTTP_TEST_MAX_RETRIES` | `int` | `2` | 单节点 HTTP 请求超时重试次数 |
| `HTTP_TEST_RETRY_DELAY` | `int` | `3` | HTTP 请求重试间隔（秒） |
| `HTTP_TEST_MAX_ROUNDS` | `int` | `2` | 整体失败（通过率为0）时的最大重试轮数 |
| `HTTP_TEST_ROUND_DELAY` | `int` | `3` | 整体重试间隔（秒） |
| `HTTP_TEST_METHOD` | `string` | `"HEAD"` | 请求方法（`GET` 或 `HEAD`） |

> 💡 HTTP 检测在可用性检测之后、带宽测速之前执行，仅淘汰非 `Code: 400` 和 `Server: cloudflare` 的节点，其余均视为可用。

**带宽测速参数**

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `BANDWIDTH_SIZE_MB` | `float` | `0.5` | 测速下载文件大小（MB） |
| `BANDWIDTH_TIMEOUT` | `int` | `3` | 单个节点带宽测速超时（秒） |
| `BANDWIDTH_RETRY_MAX` | `int` | `2` | 带宽测速整体重试轮数 |
| `BANDWIDTH_RETRY_DELAY` | `int` | `3` | 带宽测速重试间隔（秒） |
| `BANDWIDTH_URL_TEMPLATE` | `string` | `"https://speed.cloudflare.com/__down?bytes={bytes}"` | 测速 URL 模板 |
| `BANDWIDTH_PROCESS_BUFFER` | `int` | `2` | curl 进程额外缓冲时间（秒） |
| `BANDWIDTH_CONNECT_TIMEOUT` | `int` | `3` | curl 测速连接超时（秒） |

**并发控制参数**

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `MAX_WORKERS` | `int` | `200` | TCP 并发测试最大线程数 |
| `AVAILABILITY_WORKERS` | `int` | `32` | 可用性检测并发数 |
| `FALLBACK_WORKERS` | `int` | `32` | 备用国家查询的并发线程数（当标签无法识别时自动调用可用性API查询国家） |
| `HTTP_TEST_WORKERS` | `int` | `32` | HTTP 检测并发线程数 |
| `BANDWIDTH_WORKERS` | `int` | `10` | 带宽测速并发数 |

**重试策略配置**

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `DNS_UPDATE_MAX_RETRIES` | `int` | `3` | DNS 更新最大重试次数 |
| `DNS_UPDATE_RETRY_DELAY` | `int` | `3` | DNS 更新重试间隔（秒） |
| `GITHUB_SYNC_MAX_RETRIES` | `int` | `3` | GitHub 推送最大重试次数 |
| `GITHUB_SYNC_RETRY_DELAY` | `int` | `3` | GitHub 推送重试间隔（秒） |
| `GIT_SYNC_PROCESS_TIMEOUT` | `int` | `180` | Git 同步子进程最大运行时间（秒） |

#### 广告植入参数

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `AD_HEADER_ENABLED` | `boolean` | `false` | 是否在 `ip.txt` 头部插入自定义广告行 |
| `AD_HEADER_LINES` | `array` | `["0.0.0.0:443#格式 或纯文本1", "0.0.0.0:443#格式 或纯文本2"]` | 头部广告内容列表（可填任意格式） |
| `AD_FOOTER_ENABLED` | `boolean` | `false` | 是否在 `ip.txt` 尾部插入自定义广告行 |
| `AD_FOOTER_LINES` | `array` | `["0.0.0.0:443#格式 或纯文本3", "0.0.0.0:443#格式 或纯文本4"]` | 尾部广告内容列表（可填任意格式） |
| `AD_PERLINE_ENABLED` | `boolean` | `false` | 是否在每行节点末尾追加固定文本 |
| `AD_PERLINE_TEXT` | `string` | `" 纯文本"` | 追加到每行节点末尾的文本 |

> 💡 三个开关完全独立，头部/尾部可为多条，行尾为单条固定文本。  
> 开启后只会改变 `ip.txt` 内容，不影响 Cloudflare DNS 更新（DNS 仍使用纯净节点列表）。

#### ip.txt 输出内容控制

控制最终 `ip.txt` 文件中每行节点后是否附带带宽测速和 TCP 延迟信息，方便直接查看或用于其他工具解析。

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `IP_TXT_SHOW_BANDWIDTH` | `boolean` | `false` | 是否在每行末尾追加带宽测速结果（如 ` 5.20 Mbps`） |
| `IP_TXT_SHOW_LATENCY` | `boolean` | `false` | 是否在每行末尾追加 TCP 延迟信息（如 ` 50.30 ms`） |

> 两个开关可以独立或同时开启，输出格式示例：  
> `104.16.0.1:443#US 5.20 Mbps 50.30 ms`

</details>

> 💡 **快速配置建议**  
> - 通常只需修改 `ALLOWED_COUNTRIES`、`WXPUSHER_APP_TOKEN`、`WXPUSHER_UIDS`。  
> - 启用 DNS 更新需正确填写 `CF_API_TOKEN`、`CF_ZONE_ID`、`CF_DNS_RECORD_NAME`。  
> - 网络不稳定时可 ↑ `TCP_PROBES` / `TIMEOUT`，↓ `MIN_SUCCESS_RATE` / `MAX_WORKERS`。  
> - 希望更快出结果可 ↓ `BANDWIDTH_CANDIDATES` 或 `BANDWIDTH_SIZE_MB`。

---

## 📊 结果输出说明

程序运行完成后，会在本地生成 `ip.txt` 文件，每行格式为 `IP地址:端口#国家代码`，例如：

> `104.16.x.x:443#US`  
> `162.159.x.x:443#HK`

**重要说明**：  
- `ip.txt` 中保存的是**基于带宽测速排序的结果**，以确保 GitHub 推送的节点列表完整且不丢失任何高速 IP。  
- Cloudflare DNS 批量更新环节会额外应用 `FILTER_IPV6_AVAILABILITY`（过滤落地 IPv6）、`BLOCKED_COUNTRIES`（屏蔽特定国家）、`DNS_IP_RISK_FILTER_ENABLED`（IP 风险等级过滤，可设定最高允许等级，过滤后无节点自动回退到无风险过滤列表）等过滤，仅将符合条件的 IP 写入 DNS 记录。

---

## ☁️ 配置 Cloudflare DNS 自动更新

本工具支持将优选出的 IP 地址列表自动更新到 Cloudflare DNS 的同名 A 记录，实现解析层面的多 IP 轮询负载均衡。

### 第一步：获取 Cloudflare API Token 与 Zone ID

1. 按照 [获取必要令牌](#-获取必要令牌重要) 中的步骤获取 **Cloudflare API Token**（需具有 Zone:DNS:Edit 权限）。
2. 在 Cloudflare 域名概览页面右侧复制你的 **Zone ID**。

### 第二步：填写配置文件

编辑 `config.json`，找到 Cloudflare DNS 配置部分，填入你的信息：

```json
"CF_ENABLED": true,
"CF_API_TOKEN": "your_CF_API_TOKEN",
"CF_ZONE_ID": "your_CF_ZONE_ID",
"CF_DNS_RECORD_NAME": "your_CF_DNS_RECORD_NAME",
"CF_TTL": 60,
"CF_PROXIED": false
```

| 参数 | 说明 |
|------|------|
| `CF_ENABLED` | 设为 `true` 启用 DNS 自动更新 |
| `CF_API_TOKEN` | 上一步获取的 API Token |
| `CF_ZONE_ID` | 上一步获取的 Zone ID |
| `CF_DNS_RECORD_NAME` | 要更新的完整子域名 |
| `CF_TTL` | DNS 记录 TTL（秒），免费套餐最低 120 |
| `CF_PROXIED` | 是否启用 Cloudflare CDN 代理（橙色云朵），通常设为 `false` |

> 💡 若不需要 DNS 更新功能，将 `CF_ENABLED` 设为 `false` 即可。

### 第三步：测试运行

1. 手动运行一次优选程序：`python main.py`（Windows）或 `python3 main.py`（Linux）。
2. 程序运行结束后，观察控制台输出。若看到 `✅ Cloudflare DNS 批量更新成功！`，则配置成功。

### 工作原理

每次运行时，脚本会：

1. 查询目标子域名下现有的所有 A 记录。
2. 从带宽测速结果中按速度顺序挑选落地 IPv4 的节点（若启用 `FILTER_IPV6_AVAILABILITY`）。
3. 组装一个原子批量请求：同时删除所有旧记录并创建全部新记录。

### 注意事项

- 免费套餐单次批量操作最多支持 200 条记录，足够使用。
- 若候选池中落地 IPv4 节点不足目标数量，则更新实际可用的数量，不会强制凑满。
- 使用原子批量 API，单次请求完成删除和创建，可能存在极短暂的解析真空期（通常 1~5 秒）。

---

## 📤 配置 GitHub 自动同步

本工具支持每次运行后将 `ip.txt` 自动推送到你指定的 GitHub 仓库，方便通过 Raw 链接订阅节点列表。

### 第一步：创建 GitHub 仓库

1. 登录 GitHub，点击右上角 `+` → **New repository**。
2. **Repository name** 可任意填写（如 `cf-ip`）。
3. 仓库类型选择 **Private**（推荐）或 Public。
4. **不要**勾选 “Add a README file”、“.gitignore” 等初始化选项。
5. 点击 **Create repository**。

### 第二步：初始化本地仓库并关联远程

> 💡 **如果你是通过网页下载的 ZIP 压缩包解压的**，必须执行以下全部命令。  
> **如果你是用 `git clone` 命令下载的**，本地仓库已自动关联远程，可跳过此步，直接进入第三步。

根据你的操作系统选择对应标签页的命令，**在项目根目录**下打开终端执行：

#### **Windows（PowerShell）**

```powershell
# 1. 初始化仓库（若尚未初始化）
git init

# 2. 移除旧 origin 并添加你的远程地址（替换为你的仓库链接）
$null = git remote remove origin 2>&1
git remote add origin https://github.com/你的用户名/仓库名.git

# 3. 拉取远程数据并切换到默认分支（先 main 后 master）
git fetch origin
$null = git checkout main 2>&1
if ($LASTEXITCODE -ne 0) { $null = git checkout master 2>&1 }
```

#### **Linux （Bash）**

```bash
# 1. 初始化仓库（若尚未初始化）
git init

# 2. 移除旧 origin 并添加你的远程地址（替换为你的仓库链接）
git remote remove origin 2>/dev/null
git remote add origin https://github.com/你的用户名/仓库名.git

# 3. 拉取远程数据，对齐远程默认分支名
git fetch origin
git checkout -b temp-branch 2>/dev/null || git checkout main 2>/dev/null || git checkout master 2>/dev/null
git branch -M $(git remote show origin | grep "HEAD branch" | cut -d " " -f5) 2>/dev/null || git branch -M main
```

> ⚠️ **如果远程仓库是完全空的**（创建时未勾选任何初始化文件，无任何分支），上述命令会因没有可检出的分支而失败。  
> **解决方法**：先手动创建一个初始提交再重试：
> ```bash
> git commit --allow-empty -m "init"
> ```
> 然后再次执行上面的第 3 步。

### 第三步：获取并填写 GitHub Token

1. 按照 [获取必要令牌](#-获取必要令牌重要) 中的步骤获取 **GitHub Personal Access Token**（需勾选 `repo` 权限，过期时间设为 **No expiration**）。
2. 编辑对应平台的推送脚本：
   - **Windows**：用文本编辑器打开 `git_sync.ps1`
   - **Linux**：用文本编辑器打开 `git_sync.sh`
3. 将脚本开头部分的四个变量替换为你的真实信息：

   ```powershell
   # Windows (git_sync.ps1)
   $github_token = "your_github_personal_access_token_here"
   $github_username = "your_github_username"
   $repo_name = "your_repo_name"
   $branch = "your_branch"
   ```

   ```bash
   # Linux (git_sync.sh)
   github_token="your_github_personal_access_token_here"
   github_username="your_github_username"
   repo_name="your_repo_name"
   branch="your_branch"
   ```

### 第四步：测试推送

1. 确保项目目录下已有 `ip.txt` 文件（可先手动运行一次 `python main.py` 生成）。
2. 手动执行推送脚本测试：
   - **Windows**：双击运行 `git_sync.ps1` 或在 PowerShell 中执行 `.\git_sync.ps1`
   - **Linux**：执行 `./git_sync.sh`
3. 若终端显示 `✅ ip.txt 已推送到 GitHub`，则配置成功。
4. 之后每次运行 `main.py`，程序都会自动调用推送脚本，无需人工干预。

<details>
<summary>🚨 推送报错常见原因</summary>

| 报错信息 | 原因 | 解决方法 |
|----------|------|----------|
| `remote origin already exists` | 远程仓库已关联过 | 执行 `git remote set-url origin https://github.com/你的用户名/仓库名.git` 直接修改地址 |
| `failed to push some refs` | 远程有本地没有的文件（如 README） | 首次推送使用 `git push -f origin main` 强制覆盖（⚠️ 会删除远程多余文件） |
| `Permission denied` 或 `403` | Token 无效或权限不足 | 检查 Token 是否勾选 `repo` 权限，且未过期；重新生成 Token 并替换 |
| `src refspec main does not match any` | 本地分支名不是 `main` | 执行 `git branch` 查看实际分支名，修改推送脚本中的 `$branch` 变量与之相同 |
</details>

---

> [!WARNING]
> **关于私有仓库的特别提醒**
> 
> 如果你将仓库设置为 **Private（私有）**，则通过 Raw 链接访问 `ip.txt` 时必须在 URL 后附加 `?token=xxxxxx` 参数才能获取内容，例如：
> ```text
> https://raw.githubusercontent.com/用户名/仓库名/refs/heads/分支名/ip.txt?token=xxxxxx
> ```
> 但请注意，**部分代理工具或订阅解析器可能无法正确处理带 Token 参数的 URL**，原因包括：
> - 不支持自定义请求头（GitHub 要求完整的 User-Agent 等头信息）
> - 无法解析带查询参数的链接
> - 防火墙或网络环境限制
> 
> **因此，如果你希望将 `ip.txt` 作为订阅链接供代理工具使用，强烈建议将仓库设为 Public（公开）。**
> 
> 公开仓库的 Raw 链接无需 Token 即可访问，兼容性最佳：
> ```text
> https://raw.githubusercontent.com/用户名/仓库名/refs/heads/分支名/ip.txt
> ```

### 验证与订阅

推送成功后，访问 `https://raw.githubusercontent.com/你的用户名/仓库名/refs/heads/分支名/ip.txt` 即可获取最新节点列表，供代理工具订阅使用。

> 💡 若不需要 GitHub 同步功能，可在 `config.json` 中设置 `GITHUB_SYNC_MAX_RETRIES: 0` 即可关闭。

---

## 🚀 对接 EdgeTunnel (2.0+) 指南

**EdgeTunnel** (EDTunnel) 是基于 Cloudflare Workers 的隧道工具。使用本项目筛选出的 `ip.txt` 可以显著提升连接速度和稳定性。

### 方法一：优选订阅模式（推荐）

1. 复制你的 GitHub Raw 链接：
   ```text
   https://raw.githubusercontent.com/你的用户名/仓库名/refs/heads/分支名/ip.txt
   ```
2. 打开 EdgeTunnel 控制面板，点击菜单栏的 **“优选订阅生成”**。
3. 在 **“优选订阅模式”** 区域，选择 **“自定义订阅（支持汇聚订阅）”**。
4. 点击 **“订阅接口”** 按钮，在 **API URL** 输入框中粘贴上一步获取的 GitHub Raw 链接。
   > 💡 如需指定端口，可在链接后添加 `?port=443`。
5. （可选）勾选 **“将优选作为 PROXYIP”**。
6. 点击 **“可用性验证”**，系统将验证 API 并拉取节点列表。
7. 检查无误后，点击 **“追加API”** 按钮将链接加入自定义订阅地址。
8. 点击 **“保存”** 按钮完成配置。

### 方法二：手动替换 EdgeTunnel 节点配置

1. 打开 EdgeTunnel 控制面板，点击菜单栏的 **“优选订阅生成”**。
2. 在 **“优选订阅模式”** 区域，选择 **“自定义订阅（支持汇聚订阅）”**。
3. 在 **“自定义订阅地址”** 输入框中直接粘贴节点地址，每行一个，例如：
   ```text
   104.16.x.x:443#US
   162.159.x.x:443#HK
   ```
4. 点击 **“保存”** 按钮，即可手动指定优选的节点列表。

### 方法三：使用 Cloudflare DNS 域名（推荐）

如果你已启用 Cloudflare DNS 批量更新，可以直接将你的子域名（如 `cf.yourdomain.com`）填入 EdgeTunnel：

**方式一：通过“优选订阅生成”**
1. 打开 **“优选订阅生成”** 页面，选择 **“自定义订阅（支持汇聚订阅）”**。
2. 在 **“自定义订阅地址”** 输入框中，填入你的子域名（例如 `cf.yourdomain.com`）。
3. 点击 **“保存”** 按钮。

**方式二：通过“Cloudflare CDN 访问设置”**
1. 进入 **“Cloudflare CDN 访问设置”** 页面。
2. 在 **“PROXYIP”** 输入框中，填入你的子域名（例如 `cf.yourdomain.com`）。
3. 点击 **“保存”** 按钮。

该域名会自动解析到当前最优的多个 IP 之一，实现零配置动态切换。

### 💡 为什么这样对接更有效？
- **低延迟**：`main.py` 已经通过 TCP 握手筛选出了延迟最低的节点。
- **高带宽**：结果经过真实 `curl` 下载测试，排在前面的节点具有更强的并发吞吐能力。
- **高可用**：通过 `AVAILABILITY_CHECK_API` 过滤了那些能 Ping 通但无法正常通过代理请求的无效 IP。
- **自动更新**：DNS 记录随优选结果自动刷新，无需手动修改配置。

### 注意事项
- **GitHub 缓存**：GitHub Raw 链接有一定的 CDN 缓存时间（通常为 5 分钟左右）。如果刚运行完脚本发现链接内容没变，请稍等片刻。
- **网络环境**：建议在你的主运行环境（如家庭软路由或主力 PC）运行此脚本，因为不同网络环境下筛选出的最优 IP 可能不同。
- **DNS 生效时间**：修改 DNS 记录后受 TTL 影响，全球生效可能需要几分钟，但通常 Cloudflare 更新是实时的。

---

## ❓ 常见问题

<details>
<summary>🌐 代理环境影响</summary>

**会影响，尤其全局/TUN 模式。**

| 测试阶段 | 是否走代理 | 说明 |
| :--- | :--- | :--- |
| TCP 延迟测试 (Socket) | ❌ 直连 | 反映本机到节点的 RTT |
| HTTP 检测 (requests) | ✅ 跟随系统代理 | 过滤非Cloudflare节点 |
| 带宽测速 (curl) | ❌ 直连 | 反映本机到 CDN 的速度 |
| API 请求类 (requests) | ✅ 跟随系统代理 | 获取节点、可用性、微信通知等 |
| Git 推送 (git) | ✅ 跟随系统代理 | 涉及 `github.com` 等 |

> 各阶段对应域名见上方“涉及域名”列表。

**涉及域名：**  
`cm.edu.kg` · `090227.xyz` · `cloudflare.com` · `zjiecode.com` · `pages.dev` · `ipapi.is` · `github.com` · `githubusercontent.com`

**建议：**  
1. 检查本机能否直连上述域名 → 能通设 `DIRECT`，不通设 `PROXY`  
2. **运行程序时关闭全局模式 / TUN 模式**  
3. 不确定网络情况就直接**退出代理工具再运行**

</details>

<details>
<summary>🔌 依赖与安装</summary>

1. **提示 `ModuleNotFoundError: No module named 'requests'`**  
   请执行 `pip install requests` (Windows) 或 `pip3 install requests` (Linux)。

2. **带宽测速被跳过**  
   请确保系统已安装 `curl` 且位于 PATH 环境变量中。

3. **Linux 下 `git_sync.sh` 权限被拒绝**  
   执行 `chmod +x git_sync.sh` 赋予执行权限。

</details>

<details>
<summary>📤 GitHub 推送与同步</summary>

4. **GitHub 推送失败**  
   - 检查 `git_sync.ps1` / `git_sync.sh` 中的 Token、用户名、仓库名是否正确。
   - 确保 Token 具备 `repo` 权限。
   - 确认本地 Git 已正确配置用户信息（`git config --global user.name/email`）。

5. **GitHub 推送时提示权限错误或 403**  
   - 请确认令牌具有 `repo` 权限，且未过期。创建令牌时务必勾选 **repo** 全部子项，并将过期时间设为 **No expiration**。

6. **`git pull` 报错 `fatal: refusing to merge unrelated histories`**  
   - 通常发生在 Fork 或手动修改远程仓库后。运行对应平台的一键修复脚本即可：
     - Windows：`.\update_fork.ps1`
     - Linux：`./update_fork.sh`

7. **每次推送都弹出浏览器要求登录**  
   - 运行上述 `update_fork.ps1` 或 `update_fork.sh`，自动将远程地址设为免认证模式。

</details>

<details>
<summary>☁️ Cloudflare DNS 更新</summary>

8. **Cloudflare DNS 更新失败**  
   - 检查 `CF_API_TOKEN` 权限、`CF_ZONE_ID`、`CF_DNS_RECORD_NAME` 是否正确。  
   - 程序内置重试机制，全部失败时会通过微信通知（如已启用）。

9. **为什么我的 DNS 记录数量少于 `DNS_UPDATE_TARGET_COUNT`？**  
   如果你启用了 `FILTER_IPV6_AVAILABILITY`，且候选池中符合端口、落地类型、国家过滤等条件的节点总数不足你设定的 DNS 更新目标数量，则 DNS 只会更新实际可用的节点数。这是正常现象，你可以通过增加 `BANDWIDTH_CANDIDATES` 来扩大候选池。

10. **开启了风险等级过滤，但 DNS 更新似乎没有按预期过滤？**  
    - 检查 `DNS_IP_RISK_FILTER_ENABLED` 是否为 `true`，以及 `DNS_IP_RISK_MAX_LEVEL` 是否设置正确。  
    - 若 API 请求失败或所有节点均被过滤，程序会**自动回退到无风险过滤的列表**，并发送微信通知。  
    - 可以查看运行日志中的过滤统计信息确认过滤数量。

</details>

<details>
<summary>🔍 检测与过滤</summary>

11. **TCP 测试无节点通过**  
若所有节点的 TCP 连接成功率均低于 `MIN_SUCCESS_RATE`，程序将直接退出并提示检查网络或降低成功率阈值。此为第一道硬性门槛，无回退机制。

12. **可用性检测全部失败**  
若 API 接口异常导致可用性检测通过率为 0%，程序会自动跳过此步骤并回退到 TCP 筛选结果，同时发送微信提醒（如已配置）。

13. **HTTP检测全部失败**  
若所有候选节点均返回非 `400` / `cloudflare` 或连接失败，程序将降级使用过滤前列表（即可用性检测通过的结果），并发送微信通知（如已启用）。

14. **带宽测速全部失败**  
若 curl 测速多次重试仍无有效带宽数据，程序将回退到 TCP 延迟排序结果作为最终优选节点，并发送微信通知。

</details>

<details>
<summary>🔒 隐私与其他</summary>

15. **隐私保护**  
   自动生成的 `.gitignore` 文件会忽略 `config.json`、`git_sync.ps1` 和 `git_sync.sh`，防止敏感信息被提交到公开仓库。

</details>

---

## 🙏 致谢

- 节点数据源 & 检测 API：[cmliussss](https://github.com/cmliussss)
- IP 风险检测 API：[ipapi.is](https://ipapi.is/)
- 微信通知服务：[WxPusher](https://wxpusher.zjiecode.com/)

---

**许可证**：本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源。

---
