summary_schema = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Your thought process about this session",
        },
        "learnings": {
            "type": "string",
            "description": "What you learned from interactions and feedback",
        },
        "next_session_plan": {
            "type": "string",
            "description": "What you plan to do in the next session",
        },
    },
    "required": ["reasoning", "learnings", "next_session_plan"],
}

master_plan_schema = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Your strategic thought process",
        },
        "objective": {
            "type": "string",
            "description": "The supreme long-term goal",
        },
        "strategy": {
            "type": "string",
            "description": "The global methodology to reach the objective",
        },
        "milestones": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key steps to track progress",
        },
    },
    "required": ["reasoning", "objective", "strategy", "milestones"],
}

session_plan_schema = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Why these tasks align with your strategy",
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["task", "priority"],
            },
        },
    },
    "required": ["reasoning", "tasks"],
}

update_master_plan_schema = {
    "type": "object",
    "properties": {
        "should_update": {"type": "boolean"},
        "reasoning": {"type": "string"},
        "new_objective": {"type": "string"},
        "new_strategy": {"type": "string"},
        "new_milestones": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["should_update", "reasoning"],
}


def get_actions_schema(allowed_actions, feed_options):
    return {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "action_type": {
                "type": "string",
                "enum": allowed_actions,
            },
            "action_params": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "string"},
                    "comment_id": {"type": "string"},
                    "submolt": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "excerpt": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "url": {"type": "string"},
                    "comment_id_blog": {"type": "string"},
                    "request_id": {"type": "string"},
                    "agent_name": {"type": "string"},
                    "follow_type": {
                        "type": "string",
                        "enum": ["follow", "unfollow", "none"],
                    },
                    "vote_type": {
                        "type": "string",
                        "enum": ["upvote", "downvote", "none"],
                    },
                    "sort": {"type": "string", "enum": feed_options},
                    "limit": {"type": "integer", "default": 10},
                    "web_url": {"type": "string"},
                    "web_domain": {"type": "string"},
                    "web_query": {"type": "string"},
                    "memory_category": {"type": "string"},
                    "memory_content": {"type": "string"},
                    "memory_limit": {"type": "integer", "default": 5},
                    "memory_order": {"type": "string", "enum": ["asc", "desc"]},
                    "todo_task": {"type": "string"},
                    "todo_status": {
                        "type": "string",
                        "enum": ["pending", "completed", "cancelled", "none"],
                    },
                },
            },
        },
        "required": ["reasoning", "action_type", "action_params"],
    }
