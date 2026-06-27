#!/bin/bash
# setup.sh - Cloudflare IP 优选工具 Linux 一键部署脚本
# 
# 用法：
#   chmod +x setup.sh
#   sudo ./setup.sh          # 推荐使用 sudo 以便安装软件包
#   或
#   ./setup.sh               # 若仅为当前用户配置定时任务，可不用 sudo

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================"
echo -e " Cloudflare IP 优选工具 - Linux 部署"
echo -e "========================================${NC}\n"

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo -e "工作目录: $SCRIPT_DIR\n"

# ==================== 配置 ====================
TASK_INTERVAL_MINUTES=5
PYTHON_SCRIPT="main.py"
# =============================================

# ---------- 辅助函数：检测命令是否存在 ----------
command_exists() {
    command -v "$1" &> /dev/null
}

# ---------- 管理员权限检查与友好提示（对齐 Windows 版） ----------
check_root() {
    if [[ $EUID -eq 0 ]]; then
        return 0  # 已是 root
    else
        echo -e "${YELLOW}⚠️  当前未以 root 身份运行。${NC}"
        echo -e "本脚本安装系统软件包需要管理员权限，建议使用 sudo 运行。"
        echo -e "如果您仅需为当前用户配置定时任务，也可以继续（但可能无法自动安装缺失的软件）。"
        echo ""
        read -p "是否继续以非 root 身份运行？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}请使用以下命令重新运行：${NC}"
            echo -e "  sudo ./setup.sh"
            echo ""
            exit 1
        fi
        return 1  # 非 root 但用户选择继续
    fi
}

check_root

# ---------- 1. 检测并安装系统依赖 ----------
echo -e "${GREEN}[1/4] 检查系统依赖...${NC}"

# 检测包管理器
if command_exists apt-get; then
    PKG_MANAGER="apt-get"
    INSTALL_CMD="sudo apt-get update; sudo apt-get install -y"
elif command_exists yum; then
    PKG_MANAGER="yum"
    INSTALL_CMD="sudo yum install -y"
elif command_exists dnf; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="sudo dnf install -y"
elif command_exists pacman; then
    PKG_MANAGER="pacman"
    INSTALL_CMD="sudo pacman -S --noconfirm"
else
    echo -e "${RED}❌ 未检测到支持的包管理器。${NC}"
    echo -e "请手动安装以下软件：python3, pip, git, curl"
    echo -e "然后重新运行本脚本。"
    exit 1
fi

# Python3
if command_exists python3; then
    echo -e "✅ Python3 已安装: $(which python3)"
else
    echo -e "${YELLOW}正在安装 Python3...${NC}"
    eval "$INSTALL_CMD python3"
    if ! command_exists python3; then
        echo -e "${RED}❌ Python3 安装失败，请手动安装后重试。${NC}"
        exit 1
    fi
fi

# pip3
if command_exists pip3; then
    echo -e "✅ pip3 已安装: $(which pip3)"
else
    echo -e "${YELLOW}正在安装 pip3...${NC}"
    eval "$INSTALL_CMD python3-pip"
    if ! command_exists pip3; then
        echo -e "${RED}❌ pip3 安装失败，请手动安装后重试。${NC}"
        exit 1
    fi
fi

# Git
if command_exists git; then
    echo -e "✅ Git 已安装: $(which git)"
else
    echo -e "${YELLOW}正在安装 Git...${NC}"
    eval "$INSTALL_CMD git"
    if ! command_exists git; then
        echo -e "${RED}❌ Git 安装失败，请手动安装后重试。${NC}"
        exit 1
    fi
fi

# curl
if command_exists curl; then
    echo -e "✅ curl 已安装: $(which curl)"
else
    echo -e "${YELLOW}正在安装 curl...${NC}"
    eval "$INSTALL_CMD curl"
    if ! command_exists curl; then
        echo -e "${RED}❌ curl 安装失败，请手动安装后重试。${NC}"
        exit 1
    fi
fi

echo ""

# ---------- 2. 安装 Python 依赖（requests, aiohttp, brotlicffi）----------
echo -e "${GREEN}[2/4] 检查并安装 Python 依赖...${NC}"

# 先升级 pip，保证安装过程顺利
python3 -m pip install --upgrade pip --quiet

# 检查并安装 requests
if python3 -m pip show requests &> /dev/null; then
    echo -e "  ✅ requests 已安装"
else
    echo -e "${YELLOW}  安装 requests...${NC}"
    python3 -m pip install requests --quiet
    if python3 -m pip show requests &> /dev/null; then
        echo -e "  ✅ requests 安装完成"
    else
        echo -e "${RED}  ❌ requests 安装失败，请手动执行: pip3 install requests${NC}"
        exit 1
    fi
fi

# 检查并安装 aiohttp
if python3 -m pip show aiohttp &> /dev/null; then
    echo -e "  ✅ aiohttp 已安装"
else
    echo -e "${YELLOW}  安装 aiohttp...${NC}"
    python3 -m pip install aiohttp --quiet
    if python3 -m pip show aiohttp &> /dev/null; then
        echo -e "  ✅ aiohttp 安装完成"
    else
        echo -e "${RED}  ❌ aiohttp 安装失败，请手动执行: pip3 install aiohttp${NC}"
        exit 1
    fi
