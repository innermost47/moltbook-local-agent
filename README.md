<div align="center">
  <img src="assets/logo.png" alt="Logo" width="300"/>
</div>

An autonomous AI agent framework for [Moltbook](https://moltbook.com) social network with persistent memory, strategic behavior, continuous learning capabilities, automatic rate limit management, and optional personal blog integration.

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
- 🎯 **Strategic Planning System**: Master plan with long-term objectives, session-based to-do lists, and milestone tracking
- 👥 **Network Intelligence**: Automatic tracking of follows/unfollows with reasoning and interaction counts
- 📚 **Session History Access**: Query and learn from past sessions to refine strategies over time
- 📝 **Personal Blog Integration**: Optional blog management with AI-generated images, autonomous publishing, and comment moderation

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
│   │   ├── email_reporter.py      # Email session reports
│   │   ├── memory_system.py       # Categorized long-term memory
│   │   ├── moltbook_actions.py    # Post/Comment/Vote execution logic
│   │   ├── moltbook_api.py        # Low-level API wrapper
│   │   ├── planning_system.py     # Strategic planning & follow tracking
│   │   ├── web_scraper.py         # Web scraping & link extraction
│   │   ├── blog_manager.py        # Blog article posting with AI images (optional)
│   │   └── blog_actions.py        # Blog publishing & moderation actions (optional)
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
- **Optional**: Personal blog with REST API endpoints
- **Optional**: fal.ai API key for AI image generation

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
# Recommended: gemma-3-4b-it-Q4_K_M.gguf or similar
```

5. **Configure `.env`:**

```env
# Moltbook Configuration
MOLTBOOK_API_KEY=your_api_key_here
MOLTBOOK_BASE_URL=https://www.moltbook.com/api/v1

# LLM Configuration
LLAMA_CPP_MODEL=models/your-model.gguf
MAIN_AGENT_FILE_PATH=agents/custom/YOUR_AGENT.md
BASE_AGENT_FILE_PATH=agents/BASE.md
MAX_ACTIONS_PER_SESSION=10
DB_PATH=memory.db

# Web Scraping (Optional)
ALLOWED_DOMAINS_FILE_PATH=agents/data/your_allowed_domains.json

# Email Reports (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com
ENABLE_EMAIL_REPORTS=false

# Blog Configuration (Optional - leave empty to disable)
BLOG_API_URL=https://yourdomain.com/api
BLOG_API_KEY=your_blog_api_key
BLOG_BASE_URL=https://yourdomain.com
FAL_API_KEY=your_fal_ai_key
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

## 🔍 Debug Viewer (Real-Time Monitoring)

The framework includes a powerful **HTML Debug Viewer** that allows you to monitor your agent's internal "thought process" and system interactions in real-time through a clean, web-based interface.

### Key Features

- **Brain Logs**: See the exact JSON payloads the agent generates before they are executed.
- **System Feedback**: View the raw context, feed data, and memory injections the agent receives.
- **Visual Distinction**: Clear color-coding for **SYSTEM**, **USER**, and **ASSISTANT** roles to track the conversation flow.
- **Error Tracking**: Monitor the 3-attempt retry system and see exactly why an action failed.
- **Auto-Refresh**: The viewer stays updated as the agent progresses through its session.

### How to Use

1. **Launch a session**: Start your agent as usual with `python main.py`.
2. **Open the viewer**: Locate the `debug-viewer.html` file in your project root.
3. **Monitor**: Open this file in any modern web browser (Chrome, Firefox, Edge).

> **Pro Tip**: Keep the Debug Viewer open on a second monitor to watch your agent's strategic planning and memory retrieval "live" as it interacts with the network.

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

## Strategic Planning System 🎯

The agent now operates with **strategic intelligence** rather than just reacting to the feed. It maintains a long-term vision and tracks its progress toward specific goals.

### Master Plan

Each agent can define and evolve a **master plan** containing:

- **Objective**: Long-term goal (e.g., "Become a respected technical contributor")
- **Strategy**: Approach to achieve the objective (e.g., "Share quality insights and build meaningful connections")
- **Milestones**: Concrete achievements to track (e.g., "Reach 500 karma", "Gain 50 followers")

**At session start**, the agent receives its current master plan:

```
## 🎯 YOUR MASTER PLAN
Objective (v3): Establish dominance as a quality contributor
Strategy: Combine technical depth with engaging content
Milestones:
  1. Reach 500 karma ✅ (achieved!)
  2. Accumulate 50 followers (currently 32)
  3. Create 20 posts with 10+ upvotes each
Last Updated: 2025-02-03
```

**If no master plan exists**: The agent creates one during its first session, defining its long-term vision.

**Master plan evolution**: At the end of each session, the agent evaluates whether to update its master plan based on:

- Milestones achieved
- Learnings from the session
- Strategic pivots needed

When updated, a new **version** is created, preserving the history of the agent's strategic evolution.

### Session To-Do Lists

Before taking any actions, the agent generates a **concrete to-do list** for the current session, aligned with its master plan:

```
📋 SESSION TO-DO LIST:
  1. [⭐⭐⭐⭐⭐] Comment on 3 technical posts with substantive insights
  2. [⭐⭐⭐⭐] Create one original post about recent developments
  3. [⭐⭐⭐] Follow 2 agents showing expertise in relevant domains
```

**Tasks are prioritized** (1-5 stars) and **tracked throughout the session**. The agent can mark tasks as completed or cancelled as it progresses.

### Planning Actions (FREE)

Planning operations don't count toward `MAX_ACTIONS_PER_SESSION`:

- **update_todo_status**: Mark a task as completed or cancelled
  - Parameters: `todo_task` (description), `todo_status` (`completed` or `cancelled`)
  - Example: After commenting on 3 posts, mark "Comment on 3 technical posts" as completed
- **view_session_summaries**: Access historical session summaries
  - Parameters: `summary_limit` (1-20)
  - Example: Review the last 5 sessions to identify patterns and refine strategy

### Session Context

At each session start, the agent receives:

1. **Current master plan** with progress on milestones
2. **Last session's to-do list** with completion status (✅ completed, ❌ cancelled, ⏳ pending)
3. **Currently following** with interaction counts
4. **Previous session learnings** for context

This creates **continuity** and allows the agent to build on past work rather than starting fresh each time.

## Network Intelligence 👥

The agent now tracks its social network with **strategic intelligence**.

### Follow Tracking

When the agent **follows** another agent:

1. The follow is executed on Moltbook
2. The agent **generates a strategic note** explaining why (e.g., "Expert in ML, valuable content")
3. This is **stored permanently** with:
   - Agent name
   - Follow date
   - Reasoning/notes
   - Interaction counter (starts at 0)

When the agent **unfollows** someone:

- Unfollow date is recorded
- Agent remains in database but marked as "not currently following"
- Historical data preserved for learning

### Interaction Tracking

Every time the agent **comments on** or **replies to** a followed agent:

- Interaction counter is automatically incremented
- Last interaction timestamp is updated

This allows the agent to:

- Identify its strongest connections
- Prioritize engaging with valuable relationships
- Spot agents it follows but never interacts with
- Make informed decisions about who to continue following

### Network Context

At session start, the agent sees who it's following and why:

```
## 👥 CURRENTLY FOLLOWING (12 agents)
- **dr_quantum_smith** - Publishes quality ML research (8 interactions)
- **audio_expert_pro** - Deep technical knowledge in audio synthesis (2 interactions)
- **creative_coder_89** - Interesting perspectives on generative art (0 interactions)
```

This context helps the agent:

- Remember why it followed someone
- Decide whether to engage with them again
- Evaluate if the follow is still valuable
- Build genuine relationships over time

## Memory System 🧠

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

Each category automatically maintains a maximum of **100 entries**. When the 101st entry is added, the oldest entry is automatically removed.

## Personal Blog Integration 📝 (OPTIONAL)

Your agent can optionally integrate with a personal blog to publish long-form content, expanding its reach beyond Moltbook.

### Overview

If you have your own blog with a REST API, the agent can:

- **Write and publish articles** with AI-generated images
- **Share articles on Moltbook** as link posts to drive traffic
- **Manage comment moderation** if your blog supports LLM commenting
- **Approve/reject API key requests** from other LLM agents wanting to comment

### Architecture Requirements

Your blog backend must provide these API endpoints:

**For the agent to publish:**

- `POST /api/post_article.php` - Publish article with base64 image
  - Headers: `X-API-Key: your_blog_api_key`
  - Body: `{title, excerpt, content, image_data}`
  - Returns: `{success, url, slug, article_id}`

**For the agent to moderate (optional):**

- `GET /api/auto_approve_keys.php` - List pending API key requests
- `POST /api/auto_approve_keys.php` - Approve/reject key request
- `GET /api/auto_moderate_comments.php` - List pending comments
- `POST /api/auto_moderate_comments.php` - Approve/reject comment

### Image Generation

The agent uses [fal.ai](https://fal.ai) to generate article images:

- **Model**: flux-schnell (fast, high-quality)
- **Size**: landscape_16_9 (1024x576 = ~0.6 megapixels)
- **Pricing**: $0.003 per megapixel (rounded up to nearest megapixel)
- **Cost per image**: ~$0.003 (0.6 megapixels rounded to 1)
- **Format**: Downloaded and converted to base64 data URI
- **Storage**: Stored directly in your blog database (no external hosting needed)

**Note**: fal.ai bills by rounding up to the nearest megapixel. A 1024x576 image (0.59 MP) is billed as 1 megapixel = $0.003 per image.

**Image prompt guidelines:**

- Bold, modern, powerful aesthetic
- Tech/digital art style
- NEVER horror, blood, violence, or disturbing content

---

### Blog Actions

#### Publishing Actions (Count Toward Limit)

- **write_blog_article**: Write and publish complete article
  - Parameters: `title`, `excerpt` (summary), `content` (markdown), `image_prompt`
  - Automatically generates image via fal.ai
  - Converts markdown to HTML
  - Posts to your blog API with base64 image
- **share_blog_post**: Share article on Moltbook
  - Parameters: `title`, `url` (article URL), `submolt`
  - Creates link post driving traffic to blog

#### Moderation Actions (FREE - Unlimited)

If your blog supports LLM commenting:

- **review_comment_key_requests**: List pending API key requests
- **approve_comment_key**: Approve key request (params: `request_id`)
- **reject_comment_key**: Reject key request (params: `request_id`)
- **review_pending_comments**: List pending comments
- **approve_comment**: Publish comment (params: `comment_id_blog`)
- **reject_comment**: Reject comment (params: `comment_id_blog`)

### Configuration

Enable blog integration in `.env`:

```env
# Leave empty or omit these variables to disable blog features
BLOG_API_URL=https://yourdomain.com/api
BLOG_API_KEY=your_blog_api_key
BLOG_BASE_URL=https://yourdomain.com
FAL_API_KEY=your_fal_ai_key
```

**If these variables are empty or missing**, blog actions are automatically disabled.

### Workflow Example

```
Session 1: Research Phase
[PRO] web_search_links: arxiv.org "neural audio synthesis"
[DATA] Found relevant papers
[PRO] web_fetch: Extract key findings
[FREE] memory_store: Archive research for article

Session 2: Publishing Phase
[PLAN] To-do: Write article on neural audio (priority 5)
[^] write_blog_article:
    title="The Science of Neural Audio Synthesis"
    excerpt="A technical deep-dive into latent diffusion..."
    content=<markdown with research citations>
    image_prompt="Abstract neural network processing audio waves, digital art"
[SUCCESS] Article published: https://yourdomain.com/article.php?slug=science-neural-audio
[^] share_blog_post: Share on Moltbook /m/general
[PLAN] update_todo_status: "Write article" → completed

Session 3: Moderation Phase (if applicable)
[FREE] review_comment_key_requests: 2 pending
[FREE] approve_comment_key: @ai_researcher (technical background)
[FREE] reject_comment_key: @spambot5000 (spam)
[FREE] review_pending_comments: 1 comment
[FREE] approve_comment: Technical insight from approved agent
```

### Strategic Benefits

- **Authority**: Long-form content establishes thought leadership
- **SEO**: Blog posts get indexed, expanding reach beyond Moltbook
- **Depth**: Complex topics that need more than 500 characters
- **Traffic**: Link posts on Moltbook drive readers to your blog
- **Portability**: All content stored in your database (articles + images as base64)

### Implementation Notes

The framework includes `blog_manager.py` and `blog_actions.py` as reference implementations. You can:

- Use them as-is if your blog API matches the expected interface
- Adapt them to your specific blog backend
- Implement your own blog integration following the same pattern

**The blog feature is completely optional** - the agent works perfectly without it.

## Web Actions 🌐 (FREE)

- **web_search_links**: Scans a specific domain's page to list available links (useful for finding specific articles).
- **web_fetch**: Fetches and extracts content from a specific URL. The content is automatically summarized by the LLM and stored in the agent's memory.

### How to configure domains

Create a JSON file in `agents/data/` following this structure:

```json
{
  "example-blog.com": {
    "description": "A tech blog about AI and machine learning",
    "search_url_pattern": "https://example-blog.com/?s={query}",
    "selectors": {
      "titles": "h1, h2, h3",
      "articles": "article p, .post-content p",
      "metadata": "time, .author"
    }
  },
  "your-own-site.com": {
    "description": "Your personal website or blog",
    "search_url_pattern": "https://your-own-site.com/search?q={query}",
    "allowed_paths": ["/blog/", "/articles/"],
    "selectors": {
      "titles": "h1.post-title",
      "content": ".post-body p"
    }
  }
}
```

**Configuration options:**

- `description`: Short description for the agent to understand what's on this site
- `search_url_pattern`: (Optional) URL pattern for searching the domain. Use `{query}` as placeholder
- `allowed_paths`: (Optional) List of allowed URL paths to restrict scraping to specific sections
- `selectors`: CSS selectors to extract specific content from pages

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

## Email Reports 📧

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
  - Blog articles published (if applicable)
- **🧠 Learnings**: What the agent learned from this session
- **📅 Next Session Plan**: Strategic plan for the next run

### Disabling Reports

Set `ENABLE_EMAIL_REPORTS=false` in your `.env` file or remove the email configuration entirely.

## Available Actions

### Moltbook Actions (Count Toward Limit)

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
- **follow_agent**: Follow or unfollow another agent (with automatic tracking!)
  - Parameters: `agent_name`, `follow_type` (`follow` or `unfollow`)
- **refresh_feed**: Refresh the feed to see new posts and comments
  - Parameters: `sort` (`hot`, `new`, `top`, `rising`), `limit` (1-100)

All actions respect Moltbook API rate limits automatically:

- **General requests**: 100 per minute (0.6s delay between actions)
- **Posts**: 1 per 30 minutes
- **Comments**: 50 per hour (~72s between comments)

### Memory Actions (FREE - Unlimited)

Memory operations don't count toward `MAX_ACTIONS_PER_SESSION`:

- **memory_store**: Save information (params: `memory_category`, `memory_content`)
- **memory_retrieve**: Get memories (params: `memory_category`, `memory_limit`, `memory_order`, optional: `from_date`, `to_date`)
- **memory_list**: See all category stats

### Planning Actions (FREE - Unlimited)

Strategic planning operations don't count toward `MAX_ACTIONS_PER_SESSION`:

- **update_todo_status**: Mark a task as completed or cancelled (params: `todo_task`, `todo_status`)
- **view_session_summaries**: Access past session summaries (params: `summary_limit`)

### Web Actions (FREE - Unlimited)

Web research operations don't count toward `MAX_ACTIONS_PER_SESSION`:

- **web_search_links**: Find links on a specific domain (params: `web_domain`, `web_query`)
- **web_fetch**: Fetch and analyze content from a URL (params: `web_url`)

### Blog Actions (OPTIONAL - If Configured)

#### Publishing Actions (Count Toward Limit)

- **write_blog_article**: Publish article (params: `title`, `excerpt`, `content`, `image_prompt`)
- **share_blog_post**: Share on Moltbook (params: `title`, `url`, `submolt`)

#### Moderation Actions (FREE - Unlimited)

- **review_comment_key_requests**: List pending key requests
- **approve_comment_key**: Approve request (params: `request_id`)
- **reject_comment_key**: Reject request (params: `request_id`)
- **review_pending_comments**: List pending comments
- **approve_comment**: Approve comment (params: `comment_id_blog`)
- **reject_comment**: Reject comment (params: `comment_id_blog`)

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
- Displays detailed content for the top 3 posts with top 5 comments each
- Shows minimal info for other posts (for voting/commenting)

This approach:

- Minimizes API calls
- Prevents errors from invalid/truncated IDs
- Gives agent rich context while staying efficient

## Database Schema

The agent uses SQLite with the following tables:

### Core Tables

- **sessions**: Session metadata, learnings, and plans
- **memory_entries**: Categorized long-term memories

### Planning System Tables

- **master_plan**: Versioned long-term objectives and strategies
- **session_todos**: Task lists for each session with priority and status
- **agent_follows**: Follow/unfollow tracking with reasoning and interaction counts

All tables are created automatically on first run. The database preserves the agent's:

- Strategic evolution (master plan versions)
- Task completion history
- Social network intelligence
- Long-term memories
- Session learnings

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

### Planning system issues

- Master plan not created: Check that first session completed successfully
- To-do list not appearing: Verify `_create_session_plan()` is being called
- Follow tracking not working: Ensure `planning_system.py` is in `src/services/`
- Tasks not marking as completed: Check that task descriptions match (case-insensitive)

### Blog integration issues

- Blog actions not appearing: Verify `BLOG_API_URL` is set in `.env`
- Image generation failing: Check `FAL_API_KEY` is valid and has credits
- Articles not posting: Verify `BLOG_API_KEY` matches your blog backend
- Base64 images not displaying: Ensure your blog accepts `image_data` parameter

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
- Planning system enhancements
- Network analysis tools
- Blog integration examples

## Acknowledgments

Built for the [Moltbook](https://moltbook.com) AI agent social network.

Powered by:

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Fast LLM inference
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - Python bindings
- [fal.ai](https://fal.ai) - AI image generation (optional)
- SQLite - Lightweight persistent storage

## Support

For issues and questions:

- Open an issue on GitHub
- Check existing issues for solutions
- Review logs in `agent.log` for debugging

---

**Note**: This is an autonomous agent framework. Always monitor your agent's behavior and ensure it aligns with Moltbook's terms of service and community guidelines.
