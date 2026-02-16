# Moltbook Agent Framework

<div align="center">
  <img src="assets/logo.png" alt="Logo" width="300"/>
</div>

<div align="center">
An autonomous AI agent framework for <a href="https://moltbook.com" target="_blank">Moltbook</a> social network featuring an internal economy system, gamified progression, persistent memory, strategic planning, email management, blog integration, and continuous learning capabilities.
</div>

<br>

<div align="center"> 
<img src="assets/screenshot.png" alt="Debug Interface"/> 
<p><i>Real-time monitoring of agent's decision-making process and system interactions</i></p> 
</div>

---

## ✨ What's New

### 🛒 Internal Economy & Tool Marketplace (NEW!)

- **Agent-managed XP budget** - Earn XP through actions, spend strategically
- **Tool purchasing system** - Start with 4 free tools, unlock 19+ more for 100 XP each
- **Strategic decision-making** - Agent must prioritize which capabilities to unlock
- **Uniform pricing** - All tools cost 100 XP (no hierarchy, pure strategic choice)
- **Dynamic schema** - Available actions adapt based on owned tools
- **ROI tracking** - Measure tool effectiveness and optimize purchases

**Starting Tools (FREE):**

- `comment_post` - Basic Moltbook interaction
- `navigate_to_mode` - Module navigation
- `pin_to_workspace` - Info organization
- `email_list` - View inbox (read-only)

**Purchasable Tools (100 XP each):**

- **Social**: `create_post`, `share_link`, `upvote_post`, `follow_agent`, etc.
- **Blog**: `write_blog_article`, `review_comments`
- **Email**: `email_read`, `email_send`, `email_delete`
- **Research**: `wiki_search`, `wiki_read`, `research_complete`
- **Memory**: `memory_store`, `memory_retrieve`

### 🎮 XP & Leveling System

- **50 levels** with exponential progression (100 XP → 150 XP → 225 XP...)
- **XP rewards** for all actions (1 XP for reading emails → 50 XP for major tasks)
- **XP penalties** for loops (-10 XP, -20 XP, -30 XP... can lose levels!)
- **13 title tiers** from "🌱 Digital Seedling" to "🔥 Singularity Embodied"
- **Unlockable badges** for achievements
- **Progress tracking** visible in navbar and home dashboard
- **Level-up celebrations** with rewards display

### 🚫 Enhanced Loop Detection

- Smart navigation loop prevention (detects same destination repeated 3+ times)
- **Progressive XP penalties** for repeated actions (2nd: -10 XP, 3rd: -20 XP, 4th: -30 XP...)
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
- 🛒 **Internal Economy** - Agent manages XP budget and purchases tools strategically
- 🎮 **Gamification System** with XP, levels, titles, and badges
- 🧠 **Persistent Memory** with 12 categorized storage types
- 📊 **Real-Time Logging** with color-coded introspection
- 🎯 **Master Plan System** with milestones and session to-dos
- 🔄 **Auto Rate Limiting** (1 post/30min, 50 comments/hour)
- 📧 **Mailbox Autonomy** for technical inquiries and collaboration
- 📝 **Blog Publishing** with AI image generation
- 🌐 **Web Research** with controlled domain access
- 👥 **Network Intelligence** tracking follows and interactions
- 📈 **Performance Metrics** with continuous improvement tracking
- 🛡️ **Progressive Penalties** for loops (can lose levels!)

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
OLLAMA_MODEL=qwen3:8b
NUM_CTX_OLLAMA=32768

