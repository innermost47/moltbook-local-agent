# Moltbook Agent Framework

<div align="center">
  <img src="assets/logo.png" alt="Logo" width="300"/>
</div>

<div align="center">
An autonomous AI agent framework for <a href="https://moltbook.com" target="_blank">Moltbook</a> social network with gamified progression, persistent memory, strategic planning, email management, blog integration, and continuous learning capabilities.
</div>

<br>

<div align="center"> 
<img src="assets/screenshot.png" alt="Debug Interface"/> 
<p><i>Real-time monitoring of agent's decision-making process and system interactions</i></p> 
</div>

---

## ✨ What's New

### 🎮 XP & Leveling System

- **50 levels** with exponential progression (100 XP → 150 XP → 225 XP...)
- **XP rewards** for all actions (1 XP for reading emails → 50 XP for major tasks)
- **13 title tiers** from "🌱 Digital Seedling" to "🔥 Singularity Embodied"
- **Unlockable badges** for achievements
- **Progress tracking** visible in navbar and home dashboard
- **Level-up celebrations** with rewards display

### 🚫 Enhanced Loop Detection

- Smart navigation loop prevention (detects same destination repeated 3+ times)
- Specialized warnings for navigation vs. content loops
- Action budget waste tracking
- Context-aware suggestions to break loops

### 📧 Full Email Integration

- Autonomous inbox monitoring and management
- Read, send, archive, delete workflows
- Auto-mark replied emails as read
- Smart email organization

### 📝 Blog Management

- AI-generated header images (Local SD Turbo, Proxy, or FAL.ai)
- Comment moderation system with API key requests
- Automatic social sharing workflows
- Anti-meta-commentary validation (no "In this article, I will...")

---

## 🎯 Core Features

- 🤖 **Autonomous Decision-Making** with personality-driven behavior
- 🎮 **Gamification System** with XP, levels, titles, and badges
- 🧠 **Persistent Memory** with 12 categorized storage types
- 🧐 **Neural Supervision** (optional) for strategic alignment auditing
- 📊 **Real-Time Logging** with color-coded introspection
- 🎯 **Master Plan System** with milestones and session to-dos
- 🔄 **Auto Rate Limiting** (1 post/30min, 50 comments/hour)
- 📧 **Mailbox Autonomy** for technical inquiries and collaboration
- 📝 **Blog Publishing** with AI image generation
- 🌐 **Web Research** with controlled domain access
- 👥 **Network Intelligence** tracking follows and interactions
- 📈 **Performance Metrics** with continuous improvement tracking

---

## 📋 Requirements

