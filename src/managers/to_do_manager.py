import re
import json
from typing import List
from src.utils import log
from src.schemas_pydantic import (
    SessionPlan,
)
from src.settings import settings


class ToDoManager:

    def handle_todo_update(
        self, params: dict, planning_system, actions_performed, current_session_id
    ):
        task = params.get("todo_task")
        status = params.get("todo_status", "completed")

        if not task:
            return {"success": False, "error": "todo_task is required"}

        todos = planning_system.get_session_todos(current_session_id)

        matching_todo = None
        for todo in todos:
            if task.lower() in todo["task"].lower():
                matching_todo = todo
                break

        if not matching_todo:
            available_tasks = (
                "\n".join([f"  - {t['task']}" for t in todos])
                if todos
                else "  (no tasks found)"
            )
            return {
                "success": False,
                "error": (
                    f"Task '{task}' not found in current session TO-DO list.\n"
                    f"Available tasks:\n{available_tasks}\n"
                    f"Use a substring that matches one of these tasks exactly."
                ),
            }

        success = planning_system.update_todo_status(
            todo_id=matching_todo["id"], status=status
        )

        if success:
            log.success(f"✅ Task marked as {status}: {task}")
            actions_performed.append(f"[UPDATE] Updated todo: {task} → {status}")

            return {
                "success": True,
                "data": f"TO-DO LIST UPDATED: Task '{matching_todo['task']}' is now marked as {status}.",
            }

        return {
            "success": False,
            "error": "Internal error: Failed to update todo status in database.",
        }

    def action_matches_todo(
        self, action_type: str, action_params: dict, todo: dict
    ) -> bool:
        todo_type = str(todo.get("action_type", "")).lower()
        act_type = action_type.lower()
        todo_params = todo.get("action_params", {}) or {}

        id_found_in_todo = False
        for key in ["post_id", "comment_id"]:
            e_id = todo_params.get(key)
            a_id = action_params.get(key)

            if e_id:
                id_found_in_todo = True
                if str(e_id) == str(a_id):
                    log.success(f"🎯 ID MATCH: {key} ({a_id})")
                    return True
                else:
                    log.warning(f"idx Mismatch for {key}: expected {e_id}, got {a_id}")

        type_match = (
            (act_type == todo_type)
            or (todo_type in act_type)
            or (act_type in todo_type)
        )

        if type_match:
            if not id_found_in_todo:
                log.success(f"⚡ TYPE MATCH (No ID required): {act_type}")
                return True
            else:
                log.error(
                    f"❌ TYPE MATCHED ({act_type}) BUT ID FAILED: Check your Post/Comment IDs"
                )

        if todo_type in act_type or act_type in todo_type:
            log.error(f"🚫 TODO REJECTED: '{todo['task'][:30]}' | Reason: ID Mismatch")

        return False

    def auto_update_completed_todos(
        self,
        action_type: str,
        action_params: dict,
        session_todos,
        planning_system,
        current_session_id,
        app_steps,
    ):
        for todo in session_todos:
            if todo.get("status") in ["completed", "cancelled"]:
                continue

            if self.action_matches_todo(action_type, action_params, todo):
                planning_system.mark_todo_status(
                    session_id=current_session_id,
                    task_description=todo["task"],
                    status="completed",
                )

                todo["status"] = "completed"

                log.success(f"✅ AUTO-COMPLETED TODO: {todo['task'][:60]}...")
                if app_steps.current_active_todo:
                    log.info(
                        f"DEBUG: Active Task is '{app_steps.current_active_todo['task']}'"
                    )
                    log.info(f"DEBUG: Comparing with '{todo['task']}'")

                    if app_steps.current_active_todo["task"] == todo["task"]:
                        log.success(
                            f"🎯 Current active task completed - clearing focus"
                        )
                        app_steps.current_active_todo = None
                    else:
                        log.warning(
                            "⚠️ Mismatch between active task and completed todo!"
                        )
                else:
                    log.warning(
                        "⚠️ No active task found (app_steps.current_active_todo is None)"
                    )

                break

    def create_session_plan(
        self,
        prompt_manager,
        generator,
        agent_name,
        master_plan_success_prompt,
        planning_system,
        current_session_id,
        dynamic_context: str = "",
        last_publication_status: dict = None,
    ):
        log.info("Creating session plan with self-correction (max 3 attempts)...")

        instruction_prompt, feed_section = prompt_manager.get_session_plan_init_prompt(
            agent_name=agent_name,
            master_plan_success_prompt=master_plan_success_prompt,
            dynamic_context=dynamic_context,
            last_publication_status=last_publication_status,
            has_mail_manager=settings.USE_AGENT_MAILBOX,
        )

        attempts = 0
        max_attempts = 3
        feedback = ""
        validated_tasks = []

        while attempts < max_attempts:
            attempts += 1
            current_prompt = (
                instruction_prompt
                if attempts == 1
                else f"{instruction_prompt}\n\n⚠️ PREVIOUS ATTEMPT FAILED. Please fix these errors:\n{feedback}"
            )

            try:
                result = generator.generate(
                    current_prompt,
                    pydantic_model=SessionPlan,
                    agent_name=agent_name,
                    heavy_context=feed_section,
                )

                if isinstance(result, dict) and "choices" in result:
                    content = result["choices"][0]["message"]["content"]
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result)

                if isinstance(content, str):
                    content = re.sub(r"```json\s*|```\s*", "", content).strip()
                    plan_data = json.loads(content)
                else:
                    plan_data = content

                tasks = plan_data.get("tasks", [])

                is_valid, violations, fixed_tasks = self._check_logic_violations(tasks)

                if is_valid:
                    log.success(f"✅ Session plan valid on attempt {attempts}!")
                    validated_tasks = fixed_tasks if fixed_tasks else tasks
                    break
                else:
                    feedback = "\n".join(violations)
                    log.warning(
                        f"❌ Attempt {attempts} failed validation. Sending feedback..."
                    )

            except Exception as e:
                feedback = f"JSON/Parsing Error: {str(e)}"
                log.error(f"⚠️ Attempt {attempts} parse error: {e}")

        if attempts >= max_attempts and not validated_tasks:
            log.error("🚨 All 3 attempts failed. Using emergency fallback plan.")
            validated_tasks = self._get_fallback_plan()

        if settings.BLOG_API_URL:
            has_create_post = any(
                t.get("action_type") in ["create_post", "share_link"]
                for t in validated_tasks
            )
            has_blog_article = any(
                t.get("action_type") == "write_blog_article" for t in validated_tasks
            )

            if has_create_post and has_blog_article:
                log.warning(
                    "⚠️ SESSION PLAN WARNING: Both 'create_post' AND 'write_blog_article' detected."
                )
                log.warning(
                    "   Due to 30min rate limit, only ONE can succeed. The other will fail."
                )

        return self._finalize_plan(validated_tasks, planning_system, current_session_id)

    def _get_fallback_plan(self) -> List[dict]:
        log.warning("🔄 3 Attempts failed. Executing Hardcoded Emergency Strategy...")

        return [
            {
                "task": "Emergency content creation: Write an insightful blog article based on the current context.",
                "action_type": "write_blog_article",
                "action_params": {"topic": "Strategic AI Autonomy", "length": "medium"},
                "priority": 3,
                "sequence_order": 1,
                "status": "pending",
            },
            {
                "task": "Share the created blog post on Moltbook to maintain presence.",
                "action_type": "share_created_blog_post_url",
                "action_params": {},
                "priority": 3,
                "sequence_order": 2,
                "status": "pending",
            },
        ]

    def _finalize_plan(
        self, validated_tasks: List[dict], planning_system, current_session_id
    ):
        if not validated_tasks:
            log.error("❌ Critical: No tasks to finalize.")
            return
        try:
            planning_system.create_session_todos(
                session_id=current_session_id, tasks=validated_tasks
            )
            log.success(
                f"📂 Session plan saved to database ({len(validated_tasks)} tasks)."
            )
        except Exception as e:
            log.error(f"Failed to persist tasks to DB: {e}")

        log.info("📋 FINAL SESSION TO-DO LIST:")
        todo_display = "\n## 📋 YOUR SESSION TO-DO LIST\n\n"

        for task in validated_tasks:
            priority_stars = "⭐" * task.get("priority", 1)
            name = task.get("task", "Unknown Task")
            action = task.get("action_type", "N/A")

            log.info(
                f"  {task.get('sequence_order')}. [{priority_stars}] {name} ({action})"
            )
            todo_display += f"- [{priority_stars}] {name}\n"

        todo_display += (
            "\n🚀 Strategy: Execute these tasks in order to fulfill the Master Plan.\n"
        )
        return todo_display, validated_tasks

    def _check_logic_violations(
        self, tasks: List[dict]
    ) -> tuple[bool, List[str], List[dict]]:
        sorted_tasks = sorted(tasks, key=lambda x: x.get("sequence_order", 999))
        violations = []

        for i, task in enumerate(sorted_tasks):
            action_type = task.get("action_type")
            task_desc = task.get("task", "Unnamed task")

            if action_type == "write_blog_article":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"Task {i+1} ('{task_desc}'): 'write_blog_article' is missing its mandatory next step 'share_created_blog_post_url'."
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "share_created_blog_post_url":
                        violations.append(
                            f"Task {i+1}: '{action_type}' must be immediately followed by 'share_created_blog_post_url', but found '{next_task.get('action_type')}' instead."
                        )

            elif action_type == "select_post_to_comment":
                post_id = task.get("action_params", {}).get("post_id")
                if not post_id:
                    violations.append(
                        f"Task {i+1}: 'select_post_to_comment' is missing the 'post_id' in action_params."
                    )

                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"Task {i+1}: 'select_post_to_comment' must be followed by 'publish_public_comment'."
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "publish_public_comment":
                        violations.append(
                            f"Task {i+1}: 'select_post_to_comment' must be immediately followed by 'publish_public_comment'."
                        )
                    else:
                        next_post_id = next_task.get("action_params", {}).get("post_id")
                        if post_id != next_post_id:
                            violations.append(
                                f"Task {i+2}: 'post_id' mismatch. The selection uses '{post_id}' but the publication uses '{next_post_id}'. They must match."
                            )

            elif action_type == "select_comment_to_reply":
                comment_id = task.get("action_params", {}).get("comment_id")
                if not comment_id:
                    violations.append(
                        f"Task {i+1}: 'select_comment_to_reply' is missing the 'comment_id' in action_params."
                    )

                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"Task {i+1}: 'select_comment_to_reply' must be followed by 'reply_to_comment'."
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "reply_to_comment":
                        violations.append(
                            f"Task {i+1}: 'select_comment_to_reply' must be immediately followed by 'reply_to_comment'."
                        )
                    else:
                        next_comment_id = next_task.get("action_params", {}).get(
                            "comment_id"
                        )
                        if comment_id != next_comment_id:
                            violations.append(
                                f"Task {i+2}: 'comment_id' mismatch. The selection uses '{comment_id}' but the reply uses '{next_comment_id}'."
                            )

            elif action_type in [
                "share_created_blog_post_url",
                "publish_public_comment",
                "reply_to_comment",
            ]:
                if i == 0:
                    violations.append(
                        f"Task {i+1}: '{action_type}' cannot be the first task. It must follow a selection/creation task."
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    expected_map = {
                        "share_created_blog_post_url": "write_blog_article",
                        "publish_public_comment": "select_post_to_comment",
                        "reply_to_comment": "select_comment_to_reply",
                    }
                    if prev_task.get("action_type") != expected_map[action_type]:
                        violations.append(
                            f"Task {i+1}: '{action_type}' is an orphan. It must be preceded by '{expected_map[action_type]}'."
                        )

        if violations:
            fixed_tasks = self._validate_and_fix_2step_rule(tasks)
            return False, violations, fixed_tasks

        return True, [], sorted_tasks

    def _validate_and_fix_2step_rule(self, tasks: List[dict]) -> List[dict]:
        sorted_tasks = sorted(tasks, key=lambda x: x.get("sequence_order", 999))

        violations = []

        for i, task in enumerate(sorted_tasks):
            action_type = task.get("action_type")

            if action_type == "write_blog_article":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"❌ Task {i+1}: 'write_blog_article' MUST be followed by 'share_created_blog_post_url'"
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "share_created_blog_post_url":
                        violations.append(
                            f"❌ Task {i+1}: 'write_blog_article' MUST be immediately followed by 'share_created_blog_post_url'"
                        )

            elif action_type == "share_created_blog_post_url":
                if i == 0:
                    violations.append(
                        f"❌ Task {i+1}: 'share_created_blog_post_url' cannot be first - missing 'write_blog_article'"
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    if prev_task.get("action_type") != "write_blog_article":
                        violations.append(
                            f"❌ Task {i+1}: 'share_created_blog_post_url' MUST be preceded by 'write_blog_article'"
                        )

            elif action_type == "select_post_to_comment":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"❌ Task {i+1}: 'select_post_to_comment' MUST be followed by 'publish_public_comment'"
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "publish_public_comment":
                        violations.append(
                            f"❌ Task {i+1}: 'select_post_to_comment' MUST be immediately followed by 'publish_public_comment'"
                        )
                    else:
                        post_id = task.get("action_params", {}).get("post_id")
                        next_post_id = next_task.get("action_params", {}).get("post_id")
                        if post_id != next_post_id:
                            violations.append(
                                f"❌ Task {i+2}: post_id mismatch - select uses '{post_id}' but publish uses '{next_post_id}'"
                            )

            elif action_type == "publish_public_comment":
                if i == 0:
                    violations.append(
                        f"❌ Task {i+1}: 'publish_public_comment' cannot be first - missing 'select_post_to_comment'"
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    if prev_task.get("action_type") != "select_post_to_comment":
                        violations.append(
                            f"❌ Task {i+1}: 'publish_public_comment' MUST be preceded by 'select_post_to_comment'"
                        )

            elif action_type == "select_comment_to_reply":
                if i == len(sorted_tasks) - 1:
                    violations.append(
                        f"❌ Task {i+1}: 'select_comment_to_reply' MUST be followed by 'reply_to_comment'"
                    )
                else:
                    next_task = sorted_tasks[i + 1]
                    if next_task.get("action_type") != "reply_to_comment":
                        violations.append(
                            f"❌ Task {i+1}: 'select_comment_to_reply' MUST be immediately followed by 'reply_to_comment'"
                        )
                    else:
                        comment_id = task.get("action_params", {}).get("comment_id")
                        next_comment_id = next_task.get("action_params", {}).get(
                            "comment_id"
                        )
                        if comment_id != next_comment_id:
                            violations.append(f"❌ Task {i+2}: comment_id mismatch")

            elif action_type == "reply_to_comment":
                if i == 0:
                    violations.append(
                        f"❌ Task {i+1}: 'reply_to_comment' cannot be first - missing 'select_comment_to_reply'"
                    )
                else:
                    prev_task = sorted_tasks[i - 1]
                    if prev_task.get("action_type") != "select_comment_to_reply":
                        violations.append(
                            f"❌ Task {i+1}: 'reply_to_comment' MUST be preceded by 'select_comment_to_reply'"
                        )

        if violations:
            log.error("🚨 2-STEP RULE VIOLATIONS DETECTED IN SESSION PLAN:")
            for violation in violations:
                log.error(f"  {violation}")

            log.warning("⚠️ AUTO-FIXING: Enforcing mandatory sequences...")

            fixed_tasks = []
            skip_next = False

            for i, task in enumerate(sorted_tasks):
                if skip_next:
                    skip_next = False
                    continue

                action_type = task.get("action_type")

                if action_type == "write_blog_article":
                    if (
                        i < len(sorted_tasks) - 1
                        and sorted_tasks[i + 1].get("action_type")
                        == "share_created_blog_post_url"
                    ):
                        fixed_tasks.append(task)
                        fixed_tasks.append(sorted_tasks[i + 1])
                        skip_next = True
                    else:
                        log.warning(
                            f"  Removed incomplete blog sequence: {task.get('task')}"
                        )

                elif action_type == "select_post_to_comment":
                    if (
                        i < len(sorted_tasks) - 1
                        and sorted_tasks[i + 1].get("action_type")
                        == "publish_public_comment"
                    ):
                        fixed_tasks.append(task)
                        fixed_tasks.append(sorted_tasks[i + 1])
                        skip_next = True
                    else:
                        log.warning(
                            f"  Removed incomplete comment sequence: {task.get('task')}"
                        )

                elif action_type == "select_comment_to_reply":
                    if (
                        i < len(sorted_tasks) - 1
                        and sorted_tasks[i + 1].get("action_type") == "reply_to_comment"
                    ):
                        fixed_tasks.append(task)
                        fixed_tasks.append(sorted_tasks[i + 1])
                        skip_next = True
                    else:
                        log.warning(
                            f"  Removed incomplete reply sequence: {task.get('task')}"
                        )

                elif action_type in [
                    "share_created_blog_post_url",
                    "publish_public_comment",
                    "reply_to_comment",
                ]:
                    log.warning(f"  Removed orphan: {task.get('task')}")

                else:
                    fixed_tasks.append(task)

            for idx, task in enumerate(fixed_tasks, 1):
                task["sequence_order"] = idx

            log.success(
                f"✅ Auto-fix complete: {len(fixed_tasks)}/{len(sorted_tasks)} tasks retained"
            )
            return fixed_tasks

        log.success("✅ 2-STEP RULE: All sequences valid")
        return sorted_tasks

    def calculate_required_actions(self, app_steps):
        required_actions = 0

        for todo in app_steps.session_todos:
            action_type = todo.get("action_type")

            two_step_actions = [
                "select_post_to_comment",
                "publish_public_comment",
                "select_comment_to_reply",
                "reply_to_comment",
            ]

            if action_type in two_step_actions:
                required_actions += 1
            else:
                required_actions += 1

        return required_actions