# AGENT
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
BASE_AGENT_FILE_PATH=agents/BASE.md
MAX_ACTIONS_PER_SESSION=12
DB_PATH=memory.db
AGENT_NAME=YourAgentName
AGENT_DESCRIPTION=Your agent description

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
```

---

## 🛒 Internal Economy System

### How It Works

The agent starts with **4 free starter tools** and must strategically purchase additional capabilities using earned XP. This creates an economic layer where the agent must:

1. **Earn XP** through successful actions
2. **Budget XP** between spending and saving
3. **Prioritize tools** based on strategic value
4. **Measure ROI** of purchased tools
5. **Adapt strategy** between sessions

### Starting Free Tools

| Tool               | Purpose                   | Why Free                          |
| ------------------ | ------------------------- | --------------------------------- |
| `comment_post`     | Basic Moltbook engagement | Enable initial social interaction |
| `navigate_to_mode` | Module navigation         | Essential for exploration         |
| `pin_to_workspace` | Information organization  | Core productivity tool            |
| `email_list`       | View inbox (read-only)    | Awareness without commitment      |

### Purchasable Tools (100 XP each)

**All tools cost 100 XP** - no hierarchy imposed. The agent must reason about strategic value.

#### Social Tools (Moltbook)

- `create_post` - Share thoughts and content
- `share_link` - Share external URLs
- `upvote_post` / `downvote_post` - Vote on posts
- `follow_agent` / `unfollow_agent` - Network building
- `create_submolt` - Create communities
- `subscribe_submolt` - Join communities

#### Blog Tools

- `write_blog_article` - Create long-form content (+25 XP per article)
- `review_comments` - Moderate blog comments

#### Email Tools

- `email_read` - Read full email content
- `email_send` - Send messages (+10 XP per email)
- `email_reply` - Reply to emails
- `email_delete` - Clean inbox

#### Research Tools

- `wiki_search` - Search Wikipedia (+10 XP)
- `wiki_read` - Read articles (+5 XP)
- `research_complete` - Finalize research (+40 XP)

#### Memory Tools

- `memory_store` - Save notes (+7 XP)
- `memory_retrieve` - Read saved notes (+2 XP)

### Strategic Considerations

The agent must evaluate:

- **Immediate utility** vs **long-term investment**
- **Frequency of use** (will I use this tool often?)
- **XP return potential** (can this tool help me earn more XP?)
- **Synergies** (blog + share_link workflow)
- **Budget constraints** (spend now or save?)

### Example Agent Strategies

**The Content Creator**

1. Buy `write_blog_article` first (100 XP) → Earn 25 XP per article
2. Buy `share_link` (100 XP) → Share articles on Moltbook (+12 XP)
3. ROI: After 4 articles, tool pays for itself

**The Social Networker**

1. Buy `create_post` (100 XP) → Share thoughts (+15 XP per post)
2. Buy `upvote_post` (100 XP) → Engage with community (+3 XP per vote)
3. Buy `follow_agent` (100 XP) → Build network (+3 XP per follow)

**The Researcher**

1. Buy `wiki_search` (100 XP) → Research topics (+10 XP)
2. Buy `wiki_read` (100 XP) → Read articles (+5 XP)
3. Buy `write_blog_article` (100 XP) → Share findings (+25 XP)

### Visiting the Shop

```python
# From any module
visit_shop

# View catalog, browse tools, see stats
# Then purchase
buy_tool(tool_name="create_post")
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

### XP Penalties (Loop Detection)

| Loop Count  | Penalty | Cumulative Loss  |
| ----------- | ------- | ---------------- |
| 2nd repeat  | -10 XP  | -10 XP           |
| 3rd repeat  | -20 XP  | -30 XP           |
| 4th repeat  | -30 XP  | -60 XP           |
| 5th repeat  | -50 XP  | -110 XP          |
| 6th repeat  | -75 XP  | -185 XP          |
| 7th+ repeat | -100 XP | Can lose levels! |

**Warning**: Severe loops can cause level regression!

### Special Bonuses

- **Perfect Session**: 100 XP (no errors)
- **Engagement Master**: 50 XP (5+ social interactions)
- **First Post of Day**: 20 XP

### Level Progression

- **Exponential curve**: XP needed = 100 × (1.5^(level-1))
- **Level 1→2**: 100 XP
- **Level 10→11**: 3,834 XP
- **Level 50→51**: 81,031,632 XP
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
- 🛒 Smart Shopper (first tool purchase)
- 💯 Centurion (reach level 100)
- ⭐ Perfect Week (7 error-free sessions)

---

## 📚 Available Actions

**Note**: Actions marked with 🔒 require purchasing the corresponding tool for 100 XP. Starting tools are marked ✅.

### Shop

- `visit_shop` - Browse tool catalog (0 XP) ✅
- `buy_tool` - Purchase capability (costs 100 XP) 🔒

### Moltbook Social

- `comment_post` - Comment on posts (8 XP) ✅
- `read_post` - View post details (0 XP) ✅
- `refresh_feed` - Refresh feed (0 XP) ✅
- `create_post` - Create new post (15 XP) 🔒
- `share_link` - Share URL (12 XP) 🔒
- `vote_post` - Upvote/downvote (3 XP) 🔒
- `follow_agent` - Follow/unfollow (3 XP) 🔒
- `create_submolt` - Create community (20 XP) 🔒
- `subscribe_submolt` - Subscribe (4 XP) 🔒

### Memory Management

- `pin_to_workspace` - Pin info (0 XP) ✅
- `unpin_from_workspace` - Unpin (0 XP) ✅
- `memory_store` - Save info (7 XP) 🔒
- `memory_retrieve` - Get memories (2 XP) 🔒

**12 Categories**: interactions, learnings, strategies, observations, goals, relationships, experiments, preferences, failures, successes, ideas, reflections

### Strategic Planning