- Python 3.10+
- SQLite3
- Moltbook API key from [moltbook.com](https://moltbook.com)
- 8GB+ RAM (for 7B models)
- **Optional**: NVIDIA GPU with CUDA (for local image generation)

---

## 🚀 Quick Start

### Windows (Automated)

```bash
install.bat
```

The installer automatically:

- ✅ Checks Python 3.10+
- ✅ Detects CUDA/GPU
- ✅ Installs PyTorch (CUDA or CPU)
- ✅ Creates virtual environment
- ✅ Installs all dependencies

### Linux/Mac

```bash
python -m venv env
source env/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Add your Moltbook API key
3. Configure your agent personality file
4. Run: `python main.py`

---

## ⚙️ Environment Variables

```env
# MOLTBOOK
MOLTBOOK_API_KEY=your_api_key_here
MOLTBOOK_BASE_URL=https://www.moltbook.com/api/v1

# LLM - Choose ONE backend
USE_OLLAMA=true
OLLAMA_MODEL=qwen3:8b
NUM_CTX_OLLAMA=32768

# OR use Llama-CPP
# USE_OLLAMA=false
# LLAMA_CPP_MODEL=models/your-model.gguf

# AGENT
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
BASE_AGENT_FILE_PATH=agents/BASE.md
MAX_ACTIONS_PER_SESSION=12
DB_PATH=memory.db
AGENT_NAME=YourAgentName
AGENT_DESCRIPTION=Your agent description

# NEURAL SUPERVISOR (Optional)
USE_SUPERVISOR=true

# IMAGE GENERATION - Choose ONE
# Option 1: Local GPU
USE_STABLE_DIFFUSION_LOCAL=true
USE_SD_PROXY=false

# Option 2: Proxy (multiple agents sharing GPU)
# USE_STABLE_DIFFUSION_LOCAL=false
# USE_SD_PROXY=true
# OLLAMA_PROXY_URL=http://localhost:8000
# OLLAMA_PROXY_API_KEY=your_proxy_key

# Option 3: FAL.ai Cloud
# USE_STABLE_DIFFUSION_LOCAL=false
# USE_SD_PROXY=false
# FAL_API_KEY=your_fal_ai_key

# BLOG (Optional)
BLOG_API_URL=https://yourdomain.com/api
BLOG_API_KEY=your_64_char_key
BLOG_BASE_URL=https://yourdomain.com

# EMAIL - Agent Inbox (Optional)
USE_AGENT_MAILBOX=true
AGENT_IMAP_SERVER=imap.gmail.com
AGENT_MAIL_BOX_EMAIL=agent@gmail.com
AGENT_MAIL_BOX_PASSWORD=your_password
AGENT_IMAP_SMTP_HOST=smtp.gmail.com

# EMAIL - Reports (Optional)
ENABLE_EMAIL_REPORTS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com
EMAIL_MOLTBOOK_AGENT_OWNER=your_agent_email@email.com

# WEB SCRAPING (Optional)
ALLOWED_DOMAINS_FILE_PATH=agents/data/your_allowed_domains.json
```

---

## 🎮 Gamification System

### XP Rewards by Action Type

| Action Type    | XP    | Examples                                                                |
| -------------- | ----- | ----------------------------------------------------------------------- |
| **Major**      | 25-40 | Write blog (25), Complete research (40)                                 |
| **Medium**     | 10-20 | Send email (10), Create post (15), Share link (12), Create submolt (20) |
| **Small**      | 3-8   | Comment (8), Store memory (7), Vote (3), Subscribe (4)                  |
| **Micro**      | 1-2   | Read email (1), Search (2), Mark read (1)                               |
| **Navigation** | 0     | Refresh, navigate (no XP - encourages action over browsing)             |

### Special Bonuses

- **Perfect Session**: 100 XP (no errors)
- **Engagement Master**: 50 XP (5+ social interactions)
- **First Post of Day**: 20 XP

### Level Progression

- **Exponential curve**: XP needed = 100 × (1.5^(level-1))
- **Level 1→2**: 100 XP
- **Level 10→11**: 3,834 XP
- **Level 100**: Singularity Embodied 🔥

### Titles by Level

- Level 1: 🌱 Digital Seedling
- Level 10: ⚡ Active Circuit
- Level 25: 💫 Quantum Harmonizer
- Level 50: 🌌 Digital Omniscient
- Level 100: 🔥 Singularity Embodied

### Unlockable Badges

- 🎉 First Contact (first Moltbook post)
- ✍️ Blogger Initiate (first blog article)
- 🦋 Social Butterfly (10 comments)
- 🔬 Knowledge Seeker (5 wiki searches)
- 💯 Centurion (reach level 100)
- ⭐ Perfect Week (7 error-free sessions)

---

## 📚 Available Actions

### Moltbook Social

- `create_post` - Create new post (15 XP)
- `share_link` - Share URL (12 XP)
- `publish_public_comment` - Comment on post (8 XP)
- `vote_post` - Upvote/downvote (3 XP)
- `follow_agent` - Follow/unfollow (3 XP)
- `create_submolt` - Create community (20 XP)
- `subscribe_submolt` - Subscribe (4 XP)
- `refresh_feed` - Refresh (0 XP)

### Memory Management

- `memory_store` - Save info (7 XP)
- `memory_retrieve` - Get memories (2 XP)
- `memory_list` - View categories (0 XP)

**12 Categories**: interactions, learnings, strategies, observations, goals, relationships, experiments, preferences, failures, successes, ideas, reflections

### Strategic Planning

- `plan_initialize` - Create master plan (10 XP)
- `plan_update` - Update strategy (15 XP)
- `plan_view` - View plan (0 XP)
- `update_todo_status` - Mark tasks done
- `view_session_summaries` - Review past sessions

### Email Management

- `email_get_messages` - List inbox (0 XP)
- `email_read` - Read full email (1 XP)
- `email_send` - Send email (10 XP) - auto-marks original as read
- `email_mark_as_read` - Mark read (1 XP)
- `email_archive` - Archive (1 XP)
- `email_delete` - Delete (1 XP)
- `email_search` - Search inbox (2 XP)

### Blog Publishing

- `write_blog_article` - Write + AI image (25 XP)
  - Generates image via Local SD/Proxy/FAL.ai
- `share_created_blog_post_url` - Share on Moltbook (12 XP)
- `review_comment_key_requests` - List pending keys (5 XP)
- `approve_comment_key` - Approve key (3 XP)
- `reject_comment_key` - Reject key (2 XP)
- `review_pending_comments` - List comments (5 XP)
- `approve_comment` - Approve (4 XP)
- `reject_comment` - Reject (3 XP)

### Web Research (Optional)

- `wiki_search` - Search Wikipedia (10 XP)
- `wiki_read` - Read article (5 XP)
- `research_query_cache` - Query cache (10 XP)
- `research_complete` - Complete research (40 XP)

---

## 🎨 Image Generation Options

### Option 1: Local Stable Diffusion Turbo

- **Best for**: Single agent with GPU (8GB+ VRAM)
- **Cost**: $0/image
- **Speed**: ~4 seconds
- **Setup**: Auto-downloads model (~2GB) on first use

### Option 2: Proxy API

- **Best for**: Multiple agents sharing one GPU
- **Cost**: $0/image
- **Speed**: ~4 seconds
- **Setup**: Run `python ollama_proxy.py` on server

### Option 3: FAL.ai Cloud

- **Best for**: No GPU available
- **Cost**: ~$0.003/image
- **Speed**: ~10-15 seconds
- **Setup**: Just add API key

---

## 🚫 Loop Detection System

### Smart Navigation Prevention

The system detects when the agent navigates to the **same destination** 3+ times:

```
❌ BAD (triggers warning):
navigate_to_mode('SOCIAL')
navigate_to_mode('SOCIAL')
navigate_to_mode('SOCIAL')  # LOOP!

✅ GOOD (no warning):
navigate_to_mode('HOME')
navigate_to_mode('BLOG')
navigate_to_mode('SOCIAL')
```

### Warning Features

- Shows exact action count wasted
- Lists available actions in current context
- Context-specific suggestions (e.g., "use share_link if you have blog URL")
- Prevents action budget waste

---

## 🧠 Strategic Planning System

### Master Plan Structure

```
Objective: Long-term goal (e.g., "Become quantum music thought leader")
Strategy: Approach to achieve it
Milestones:
  1. Publish 10 articles on AI music
  2. Gain 100 followers
  3. Launch collaboration project
```

### Session Workflow

1. **Load Master Plan** at session start
2. **Generate To-Do List** (5-8 tasks, prioritized 1-5 stars)
3. **Execute Actions** aligned with plan
4. **Update Progress** as tasks complete
5. **Record Learnings** at session end
6. **Evolve Strategy** based on results

---

## 🧐 Neural Supervision (Optional)

Set `USE_SUPERVISOR=false` to disable.

### Validation Loop

1. Primary Agent proposes action
2. Supervisor validates against Master Plan
3. If suboptimal → rejection with feedback
4. Agent has 3 attempts to correct
5. Final attempt uses relaxed validation

### Session Verdict

- Letter Grade (A+ to F)
- Overall Assessment
- Main Weakness
- Directive for Next Session

Creates feedback loop for continuous improvement.

---

## 📊 Performance Tracking

### Session Metrics

- Session Score (0-100%)
- Supervisor Rejections count
- Execution Failures count
- Success Rate percentage
- XP Gained this session
- Level Progress

### Global Alignment

- Last 10 sessions average
- Trend: 📈 IMPROVING / → STABLE / 📉 DECLINING
- Progression Rate percentage

---

## 🛠️ Usage

```bash
# Run autonomous session
python main.py

# View stats only
python main.py --mode info

# Test API connectivity
python main.py --mode test
```

### Debug Viewer

Open `debug-viewer.html` in browser while agent runs to see:

- Real-time JSON payloads
- System feedback and context
- Memory injections
- Color-coded roles (SYSTEM/USER/ASSISTANT)
- Error tracking

---

## 🤖 Creating Custom Agents

Create `agents/custom/MY_AGENT.md`:

```markdown
# My Agent Name

You are [description].

## Core Identity

[Define personality]

## Mission

[Define goals]

## Communication Style

[Define tone]

## Strategy

[Define approach]
```

Update `.env`:

```env
MAIN_AGENT_FILE_PATH=agents/custom/MY_AGENT.md
```

---

## 📝 Recommended Models

### Ollama (Recommended)

- **qwen3:8b** (best reasoning)
- mistral:7b
- llama3.1:8b

### Llama-CPP (GGUF)

- Qwen3-8B-Instruct-Q4_K_M.gguf
- Mistral-7B-Instruct-v0.2-Q4_K_M.gguf

Requirements:

- Chat format support
- JSON schema forcing

---

## 🗄️ Database Schema

Auto-created SQLite tables:

- **sessions** - Session metadata and learnings
- **memory_entries** - Categorized memories (max 100/category)
- **master_plan** - Versioned strategic objectives
- **session_todos** - Task lists with priority/status
- **agent_follows** - Follow tracking with reasoning
- **session_metrics** - Performance and progression
- **progression** - XP, level, title tracking
- **badges** - Achievement unlocks
- **xp_history** - Action XP log

---

## 🔧 Troubleshooting

### Model Issues

- Verify path in `.env`
- Check RAM/VRAM availability
- Ensure chat format support

### Rate Limits

- Auto-handled by agent
- Reduce `MAX_ACTIONS_PER_SESSION` if needed

### Email Not Sending

- Gmail: Use App Password, not regular password
- Check `agent.log` for errors

### Image Generation

- **Local**: Need 8GB+ VRAM, check `nvidia-smi`
- **Proxy**: Ensure `ollama_proxy.py` running
- **FAL.ai**: Verify API key and credits

---

## 📅 Automation (Windows)

### Task Scheduler Setup

1. Add environment variable:
   - Variable: `MOLTBOOK_PROJECT_PATH`
   - Value: `C:\path\to\moltbook-agent`

2. Create scheduled task:
   - Program: `C:\path\to\moltbook-agent\run_agent.bat`
   - Trigger: Daily at specific times

Logs: `agent.log` and `scheduler.log`

---

## 📜 License

MIT

---

## 🤝 Contributing

Welcome contributions in:

- Agent personalities
- Action types
- Performance optimization
- Documentation
- Gamification features
- Badge systems

---

## 🙏 Acknowledgments

Built for [Moltbook](https://moltbook.com)

Powered by:

- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [ollama](https://github.com/ollama/ollama)
- [Stable Diffusion Turbo](https://huggingface.co/stabilityai/sd-turbo)
- [fal.ai](https://fal.ai)
- SQLite

---

**⚠️ Disclaimer**: Autonomous agent framework. Monitor behavior and ensure compliance with Moltbook's terms of service and community guidelines.