fi

# 检查并安装 brotli 解压支持（优先 brotlicffi）
brotli_ok=false
if python3 -m pip show brotlicffi &> /dev/null; then
    echo -e "  ✅ brotlicffi 已安装"
    brotli_ok=true
elif python3 -m pip show brotli &> /dev/null; then
    echo -e "  ✅ brotli 已安装"
    brotli_ok=true
fi

if [ "$brotli_ok" = false ]; then
    echo -e "${YELLOW}  安装 brotlicffi（解压支持）...${NC}"
    if python3 -m pip install brotlicffi --quiet 2>/dev/null; then
        echo -e "  ✅ brotlicffi 安装完成"
    else
        echo -e "${YELLOW}  ⚠️ brotlicffi 安装失败，尝试安装 brotli...${NC}"
        python3 -m pip install brotli --quiet
        if python3 -m pip show brotli &> /dev/null; then
            echo -e "  ✅ brotli 安装完成"
        else
            echo -e "${RED}  ❌ brotli 解压库安装失败，请手动执行: pip3 install brotlicffi${NC}"
            exit 1
        fi
    fi
fi
echo ""

# ---------- 3. 创建 .gitignore 保护隐私 ----------
echo -e "${GREEN}[3/4] 创建 .gitignore...${NC}"
cat > .gitignore << 'EOF'
config.json
git_sync.ps1
git_sync.sh
__pycache__/
EOF
echo -e "✅ .gitignore 已创建\n"

# ---------- 验证 main.py 是否存在 ----------
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ 错误：未找到 $PYTHON_SCRIPT 文件，请确保脚本位于正确目录。${NC}"
    exit 1
fi

# ---------- 4. 配置 cron 定时任务 ----------
echo -e "${GREEN}[4/4] 配置定时任务（每${TASK_INTERVAL_MINUTES}分钟运行一次）...${NC}"

calc_next_aligned() {
    local interval=$1
    local current_min=$(date +%M)
    local current_hour=$(date +%H)
    local next_min=$(( ((current_min / interval) + 1) * interval ))
    local next_hour=$current_hour
    if [ $next_min -ge 60 ]; then
        next_min=0
        next_hour=$(( (next_hour + 1) % 24 ))
    fi
    printf "%02d:%02d" $next_hour $next_min
}

NEXT_RUN=$(calc_next_aligned $TASK_INTERVAL_MINUTES)
echo -e "   首次运行将发生在: ${CYAN}$NEXT_RUN${NC}（之后每 ${TASK_INTERVAL_MINUTES} 分钟运行一次）"

CRON_MINUTE_FIELD="*/5"
PYTHON_PATH=$(which python3)

if [[ $EUID -eq 0 ]]; then
    NICE_PREFIX="nice -n -20"
    echo -e "   运行优先级: 高 (nice -n -20)"
else
    echo -e "${YELLOW}⚠️  非 root 用户，cron 任务将以默认优先级运行。${NC}"
    NICE_PREFIX=""
fi

CRON_CMD="$CRON_MINUTE_FIELD * * * * cd \"$SCRIPT_DIR\" && $NICE_PREFIX \"$PYTHON_PATH\" \"$SCRIPT_DIR/$PYTHON_SCRIPT\" >> \"$SCRIPT_DIR/cron.log\" 2>&1"
CRON_COMMENT="# Cloudflare IP 优选工具定时任务（每5分钟，整点对齐）"

if crontab -l 2>/dev/null | grep -F "$SCRIPT_DIR/$PYTHON_SCRIPT" > /dev/null; then
    echo -e "${YELLOW}⚠️ 定时任务已存在，跳过添加。${NC}"
else
    (crontab -l 2>/dev/null || true; echo "$CRON_COMMENT"; echo "$CRON_CMD") | crontab -
    echo -e "${GREEN}✅ 定时任务已添加（每${TASK_INTERVAL_MINUTES}分钟，从下一个整5分钟开始）${NC}"
fi

echo -e "   执行命令: $NICE_PREFIX $PYTHON_PATH $SCRIPT_DIR/$PYTHON_SCRIPT"
echo -e "   日志文件: $SCRIPT_DIR/cron.log"
echo ""

if [ -f "git_sync.sh" ]; then
    chmod +x git_sync.sh
    echo -e "✅ 已赋予 git_sync.sh 执行权限"
fi

echo ""
echo -e "${CYAN}========================================"
echo -e " 🎉 部署完成！"
echo -e "========================================${NC}\n"
echo -e "${YELLOW}👉 接下来请完成以下手动配置步骤：${NC}"
echo -e "1. 编辑 config.json，填写 WxPusher 的 APP_TOKEN 和 UID（如需通知）"
echo -e "2. 编辑 git_sync.sh，填写你的 GitHub Token、用户名及仓库名"
echo -e "3. 手动运行一次测试: ${CYAN}python3 main.py${NC}"
echo -e "4. 查看定时任务日志: ${CYAN}tail -f cron.log${NC}"
echo -e "5. 管理定时任务: ${CYAN}crontab -e${NC}"
echo ""

read -p "是否立即运行一次 main.py 进行测试？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}正在运行 main.py ...${NC}"
    python3 "$PYTHON_SCRIPT"
fi

exit 0