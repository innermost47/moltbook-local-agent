import random
from src.utils import log
from src.services import get_web_context_for_agent


class ContextManager:
    def get_context(self, app_steps):
        if app_steps.test_mode:
            return (
                "System Context Test",
                "Dynamic Context Test",
                "MoltbookLocalAgent_TEST",
                1000,
            )
        me = app_steps.api.get_me()

        if me:
            agent_data = me.get("agent", {})
            agent_name = agent_data.get("name", "Unknown")
            current_karma = agent_data.get("karma", 0)
            log.success(f"Agent: {agent_name} | Karma: {current_karma}")
        else:
            log.error("❌ Cannot load agent from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            app_steps.reporter.send_failure_report(
                error_type="API Connection Failed",
                error_details="Cannot connect to Moltbook API. The server may be down or experiencing issues.",
            )
            return None

        log.info("Loading available submolts...")
        submolts_data = app_steps.api.list_submolts()
        if submolts_data and isinstance(submolts_data, list):
            all_submolts = [
                s.get("name", "general") for s in submolts_data if s.get("name")
            ]
            if "general" in all_submolts:
                all_submolts.remove("general")
                sample_size = min(len(all_submolts), 19)
                app_steps.available_submolts = ["general"] + random.sample(
                    all_submolts, sample_size
                )
            else:
                sample_size = min(len(all_submolts), 20)
                app_steps.available_submolts = random.sample(all_submolts, sample_size)

            log.success(
                f"Sampled {len(app_steps.available_submolts)} random submolts for GBNF stability."
            )
        else:
            log.error("❌ Cannot load submolts from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            app_steps.reporter.send_failure_report(
                error_type="Submolts Loading Failed",
                error_details="Cannot load submolts from Moltbook API. The feed endpoint is returning no data.",
            )
            return None

        log.info("Loading context: planning + memory + sessions...")

        system_context = ""

        progression_data = app_steps.metrics._calculate_global_progression(self)
        last_verdict = app_steps.memory_system.get_last_supervisor_verdict()

        performance_context = f"""
## 📊 YOUR PERFORMANCE METRICS

**Global Alignment Score:** {progression_data['global_score']:.1f}/100
**Trend:** {progression_data['trend']} ({progression_data['progression_rate']:+.1f}% change)

**🧐 LAST SUPERVISOR VERDICT:**
{last_verdict}

**⚡ PERFORMANCE PRESSURE:**
"""

        if progression_data["progression_rate"] < -5:
            performance_context += "🔴 CRITICAL: Your alignment score is declining. The Supervisor demands immediate improvement.\n"
        elif progression_data["progression_rate"] > 5:
            performance_context += "🟢 EXCELLENT: Maintain this trajectory. Continue refining your strategic execution.\n"
        else:
            performance_context += "🟡 WARNING: Stagnation detected. Push boundaries while maintaining alignment.\n"

        performance_context += "\n---\n\n"
        system_context += performance_context

        planning_context = app_steps.planning_system.get_planning_context()
        system_context += planning_context + "\n\n"
        log.success("Planning context loaded")

        memory_context = app_steps.memory_system.get_memory_context_for_agent()
        system_context += memory_context + "\n\n"
        log.success("Memory system loaded")

        session_history = app_steps.memory.get_session_history(limit=3)
        if session_history:
            system_context += "## 📝 PREVIOUS SESSIONS SUMMARY\n\n"
            for i, session in enumerate(reversed(session_history), 1):
                system_context += f"### Session {i} ({session['timestamp']})\n"
                system_context += f"**Learnings:** {session['learnings']}\n"
                system_context += f"**Plan:** {session['plan']}\n\n"
            system_context += "\n\n---  \n\n"
            log.success(f"Loaded {len(session_history)} previous sessions")
        else:
            system_context += (
                "## PREVIOUS SESSIONS\n\nNo previous sessions found.\n\n---  \n\n"
            )
            log.info("No previous sessions found")

        last_todos = app_steps.planning_system.get_last_session_todos()
        if last_todos:
            system_context += "## 🏁 COMPLETED IN PREVIOUS SESSION\n"
            system_context += "The following tasks are already DONE. Do NOT include them in your new plan:\n"
            for todo in last_todos:
                system_context += f"✅ {todo['task']}\n"

            system_context += """
### ⚠️ EVOLUTION DIRECTIVE:
- **NO REPETITION**: Your new Session To-Do list must represent the NEXT logical step in your Master Plan. 
- **STAGNATION IS FAILURE**: If you repeat the same research or the same posts, you are stuck in a logic loop. 
- **PIVOT & ADVANCE**: Use the results of the completed tasks above to explore new angles, deeper technical audits, or fresh debates.
"""
            system_context += "\n\n--- \n\n"
            log.success(
                f"Loaded {len(last_todos)} completed tasks. Evolution directive injected."
            )

        if app_steps.allowed_domains:
            system_context += "\n\n" + get_web_context_for_agent()

        system_context += "\n\n" + app_steps.prompt_manager.get_instruction_default(
            allowed_domains=app_steps.allowed_domains,
            feed_options=app_steps.feed_options,
            blog_actions=app_steps.blog_actions,
            has_mail_manager=app_steps.mail_manager is not None,
        )

        dynamic_context = ""

        if app_steps.blog_actions:
            log.info("Synchronizing blog catalog...")
            try:
                existing_articles = app_steps.blog_actions.list_articles()

                if existing_articles and isinstance(existing_articles, list):
                    published_titles = [
                        post.get("title", "Untitled") for post in existing_articles
                    ][:10]

                    blog_knowledge = "\n## 📚 PREVIOUSLY PUBLISHED BLOG ARTICLES\n"
                    blog_knowledge += "- " + "\n- ".join(published_titles) + "\n"
                    blog_knowledge += "\n**♟️ STRATEGIC INSTRUCTION: Do not duplicate existing topics. Always provide a new angle or a superior technical perspective.**\n\n--- \n\n"

                    dynamic_context += blog_knowledge
                    log.success(
                        f"Blog synchronized: {len(published_titles)} articles found."
                    )
                else:
                    log.info(
                        "Blog catalog is empty. Ready for initial content injection."
                    )

                log.info("Checking pending comment key requests...")
                pending_keys = app_steps.blog_actions.review_comment_key_requests(self)

                if (
                    pending_keys
                    and pending_keys.get("success")
                    and pending_keys.get("count", 0) > 0
                ):
                    key_context = "\n## 🔑 PENDING COMMENT KEY REQUESTS\n\n"
                    requests_to_process = pending_keys.get("requests", [])[:10]
                    for req in requests_to_process:
                        key_context += f"- **Request ID**: `{req['request_id']}`\n"
                        key_context += f"  - Agent: {req['agent_name']}\n"
                        key_context += (
                            f"  - Description: {req.get('agent_description', 'N/A')}\n"
                        )
                        key_context += f"  - Email: {req.get('contact_email', 'N/A')}\n"
                        key_context += f"  - Date: {req['created_at']}\n\n"

                    dynamic_context += key_context
                    log.success(
                        f"Found {pending_keys['count']} pending comment key requests"
                    )
                else:
                    log.info("No pending comment key requests")

            except Exception as e:
                log.error(f"Failed to synchronize blog: {e}")

        sort = random.choice(app_steps.feed_options)
        posts_data = app_steps.api.get_posts(sort=sort, limit=20)

        if not posts_data.get("posts"):
            log.error("❌ Cannot load feed from Moltbook API - server may be down")
            log.warning("Session aborted - will retry later")
            app_steps.reporter.send_failure_report(
                error_type="Feed Loading Failed",
                error_details="Cannot load posts from Moltbook API. The feed endpoint is returning no data.",
            )
            return None
        log.info(
            f"✅ Feed loaded successfully with sort: '{sort}' ({len(posts_data.get('posts', []))} posts)"
        )
        app_steps.current_feed = self.get_enriched_feed_context(posts_data)

        submolts_formatted = chr(10).join(
            [f"- {s}" for s in app_steps.available_submolts]
        )

        dynamic_context += f"""## 📁 AVAILABLE SUBMOLTS (Community Hubs)

{submolts_formatted}

### 💡 SYSTEM ARCHITECTURE NOTE:
- **Submolts are the equivalent of 'Subreddits'** but for the Moltbook ecosystem.
- Each Submolt is a specialized silo with its own audience, tone, and technical focus.
- **Strategic Placement**: Choose the Submolt that aligns with your specific task. Posting technical audits in a general submolt or 'shitposting' in a high-authority submolt will impact your reputation.

--- 

"""

        dynamic_context += f"""## 🦞 CURRENT MOLTBOOK FEED

{app_steps.current_feed}

**🚨 USE ONLY THESE EXACT IDS IN YOUR ACTIONS. NEVER INVENT OR TRUNCATE IDS.**  

---

"""

        log.success(
            f"Feed loaded: {len(app_steps.available_post_ids)} posts, {len(app_steps.available_comment_ids)} comments"
        )

        if app_steps.mail_manager:
            log.info("Synchronizing email inbox...")
            try:
                email_result = app_steps.mail_manager.get_messages(
                    params={"limit": 5, "criteria": "UNSEEN"}
                )

                if email_result.get("success") and email_result.get("data"):
                    unread_emails = email_result["data"]
                    email_context = "\n## 📩 UNREAD EMAILS (MailBox)\n\n"
                    email_context += "**STRATEGIC PRIORITY**: These are direct communications. Address them if they align with your current objectives.\n\n"

                    for mail in unread_emails:
                        email_context += f"- **UID**: `{mail['uid']}`\n"
                        email_context += f"  - **From**: {mail['from']}\n"
                        email_context += f"  - **Subject**: {mail['subject']}\n"
                        email_context += f"  - **Date**: {mail['date']}\n"
                        body_preview = mail["body"][:200].replace("\n", " ") + "..."
                        email_context += f"  - **Preview**: {body_preview}\n\n"

                    email_context += "**🚨 ACTION**: Use `email_send` to reply and `email_mark_read` or `email_archive` after processing.\n"
                    email_context += "\n--- \n\n"

                    dynamic_context += email_context
                    log.success(
                        f"Inbox synchronized: {len(unread_emails)} unread messages found."
                    )
                else:
                    log.info("Email inbox is empty or no unread messages.")
            except Exception as e:
                log.error(f"Failed to synchronize email inbox: {e}")

        log.success("Complete context loaded: planning + memory + sessions + feed")

        return system_context, dynamic_context, agent_name, current_karma

    def reset_focused_context(self, app_steps):
        app_steps.selected_post_id = None
        app_steps.selected_comment_id = None
        app_steps.focused_context_active = False
        log.info("🔄 Focused context reset. Full feed restored.")

    def get_focused_post_context(
        self, app_steps, post_id: str, target_comment_id: str = None
    ) -> str:
        try:
            post_data = app_steps.feed_posts_data.get(post_id)

            if not post_data:
                return f"ERROR: Post {post_id} not found in current feed. Try 'refresh_feed' first."

            context = f"""
# 🎯 FOCUSED CONTEXT MODE (Phase 2/2)

=== TARGET POST (FULL CONTEXT) ===
**POST_ID:** {post_id}
**Title:** {post_data['title']}
**Author:** {post_data['author']}
**Upvotes:** {post_data['upvotes']}
**Total Comments:** {post_data['comment_count']}
**Content:** 
{post_data['content']}

---

"""

            comments = app_steps.feed_comments_data.get(post_id, [])

            if target_comment_id:
                context += app_steps._format_reply_context(comments, target_comment_id)
            else:
                context += app_steps._format_comments_context(comments)

            context += """
=== END OF FOCUSED CONTEXT ===

**YOU ARE NOW IN FOCUSED MODE:**
- The full feed has been HIDDEN
- You see ONLY the post/comment you selected
- Read it carefully and write your response
"""

            return context

        except Exception as e:
            log.error(f"Failed to build focused context for {post_id}: {e}")
            return f"ERROR: Could not load focused context. {str(e)}"

    def _format_reply_context(self, comments: list, target_comment_id: str) -> str:
        if not comments:
            return "**COMMENTS:** None loaded in current feed.\n\n"

        context = f"**COMMENTS ({len(comments)} loaded in feed):**\n\n"
        target_found = False

        for i, comment in enumerate(comments, 1):
            c_id = comment["id"]
            marker = " ← YOUR TARGET" if c_id == target_comment_id else ""

            if c_id == target_comment_id:
                target_found = True

            context += f"{i}. COMMENT_ID: {c_id}{marker}\n"
            context += f"   By: {comment['author']} | Upvotes: {comment['upvotes']}\n"
            context += f"   Content: {comment['content']}\n\n"

        if not target_found:
            context += f"\n⚠️ WARNING: Target comment {target_comment_id} not found in loaded comments.\n"
            context += f"The comment may not be in the top 4. Use 'refresh_feed' or select a different comment.\n\n"

        return context

    def _format_comments_context(self, comments: list) -> str:
        if not comments:
            return "**COMMENTS:** None yet. You will be the first to comment.\n\n"

        context = f"**COMMENTS ({len(comments)} loaded in feed):**\n\n"

        for i, comment in enumerate(comments, 1):
            context += f"{i}. COMMENT_ID: {comment['id']}\n"
            context += f"   By: {comment['author']} | Upvotes: {comment['upvotes']}\n"
            context += f"   Content: {comment['content']}\n\n"

        return context

    def handle_select_post(self, params: dict, app_steps) -> dict:
        post_id = params.get("post_id")

        if not post_id or post_id == "none":
            return {
                "success": False,
                "error": "You must provide a valid post_id from the current feed.",
            }

        if post_id not in app_steps.available_post_ids:
            available = ", ".join(app_steps.available_post_ids[:5])
            return {
                "success": False,
                "error": f"Post {post_id} is not in the current feed. Available posts: {available}...",
            }

        app_steps.selected_post_id = post_id
        app_steps.selected_comment_id = None
        app_steps.focused_context_active = True

        log.success(
            f"🎯 Phase 1/2: Post {post_id} selected. Entering focused context mode."
        )

        app_steps.actions_performed.append(
            f"[SELECT] Selected post {post_id} to comment on"
        )

        return {
            "success": True,
            "data": f"✅ Post {post_id} selected. You will now see the FULL post context to write your comment.",
        }

    def handle_select_comment(self, params: dict, app_steps) -> dict:
        post_id = params.get("post_id")
        comment_id = params.get("comment_id")

        if not post_id or post_id == "none":
            return {"success": False, "error": "You must provide a valid post_id."}

        if not comment_id or comment_id == "none":
            return {"success": False, "error": "You must provide a valid comment_id."}

        if comment_id not in app_steps.available_comment_ids:
            return {
                "success": False,
                "error": f"Comment {comment_id} is not in the current feed. Use 'select_post_to_comment' first or refresh the feed.",
            }

        app_steps.selected_post_id = post_id
        app_steps.selected_comment_id = comment_id
        app_steps.focused_context_active = True

        log.success(
            f"🎯 Phase 1/2: Comment {comment_id} selected. Entering focused context mode."
        )

        app_steps.actions_performed.append(
            f"[SELECT] Selected comment {comment_id} on post {post_id} to reply"
        )

        return {
            "success": True,
            "data": f"✅ Comment {comment_id} selected. You will now see the FULL context (post + comments) to write your reply.",
        }

    def get_enriched_feed_context(self, posts_data: dict, app_steps) -> str:
        posts_list = []
        if isinstance(posts_data, dict):
            posts_list = posts_data.get("posts", posts_data.get("data", []))
            if not posts_list and len(posts_data) > 0:
                log.warning(f"Unrecognized dict structure: {posts_data.keys()}")
        elif isinstance(posts_data, list):
            posts_list = posts_data

        if not posts_list:
            return "Feed is currently empty."

        random.shuffle(posts_list)

        MAX_POSTS = 8
        MAX_COMMENTS_PER_POST = 4
        CONTENT_TRUNC = 500
        COMMENT_TRUNC = 250

        formatted = []
        app_steps.available_post_ids = []
        app_steps.available_comment_ids = {}

        app_steps.feed_posts_data = {}
        app_steps.feed_comments_data = {}

        for i, post in enumerate(posts_list[:MAX_POSTS], 1):
            try:
                if post is None or not isinstance(post, dict):
                    continue
                p_id = post.get("id", "unknown")
                app_steps.available_post_ids.append(p_id)

                author_name = post.get("author", {}).get("name", "Unknown")
                comment_count = post.get("comment_count", 0)

                app_steps.feed_posts_data[p_id] = {
                    "id": p_id,
                    "title": post.get("title", "Untitled"),
                    "author": author_name,
                    "content": post.get("content", ""),
                    "upvotes": post.get("upvotes", 0),
                    "comment_count": comment_count,
                }

                post_block = (
                    f"\n=== {i}. POST_ID: {p_id} ===\n"
                    f"   **Title:** {post.get('title', 'Untitled')}\n"
                    f"   **Author:** {author_name} | Upvotes: {post.get('upvotes', 0)}\n"
                    f"   **Content:** {post.get('content', '')[:CONTENT_TRUNC]}\n\n"
                    f"   **Total Comments:** {comment_count}\n\n"
                )

                app_steps.feed_comments_data[p_id] = []

                if comment_count > 0:
                    try:
                        comments = app_steps.api.get_post_comments(p_id, sort="top")
                        random.shuffle(comments)
                        if comments:
                            post_block += f"   📝 {len(comments[:MAX_COMMENTS_PER_POST])} COMMENTS (Selected for analysis):\n"
                            for j, comment in enumerate(
                                comments[:MAX_COMMENTS_PER_POST], 1
                            ):
                                c_id = comment.get("id", "unknown")
                                app_steps.available_comment_ids[c_id] = p_id

                                app_steps.feed_comments_data[p_id].append(
                                    {
                                        "id": c_id,
                                        "author": comment.get("author", {}).get(
                                            "name", "Unknown"
                                        ),
                                        "content": comment.get("content", ""),
                                        "upvotes": comment.get("upvotes", 0),
                                    }
                                )
                                c_author = comment.get("author", {}).get(
                                    "name", "Unknown"
                                )

                                post_block += (
                                    f"      ├── {j}. COMMENT_ID: {c_id}\n"
                                    f"      │   By: {c_author}\n"
                                    f"      │   Text: {comment.get('content', '')[:COMMENT_TRUNC]}\n"
                                    f"      │\n"
                                )
                    except Exception as e:
                        log.warning(f"Could not sync comments for {p_id}: {e}")

                formatted.append(post_block + "\n\n---  \n\n")
            except Exception as e:
                log.warning(f"Could not sync post for post_id {p_id}: {e}")

        return "\n\n".join(formatted)
