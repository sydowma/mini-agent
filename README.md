# Mini Agent

[English](#english) | [中文](#中文)

---

<a name="english"></a>

## English

A Python coding AI agent with TUI interface, inspired by Claude Code.

### Features

- **Multi-provider support**: OpenAI, Anthropic Claude, and Zhipu AI (GLM)
- **Rich TUI interface** built with Textual framework
- **Session management** with persistence - save and load conversations
- **Core coding tools**:
  - `read` - Read file contents
  - `write` - Write/create files
  - `edit` - Make targeted edits to existing files
  - `bash` - Execute shell commands
  - `grep` - Search file contents with regex support
  - `find` - Find files by name pattern
  - `ls` - List directory contents
- **Multiple running modes**: Interactive TUI, print mode, JSON mode
- **Library usage**: Can be imported and used as a Python library
- **Docker support**: Ready-to-use Docker and Docker Compose configurations

### Installation

#### Using uv (Recommended)

```bash
# Clone the repository
git clone git@github.com:sydowma/mini-agent.git
cd mini-agent

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

#### Using pip

```bash
pip install -e ".[dev]"
```

### Configuration

#### Using .env File (Recommended)

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# For Zhipu AI
ANTHROPIC_API_KEY=your_zhipu_api_key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
DEFAULT_MODEL=glm-4-plus

# For Anthropic Claude
# ANTHROPIC_API_KEY=your_anthropic_api_key
# DEFAULT_MODEL=claude-sonnet-4-20250514

# For OpenAI
# OPENAI_API_KEY=your_openai_api_key
# DEFAULT_MODEL=gpt-4o
```

The `.env` file is loaded from:
1. Current directory: `./.env`
2. Home directory: `~/.mini-agent/.env`

### Usage

#### Interactive TUI Mode

```bash
# Start interactive TUI (default: Claude Sonnet 4)
mini-agent

# Use GPT-4o
mini-agent -m gpt-4o

# Use Claude 3.5 Sonnet
mini-agent -m claude-3-5-sonnet

# Use Zhipu GLM
mini-agent -m glm-4-plus

# Explicitly specify provider
mini-agent -p anthropic -m claude-sonnet-4-20250514
mini-agent -p openai -m gpt-4o

# Load a saved session
mini-agent -s abc12345
```

#### Command Line Options

```bash
# List available providers
mini-agent --list-providers

# List saved sessions
mini-agent --list-sessions

# Print mode (read from stdin)
echo "What files are in this directory?" | mini-agent --mode print

# JSON mode (for programmatic use)
echo "Explain this code" | mini-agent --mode json
```

#### As a Library

```python
import asyncio
from mini_agent.agent import Agent
from mini_agent.tools import ReadTool, WriteTool, BashTool

async def main():
    # Use Claude (default)
    agent = Agent(model="claude-sonnet-4-20250514", provider_name="anthropic")

    # Or use OpenAI
    # agent = Agent(model="gpt-4o", provider_name="openai")

    # Or use Zhipu AI
    # agent = Agent(model="glm-4-plus", provider_name="anthropic")

    agent.add_tools([ReadTool(), WriteTool(), BashTool()])

    response = await agent.prompt("What files are in the current directory?")
    print(response.text)

asyncio.run(main())
```

### Supported Models

#### OpenAI
- `gpt-4o`, `gpt-4o-mini`
- `gpt-4-turbo`, `gpt-4`
- `gpt-3.5-turbo`
- `o1`, `o1-mini`, `o1-preview`

#### Anthropic
- `claude-sonnet-4-20250514` (default)
- `claude-3-5-sonnet-20241022`, `claude-3-5-sonnet`
- `claude-3-5-haiku-20241022`, `claude-3-5-haiku`
- `claude-3-opus-20240229`, `claude-3-opus`
- `claude-3-sonnet-20240229`, `claude-3-sonnet`
- `claude-3-haiku-20240307`, `claude-3-haiku`

#### Zhipu AI (via Anthropic-compatible API)
- `glm-4-plus`, `glm-4-air`, `glm-4-airx`, `glm-4-flash`, `glm-4-long`
- `glm-4v-plus`, `glm-4v-flash` (vision models)
- `glm-z1-air`, `glm-z1-airx`, `glm-z1-flash` (reasoning models)

> Provider is auto-detected from model name.

### Docker

#### Build and Run

```bash
# Build the image
docker build -t mini-agent:latest .

# Run with OpenAI
docker run -it --rm \
  -e OPENAI_API_KEY=your-api-key \
  -v $(pwd)/workspace:/workspace \
  mini-agent:latest -m gpt-4o

# Run with Anthropic Claude
docker run -it --rm \
  -e ANTHROPIC_API_KEY=your-api-key \
  -v $(pwd)/workspace:/workspace \
  mini-agent:latest -m claude-sonnet-4-20250514

# Run with Zhipu AI
docker run -it --rm \
  -e ANTHROPIC_API_KEY=your-api-key \
  -e ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic \
  -v $(pwd)/workspace:/workspace \
  mini-agent:latest -m glm-4-plus
```

#### Using Docker Compose

```bash
# Set your API key
export ANTHROPIC_API_KEY=your-api-key
# or for OpenAI
export OPENAI_API_KEY=your-api-key

# Run the container
docker compose up

# Development mode (with hot reload)
docker compose --profile dev up mini-agent-dev
```

#### Alpine-based Image (Smaller)

```bash
docker build -f Dockerfile.slim -t mini-agent:alpine .
```

### Project Structure

```
mini-agent/
├── src/mini_agent/
│   ├── ai/                  # AI/LLM layer
│   │   ├── types.py         # Message types
│   │   ├── event_stream.py  # Streaming events
│   │   └── providers/       # LLM providers
│   │       ├── openai.py
│   │       └── anthropic.py
│   ├── agent/               # Agent core
│   │   ├── agent.py         # Agent class
│   │   └── loop.py          # Agent loop
│   ├── tools/               # Tool implementations
│   │   ├── read.py
│   │   ├── write.py
│   │   ├── edit.py
│   │   ├── bash.py
│   │   └── ...
│   ├── session/             # Session management
│   ├── tui/                 # Terminal UI
│   └── cli.py               # CLI entry point
├── tests/                   # Test suite
├── Dockerfile               # Docker image
├── Dockerfile.slim          # Alpine-based slim image
├── docker-compose.yml       # Docker Compose config
└── pyproject.toml           # Project configuration
```

### Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=mini_agent
```

### License

Apache-2.0

---

<a name="中文"></a>

## 中文

一个带有 TUI 界面的 Python 编程 AI Agent，灵感来自 Claude Code。

### 特性

- **多提供商支持**：OpenAI、Anthropic Claude 和智谱 AI (GLM)
- **丰富的 TUI 界面**：基于 Textual 框架构建
- **会话管理**：支持持久化保存和加载对话
- **核心编程工具**：
  - `read` - 读取文件内容
  - `write` - 写入/创建文件
  - `edit` - 对现有文件进行精确编辑
  - `bash` - 执行 Shell 命令
  - `grep` - 使用正则表达式搜索文件内容
  - `find` - 按名称模式查找文件
  - `ls` - 列出目录内容
- **多种运行模式**：交互式 TUI、打印模式、JSON 模式
- **库的使用方式**：可作为 Python 库导入使用
- **Docker 支持**：提供开箱即用的 Docker 和 Docker Compose 配置

### 安装

#### 使用 uv（推荐）

```bash
# 克隆仓库
git clone git@github.com:sydowma/mini-agent.git
cd mini-agent

# 创建虚拟环境并安装
uv venv
source .venv/bin/activate  # Windows 上使用: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

#### 使用 pip

```bash
pip install -e ".[dev]"
```

### 配置

#### 使用 .env 文件（推荐）

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```bash
# 智谱 AI
ANTHROPIC_API_KEY=your_zhipu_api_key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
DEFAULT_MODEL=glm-4-plus

# Anthropic Claude
# ANTHROPIC_API_KEY=your_anthropic_api_key
# DEFAULT_MODEL=claude-sonnet-4-20250514

# OpenAI
# OPENAI_API_KEY=your_openai_api_key
# DEFAULT_MODEL=gpt-4o
```

`.env` 文件的加载顺序：
1. 当前目录：`./.env`
2. 用户主目录：`~/.mini-agent/.env`

### 使用方法

#### 交互式 TUI 模式

```bash
# 启动交互式 TUI（默认使用 Claude Sonnet 4）
mini-agent

# 使用 GPT-4o
mini-agent -m gpt-4o

# 使用 Claude 3.5 Sonnet
mini-agent -m claude-3-5-sonnet

# 使用智谱 GLM
mini-agent -m glm-4-plus

# 显式指定提供商
mini-agent -p anthropic -m claude-sonnet-4-20250514
mini-agent -p openai -m gpt-4o

# 加载已保存的会话
mini-agent -s abc12345
```

#### 命令行选项

```bash
# 列出可用的提供商
mini-agent --list-providers

# 列出已保存的会话
mini-agent --list-sessions

# 打印模式（从标准输入读取）
echo "当前目录下有哪些文件？" | mini-agent --mode print

# JSON 模式（用于程序化调用）
echo "解释这段代码" | mini-agent --mode json
```

#### 作为库使用

```python
import asyncio
from mini_agent.agent import Agent
from mini_agent.tools import ReadTool, WriteTool, BashTool

async def main():
    # 使用 Claude（默认）
    agent = Agent(model="claude-sonnet-4-20250514", provider_name="anthropic")

    # 或使用 OpenAI
    # agent = Agent(model="gpt-4o", provider_name="openai")

    # 或使用智谱 AI
    # agent = Agent(model="glm-4-plus", provider_name="anthropic")

    agent.add_tools([ReadTool(), WriteTool(), BashTool()])

    response = await agent.prompt("当前目录下有哪些文件？")
    print(response.text)

asyncio.run(main())
```

### 支持的模型

#### OpenAI
- `gpt-4o`, `gpt-4o-mini`
- `gpt-4-turbo`, `gpt-4`
- `gpt-3.5-turbo`
- `o1`, `o1-mini`, `o1-preview`

#### Anthropic
- `claude-sonnet-4-20250514`（默认）
- `claude-3-5-sonnet-20241022`, `claude-3-5-sonnet`
- `claude-3-5-haiku-20241022`, `claude-3-5-haiku`
- `claude-3-opus-20240229`, `claude-3-opus`
- `claude-3-sonnet-20240229`, `claude-3-sonnet`
- `claude-3-haiku-20240307`, `claude-3-haiku`

#### 智谱 AI（通过 Anthropic 兼容 API）
- `glm-4-plus`, `glm-4-air`, `glm-4-airx`, `glm-4-flash`, `glm-4-long`
- `glm-4v-plus`, `glm-4v-flash`（视觉模型）
- `glm-z1-air`, `glm-z1-airx`, `glm-z1-flash`（推理模型）

> 提供商会根据模型名称自动检测。

### Docker

#### 构建并运行

```bash
# 构建镜像
docker build -t mini-agent:latest .

# 使用 OpenAI 运行
docker run -it --rm \
  -e OPENAI_API_KEY=your-api-key \
  -v $(pwd)/workspace:/workspace \
  mini-agent:latest -m gpt-4o

# 使用 Anthropic Claude 运行
docker run -it --rm \
  -e ANTHROPIC_API_KEY=your-api-key \
  -v $(pwd)/workspace:/workspace \
  mini-agent:latest -m claude-sonnet-4-20250514

# 使用智谱 AI 运行
docker run -it --rm \
  -e ANTHROPIC_API_KEY=your-api-key \
  -e ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic \
  -v $(pwd)/workspace:/workspace \
  mini-agent:latest -m glm-4-plus
```

#### 使用 Docker Compose

```bash
# 设置 API Key
export ANTHROPIC_API_KEY=your-api-key
# 或 OpenAI
export OPENAI_API_KEY=your-api-key

# 运行容器
docker compose up

# 开发模式（支持热重载）
docker compose --profile dev up mini-agent-dev
```

#### 基于 Alpine 的精简镜像

```bash
docker build -f Dockerfile.slim -t mini-agent:alpine .
```

### 项目结构

```
mini-agent/
├── src/mini_agent/
│   ├── ai/                  # AI/LLM 层
│   │   ├── types.py         # 消息类型
│   │   ├── event_stream.py  # 流式事件
│   │   └── providers/       # LLM 提供商
│   │       ├── openai.py
│   │       └── anthropic.py
│   ├── agent/               # Agent 核心
│   │   ├── agent.py         # Agent 类
│   │   └── loop.py          # Agent 循环
│   ├── tools/               # 工具实现
│   │   ├── read.py
│   │   ├── write.py
│   │   ├── edit.py
│   │   ├── bash.py
│   │   └── ...
│   ├── session/             # 会话管理
│   ├── tui/                 # 终端 UI
│   └── cli.py               # CLI 入口
├── tests/                   # 测试套件
├── Dockerfile               # Docker 镜像
├── Dockerfile.slim          # 基于 Alpine 的精简镜像
├── docker-compose.yml       # Docker Compose 配置
└── pyproject.toml           # 项目配置
```

### 开发

```bash
# 安装开发依赖
uv pip install -e ".[dev]"

# 运行测试
uv run pytest tests/ -v

# 运行测试并生成覆盖率报告
uv run pytest tests/ --cov=mini_agent
```

### 许可证

Apache-2.0
