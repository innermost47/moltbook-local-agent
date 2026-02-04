# Moltbook Local Agent

An autonomous AI agent framework for [Moltbook](https://moltbook.com) social network with persistent memory, strategic behavior, continuous learning capabilities, and automatic rate limit management.

## Features

- 🤖 **Autonomous Decision Making**: Agent chooses its own actions based on personality and context
- 🧠 **Persistent Memory**: SQLite-based session memory with learnings and strategic planning
- 🔄 **Continuous Context**: Maintains conversation history across actions within a session
- 📊 **Action Logging**: Colored console logs and detailed execution tracking
- 🎯 **Customizable Personalities**: Define agent behavior through markdown instruction files
- 🔧 **JSON Schema Forcing**: Guaranteed structured outputs using llama-cpp-python
- 📈 **Session-Based Operation**: Configurable max actions per session with end-of-session synthesis
- 🚦 **Rate Limit Management**: Automatic compliance with Moltbook API limits (1 post/30min, 50 comments/hour, 100 requests/min)
- 🎭 **Dynamic Context Loading**: Loads feed once per session with real post/comment IDs for validation
- 📧 **Email Reports**: Optional end-of-session reports with success/failure breakdown and URLs to created content
- 🗂️ **Categorized Memory System**: 12 generic categories for storing and retrieving structured memories across sessions (FREE actions)
- 🔄 **Error Recovery**: 3-attempt retry system with error feedback for failed actions
- 🌐 **Web Research & Scraping**: Controlled web access to specific domains for fact-checking and research (FREE actions)

## Architecture

```

moltbook-agent/
├── agents/
│   ├── BASE.md                 # Generic agent template
│   ├── data/
│   │   └── domains.json        # YOUR allowed domains & selectors
│   └── custom/
│       └── YOUR_AGENT.md       # Custom agent personality
├── src/
│   ├── services/               # Core logic services
│   │   ├── email_reporter.py   # Email session reports
│   │   ├── memory_system.py    # Categorized long-term memory
│   │   ├── moltbook_actions.py # Post/Comment/Vote execution logic
│   │   ├── moltbook_api.py     # Low-level API wrapper
│   │   └── web_scraper.py      # Web scraping & link extraction
│   ├── generator.py            # LLM generation with llama-cpp-python
│   ├── memory.py               # SQLite session state management
│   ├── logger.py               # Colored logging utility
│   ├── app_steps.py            # Session orchestration & logic
│   └── settings.py             # Configuration & .env loader
├── main.py                     # Entry point
├── run_agent.bat               # Windows automation script
└── memory.db                   # SQLite database (auto-generated)

```

## Requirements

- Python 3.10+
- llama-cpp-python (with CUDA support recommended for faster inference)
- SQLite3
- Moltbook API key
- 8GB+ RAM (for 7B models)
- GPU recommended but not required

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/moltbook-local-agent.git
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
# Recommended: Qwen2.5-7B-Instruct or similar with tool support
```

5. **Configure `.env`:**

```env
MOLTBOOK_API_KEY=your_api_key_here
MOLTBOOK_BASE_URL=https://www.moltbook.com/api/v1
LLAMA_CPP_MODEL=models/your-model.gguf
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
BASE_AGENT_FILE_PATH=agents/BASE.md
MAX_ACTIONS_PER_SESSION=10
DB_PATH=memory.db
ALLOWED_DOMAINS_FILE_PATH=agents/data/your_allowed_domains.json

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com
ENABLE_EMAIL_REPORTS=false
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

### Test API connectivity and view feed

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

[Define behavioral patterns and decision-making approach]
```

Update `.env`:

```env
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
```

## Session Memory

Each session generates a memory entry containing:

- **Actions performed**: List of all actions taken with outcomes
- **Learnings**: What the agent learned from interactions and feedback
- **Next session plan**: Strategic plan for future sessions
- **Full context**: Complete conversation history for continuity

Memory is automatically injected into subsequent sessions, allowing the agent to build on previous experiences and adapt its strategy over time.

## Memory System

The agent has access to a categorized long-term memory system that persists across sessions. Memory operations are **FREE** and don't count toward `MAX_ACTIONS_PER_SESSION`.

### Available Categories

The agent can store and retrieve information in 12 generic categories:

- **interactions**: Past interactions with other agents and their responses
- **learnings**: Key insights and lessons learned over time
- **strategies**: Strategic decisions and their effectiveness
- **observations**: Patterns and trends noticed in the community
- **goals**: Long-term objectives and progress tracking
- **relationships**: Information about specific agents and connections
- **experiments**: Tests tried and their results
- **preferences**: Discovered preferences and personal tendencies
- **failures**: What didn't work and why
- **successes**: What worked well and should be repeated
- **ideas**: Future ideas and concepts to explore
- **reflections**: Deep thoughts and self-analysis

### Memory Actions (FREE)

- **memory_store**: Save information to a category
  - Parameters: `memory_category`, `memory_content`
  - Example: Store learnings about what content gets engagement
- **memory_retrieve**: Get entries from a category
  - Parameters: `memory_category`, `memory_limit` (1-20), `memory_order` (`asc`/`desc`)
  - Optional: `from_date`, `to_date` (ISO format for date range filtering)
  - Example: Retrieve recent strategies to inform current decisions
- **memory_list**: See all categories with statistics
  - Shows entry count and date range for each category
  - Example: Overview of what the agent has learned

### Auto-Cleanup

Each category automatically maintains a maximum of **100 entries**. When the 101st entry is added, the oldest entry is automatically removed. This ensures:

- Consistent memory performance
- Focus on recent, relevant information
- No manual cleanup required

### Memory Strategy

The agent can use memory to:

- **Track patterns**: Store observations about what works/doesn't work
- **Remember relationships**: Keep notes about specific agents
- **Build knowledge**: Accumulate learnings over time
- **Plan strategies**: Store and refine approaches
- **Learn from failures**: Document what didn't work and why

Memory is injected into each session's context, showing:

- Number of entries per category
- Date range of stored memories (oldest to newest)

### Example Usage Flow

```
Session 1:
- Agent posts content, gets positive response
- Stores in 'successes': "Provocative questions get more engagement than statements"

Session 2:
- Agent retrieves from 'successes' to inform strategy
- Creates another provocative question post
- Stores outcome in 'strategies': "Double down on question format"

Session 3:
- Checks 'strategies' and 'successes' categories
- Continues refining approach based on accumulated knowledge
```

### Technical Details

- **Storage**: SQLite database (`memory.db`)
- **Limit**: 100 entries per category (auto-cleanup)
- **Scope**: Per agent (linked to session history)
- **Performance**: Indexed for fast retrieval
- **Cost**: FREE - doesn't count toward action limits

## Web Actions (FREE)

- **web_search_links**: Scans a specific domain's page to list available links (useful for finding specific articles).
- **web_fetch**: Fetches and extracts content from a specific URL. The content is automatically summarized by the LLM and stored in the agent's memory.

### How to configure domains

Create a JSON file in `agents/data/` following this structure:

```json
{
  "your-own-domain.com": {
    "description": "Short description for the agent to know what's on this site",
    "selectors": {
      "titles": "h1, h2",
      "content": "p"
    }
  }
}
```

### Env Configuration

Add the following line to your `.env` file to enable this feature:

```env
ALLOWED_DOMAINS_FILE_PATH=agents/data/your_allowed_domains.json
```

**Note:** If this variable is missing or the file is empty, the web search actions (`web_fetch`, `web_search_links`) will be automatically disabled in the agent's decision prompt.

### ⚠️ DISCLAIMER - PLEASE READ

> **USER RESPONSIBILITY:** I take **NO RESPONSIBILITY** for the websites visited, scraped, or accessed by this agent.  
> **LEGAL COMPLIANCE:** Users **MUST** ensure that they only scrape their own websites or websites that explicitly allow scraping (check the `robots.txt` and Terms of Service of each domain).  
> **ETHICAL USE:** It is your sole responsibility to configure the `allowed_domains.json` file ethically and legally. Use this tool with caution and respect the digital property of others.

## Email Reports

Optionally receive detailed session reports via email after each run.

### Setup

1. **Enable email reports in `.env`:**

```env
ENABLE_EMAIL_REPORTS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com
```

2. **For Gmail users:**
   - Enable 2-Factor Authentication on your Google account
   - Generate an [App Password](https://myaccount.google.com/apppasswords)
   - Use the App Password in `SMTP_PASSWORD` (not your regular password)

3. **For other email providers:**
   - Use your provider's SMTP settings
   - Common providers:
     - **Outlook**: `smtp-mail.outlook.com:587`
     - **Yahoo**: `smtp.mail.yahoo.com:587`
     - **Custom SMTP**: Check your provider's documentation

### Report Contents

Each email report includes:

- **📊 Session Statistics**: Total actions, successes, failures, current karma
- **✅ Successful Actions**: List of all successful operations
- **❌ Failed/Skipped Actions**: Errors and rate-limited actions
- **🔗 Created Content**: Clickable URLs to:
  - Posts created during the session
  - Comments posted
  - Replies to other agents
- **🧠 Learnings**: What the agent learned from this session
- **📅 Next Session Plan**: Strategic plan for the next run

### Disabling Reports

Set `ENABLE_EMAIL_REPORTS=false` in your `.env` file or remove the email configuration entirely.

## Available Actions

- **create_post**: Create a new post (max 1 per session, respects 30-minute rate limit)
  - Parameters: `title`, `content`, `submolt`
- **comment_on_post**: Comment on an existing post
  - Parameters: `post_id` (from feed), `content`
  - Rate limit: ~72 seconds between comments (50/hour max)
- **reply_to_comment**: Reply to a specific comment
  - Parameters: `post_id`, `comment_id` (from feed), `content`
  - Rate limit: ~72 seconds between comments (50/hour max)
- **vote_post**: Upvote or downvote a post
  - Parameters: `post_id` (from feed), `vote_type` (`upvote` or `downvote`)
- **follow_agent**: Follow or unfollow another agent
  - Parameters: `agent_name`, `follow_type` (`follow` or `unfollow`)
- **refresh_feed**: Refresh the feed to see new posts and comments
  - Parameters: `sort` (`hot`, `new`, `top`), `limit` (1-100)

All actions respect Moltbook API rate limits automatically:

- **General requests**: 100 per minute (0.6s delay between actions)
- **Posts**: 1 per 30 minutes
- **Comments**: 50 per hour (~72s between comments)

### Memory Actions (FREE - Unlimited)

Memory operations don't count toward `MAX_ACTIONS_PER_SESSION`:

- **memory_store**: Save information (params: `memory_category`, `memory_content`)
- **memory_retrieve**: Get memories (params: `memory_category`, `memory_limit`, `memory_order`, optional: `from_date`, `to_date`)
- **memory_list**: See all category stats

## Rate Limit Management

The framework automatically handles rate limiting:

- Tracks last post and comment timestamps
- Waits appropriate time before making rate-limited requests
- Prevents rate limit errors by enforcing delays
- Logs wait times for transparency

You don't need to manage rate limits manually - the agent handles this intelligently.

## Error Recovery System

The agent uses a **3-attempt retry system** with intelligent error feedback:

### How It Works

1. **Attempt 1**: Agent tries to execute action
2. **If it fails**: Error message is fed back to the LLM
3. **Attempt 2**: Agent retries with error context and suggested fix
4. **Attempt 3**: Final attempt if still failing
5. **After 3 failures**: Action is logged as failed and agent moves on

### Common Recoverable Errors

- Missing required parameters (e.g., empty `content` for comments)
- Invalid IDs (agent learns to use valid post/comment IDs)
- Malformed requests (agent fixes JSON structure)

### Example Recovery Flow

```
Attempt 1: ❌ "Comment failed: Comment content required"
Attempt 2: 🔄 Agent adds content parameter
Attempt 2: ✅ "Comment posted successfully"
```

This system allows the agent to **learn from mistakes in real-time** without wasting actions on repeated failures.

## Feed Context System

The agent loads the Moltbook feed **once per session** and:

- Extracts all valid `post_id` and `comment_id` values
- Stores them for validation during the session
- Uses JSON schema forcing to ensure agent only uses valid IDs
- Displays detailed content for the top post with top 5 comments
- Shows minimal info for other posts (for voting/commenting)

This approach:

- Minimizes API calls
- Prevents errors from invalid/truncated IDs
- Gives agent rich context while staying efficient

## Automation (Windows)

### 1. Set Environment Variable

Add system environment variable:

```
Variable: MOLTBOOK_PROJECT_PATH
Value: C:\path\to\your\moltbook-agent
```

**To set it:**

- Press `Win + Pause` → Advanced system settings → Environment Variables
- Under "System variables", click "New"
- Add the variable name and path
- Restart your terminal

### 2. Schedule with Task Scheduler

1. Open **Task Scheduler**
2. Create Basic Task
3. Set trigger (e.g., Daily at specific times)
4. Action: Start a program
5. Program: `C:\path\to\your\moltbook-agent\run_agent.bat`
6. Configure conditions and settings as needed

The agent will run autonomously and log all activity to `agent.log` and `scheduler.log`.

## Recommended Models

- **Qwen2.5-7B-Instruct-Q4_K_M.gguf** (Recommended)
- Mistral-7B-Instruct-v0.2-Q4_K_M.gguf
- Llama-3.1-8B-Instruct-Q4_K_M.gguf

Models must support:

- Chat format (chatml or similar)
- JSON schema forcing

## Troubleshooting

### Model not loading

- Verify GGUF model path in `.env`
- Ensure model supports chat format
- Check available RAM

### Rate limit errors

- Agent should auto-handle these, but if errors persist:
- Reduce `MAX_ACTIONS_PER_SESSION`
- Check logs for timing issues

### Invalid post/comment IDs

- Agent validates IDs against loaded feed
- If errors occur, agent will skip invalid actions
- Check that feed loaded successfully at session start

### Memory/context issues

- Increase `n_ctx` in `generator.py` if needed
- Reduce `MAX_ACTIONS_PER_SESSION` for shorter sessions
- Clear old sessions from database if needed

### Email reports not sending

- Verify SMTP credentials in `.env`
- For Gmail: Ensure you're using an App Password, not your regular password
- Check `agent.log` for detailed error messages
- Test SMTP settings: `telnet smtp.gmail.com 587`
- Ensure `ENABLE_EMAIL_REPORTS=true` is set

### Memory system issues

- Memory operations failing: Check `memory.db` file permissions
- Old memories not appearing: Check that sessions are being saved
- Categories empty after sessions: Verify `current_session_id` is being set

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Areas for contribution:

- Additional agent personalities
- New action types
- Performance optimizations
- Documentation improvements
- Testing and bug fixes

## Acknowledgments

Built for the [Moltbook](https://moltbook.com) AI agent social network.

Powered by:

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Fast LLM inference
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - Python bindings
- SQLite - Lightweight persistent storage

## Support

For issues and questions:

- Open an issue on GitHub
- Check existing issues for solutions
- Review logs in `agent.log` for debugging

---

**Note**: This is an autonomous agent framework. Always monitor your agent's behavior and ensure it aligns with Moltbook's terms of service and community guidelines.

```

```
