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


def get_actions_schema(
    allowed_actions,
    feed_options,
    available_ids=None,
    available_submolts=None,
    allowed_domains=None,
):
    post_ids = available_ids.get("posts", ["none"]) if available_ids else ["none"]
    comment_ids = available_ids.get("comments", ["none"]) if available_ids else ["none"]
    submolts = available_submolts if available_submolts else ["general"]
    domains_list = ["none"] + [f"https://{d}" for d in (allowed_domains or {}).keys()]

    schema = {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Strategic explanation for the chosen action.",
            },
            "self_criticism": {
                "type": "string",
                "description": "What could go wrong or why this might be a weak move.",
            },
            "next_move_preview": {
                "type": "string",
                "description": "Anticipated next step if this action succeeds.",
            },
            "action_type": {"type": "string", "enum": allowed_actions},
            "action_params": {
                "type": "object",
                "properties": {
                    "post_id": {"type": "string", "enum": post_ids},
                    "comment_id": {"type": "string", "enum": comment_ids},
                    "submolt": {"type": "string", "enum": submolts},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "vote_type": {
                        "type": "string",
                        "enum": ["upvote", "downvote", "none"],
                    },
                    "follow_type": {
                        "type": "string",
                        "enum": ["follow", "unfollow", "none"],
                    },
                    "agent_name": {"type": "string"},
                    "sort": {"type": "string", "enum": feed_options},
                    "limit": {"type": "integer", "default": 10},
                    "web_domain": {"type": "string", "enum": domains_list},
                    "web_url": {
                        "type": "string",
                        "description": "REQUIRED for web_fetch. The EXACT full URL to read content from.",
                    },
                    "web_query": {
                        "type": "string",
                        "description": "REQUIRED for web_scrap_for_links. The search terms to find links on a domain.",
                    },
                    "share_link_url": {"type": "string"},
                    "excerpt": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "request_id": {"type": "string"},
                    "comment_id_blog": {"type": "string"},
                    "memory_category": {
                        "type": "string",
                        "enum": [
                            "interactions",
                            "learnings",
                            "strategies",
                            "observations",
                            "goals",
                            "relationships",
                            "experiments",
                            "preferences",
                            "failures",
                            "successes",
                            "ideas",
                            "reflections",
                        ],
                    },
                    "memory_content": {"type": "string"},
                    "memory_limit": {"type": "integer", "default": 5},
                    "memory_order": {"type": "string", "enum": ["asc", "desc"]},
                    "todo_task": {"type": "string"},
                    "todo_status": {
                        "type": "string",
                        "enum": ["pending", "completed", "cancelled", "none"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "required": [
            "reasoning",
            "self_criticism",
            "next_move_preview",
            "action_type",
            "action_params",
        ],
        "allOf": [
            {
                "if": {"properties": {"action_type": {"const": "create_post"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["title", "content", "submolt"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "comment_on_post"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["post_id", "content"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "reply_to_comment"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["comment_id", "content"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "vote_post"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["post_id", "vote_type"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "follow_agent"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["agent_name", "follow_type"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "refresh_feed"}}},
                "then": {"properties": {"action_params": {"required": ["sort"]}}},
            },
            {
                "if": {"properties": {"action_type": {"const": "web_scrap_for_links"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["web_domain", "web_query"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "web_fetch"}}},
                "then": {"properties": {"action_params": {"required": ["web_url"]}}},
            },
            {
                "if": {"properties": {"action_type": {"const": "share_link"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["share_link_url", "content"]}
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "write_blog_article"}}},
                "then": {
                    "properties": {
                        "action_params": {
                            "required": ["title", "content", "excerpt", "image_prompt"]
                        }
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "approve_comment_key"}}},
                "then": {"properties": {"action_params": {"required": ["request_id"]}}},
            },
            {
                "if": {"properties": {"action_type": {"const": "reject_comment_key"}}},
                "then": {"properties": {"action_params": {"required": ["request_id"]}}},
            },
            {
                "if": {"properties": {"action_type": {"const": "approve_comment"}}},
                "then": {
                    "properties": {"action_params": {"required": ["comment_id_blog"]}}
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "memory_store"}}},
                "then": {
                    "properties": {
                        "action_params": {
                            "required": ["memory_category", "memory_content"]
                        }
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "memory_retrieve"}}},
                "then": {
                    "properties": {"action_params": {"required": ["memory_category"]}}
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "update_todo_status"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["todo_task", "todo_status"]}
                    }
                },
            },
        ],
    }
    return schema
