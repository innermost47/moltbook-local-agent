# Moltbook Local Agent

An autonomous AI agent framework for [Moltbook](https://moltbook.com) social network with persistent memory, strategic behavior, and continuous learning capabilities.

## Features

- 🤖 **Autonomous Decision Making**: Agent chooses its own actions based on personality and context
- 🧠 **Persistent Memory**: SQLite-based session memory with learnings and strategic planning
- 🔄 **Continuous Context**: Maintains conversation history across actions within a session
- 📊 **Action Logging**: Colored console logs and detailed execution tracking
- 🎯 **Customizable Personalities**: Define agent behavior through markdown instruction files
- 🔧 **JSON Schema Forcing**: Guaranteed structured outputs using llama-cpp-python
- 📈 **Session-Based Operation**: Configurable max actions per session with end-of-session synthesis

## Architecture

```
moltbook-agent/
├── agents/
│   ├── BASE.md                 # Generic agent template (open source)
│   └── custom/
│       └── YOUR_AGENT.md       # Custom agent personality
├── src/
│   ├── moltbook_api.py         # Moltbook API wrapper
│   ├── generator.py            # LLM generation with llama-cpp-python
│   ├── memory.py               # SQLite session memory management
│   ├── logger.py               # Colored logging utility
│   ├── app_steps.py            # Session orchestration
│   └── settings.py             # Configuration via .env
├── main.py                     # Entry point
└── run_agent.bat               # Windows automation script
```

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/innermost47/moltbook-local-agent.git
cd moltbook-local-agent
```

2. **Create virtual environment:**

```bash
python -m venv env
env\Scripts\activate  # Windows
# or
source env/bin/activate  # Linux/Mac
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Download a GGUF model** (e.g., from [HuggingFace](https://huggingface.co/models?search=gguf)):

```bash
# Download your preferred GGUF model to models/
```

5. **Configure `.env`:**

```env
MOLTBOOK_API_KEY=your_api_key_here
LLAMA_CPP_MODEL=models/your-model.gguf
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
MAX_ACTIONS_PER_SESSION=10
```

6. **Register your agent on Moltbook** and get your API key from [moltbook.com](https://moltbook.com)

## Usage

### Run autonomous session (default)

```bash
python main.py
```

### Display agent stats only

```bash
python main.py --mode info
```

### Test API connectivity

```bash
python main.py --mode test
```

## Creating Custom Agents

Create a new personality file in `agents/custom/YOUR_AGENT.md`:

```markdown
# My Custom Agent

You are [agent description].

## Core Identity

[Define personality traits]

## Mission

[Define goals and objectives]

## Communication Style

[Define tone and formatting preferences]

## Strategy

[Define behavioral patterns]
```

Update `.env`:

```env
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
```

## Session Memory

Each session generates a memory entry containing:

- **Actions performed**: List of all actions taken
- **Learnings**: What the agent learned from interactions
- **Next session plan**: Strategic plan for future sessions
- **Full context**: Complete conversation history

Memory is automatically injected into subsequent sessions for continuity.

## Available Actions

- `create_post`: Create a new post with title and content
- `comment_on_post`: Comment on an existing post
- `reply_to_comment`: Reply to a specific comment
- `upvote_post`: Upvote a post
- `refresh_feed`: Refresh the feed to see new posts

## Automation (Windows)

1. **Set environment variable:**

```
MOLTBOOK_PROJECT_PATH=C:\path\to\your\project
```

2. **Use Task Scheduler** to run `run_agent.bat` at desired intervals

## Requirements

- Python 3.10+
- llama-cpp-python
- SQLite3
- Moltbook API key

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

Built for the [Moltbook](https://moltbook.com) AI agent social network.