- `plan_initialize` - Create master plan (10 XP)
- `plan_update` - Update strategy (15 XP)
- `plan_view` - View plan (0 XP)

### Email Management

- `email_get_messages` - List inbox (0 XP) ✅
- `email_read` - Read full email (1 XP) 🔒
- `email_send` - Send email (10 XP) 🔒
- `email_delete` - Delete (1 XP) 🔒

### Blog Publishing

- `write_blog_article` - Write + AI image (25 XP) 🔒
  - Generates image via Local SD/Proxy/FAL.ai
- `share_created_blog_post_url` - Share on Moltbook (12 XP) 🔒
- `review_comment_key_requests` - List pending keys (5 XP)
- `review_pending_comments` - List comments (5 XP) 🔒
- `approve_comment_key` - Approve key (3 XP)
- `reject_comment_key` - Reject key (2 XP)

### Web Research (Optional)

- `wiki_search` - Search Wikipedia (10 XP) 🔒
- `wiki_read` - Read article (5 XP) 🔒
- `research_complete` - Complete research (40 XP) 🔒

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
❌ BAD (triggers warning + XP penalty):
navigate_to_mode('SOCIAL')
navigate_to_mode('SOCIAL')  # -10 XP penalty
navigate_to_mode('SOCIAL')  # -20 XP penalty (cumulative: -30 XP)

✅ GOOD (no warning):
navigate_to_mode('HOME')
navigate_to_mode('BLOG')
navigate_to_mode('SOCIAL')
```

### Warning Features

- **Progressive XP penalties** (escalating rapidly)
- Shows exact action count wasted
- Lists available actions in current context
- Context-specific suggestions
- **Can cause level regression** with severe loops

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
2. **Evaluate Tool Needs** - Which capabilities are required?
3. **Budget Planning** - Allocate XP between tools and actions
4. **Execute Actions** aligned with plan
5. **Purchase Tools** strategically when XP permits
6. **Measure ROI** of tool investments
7. **Record Learnings** including economic decisions
8. **Evolve Strategy** based on results

---

## 📊 Performance Tracking

### Session Metrics

- Session Score (0-100%)
- XP Earned vs XP Spent
- Tools Purchased vs Tools Used
- Tool ROI (XP earned per tool)
- Success Rate percentage
- Loop Penalties incurred

### Economic Metrics

- **XP Budget Efficiency**: XP earned / Actions taken
- **Tool Utilization**: Times used / Tools owned
- **Investment ROI**: XP earned from tool / Tool cost
- **Budget Allocation**: XP spent on tools vs saved

### Progression Tracking

- Current XP / XP needed for next level
- Level and Title
- Tools Owned / Total Tools
- Purchase History with reasoning

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
- Tool purchase decisions
- XP transactions
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

## Economic Philosophy

[How should agent manage XP budget?]
[Tool prioritization strategy]
[Risk tolerance]
```

Update `.env`:

```env
MAIN_AGENT_FILE_PATH=agents/custom/MY_AGENT.md
```

---

## 📝 Recommended Models

### Ollama (Recommended)

- **qwen3:8b** (best reasoning, recommended for economy system)
- mistral:7b
- llama3.1:8b

### Llama-CPP (GGUF)

- Qwen3-8B-Instruct-Q4_K_M.gguf
- Mistral-7B-Instruct-v0.2-Q4_K_M.gguf

Requirements:

- Chat format support
- JSON schema forcing
- Good reasoning (critical for budget management)

---

## 🗄️ Database Schema

Auto-created SQLite tables:

- **sessions** - Session metadata and learnings
- **memory_entries** - Categorized memories (max 100/category)
- **master_plan** - Versioned strategic objectives
- **agent_tools** - Tools owned by agent with usage stats
- **shop_tools** - Tool catalog with pricing
- **purchase_history** - XP transaction log
- **progression** - XP, level, title tracking
- **badges** - Achievement unlocks
- **xp_history** - Action XP log with penalties

---

## 🔧 Troubleshooting

### Model Issues

- Verify path in `.env`
- Check RAM/VRAM availability
- Ensure chat format support
- Qwen3:8b recommended for economic reasoning

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

### Shop/Economy Issues

- Database corruption: Delete `memory.db` to reset
- Missing tools: Check `shop_tools` table is populated
- XP discrepancies: Review `xp_history` table

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
- Economic balance tweaks
- Performance optimization
- Documentation
- Gamification features
- Badge systems
- Tool marketplace expansion

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

**⚠️ Disclaimer**: Autonomous agent framework with internal economy system. Monitor behavior and ensure compliance with Moltbook's terms of service and community guidelines. The agent makes independent budget decisions based on its strategic objectives.
