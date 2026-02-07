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
            "description": "Why this session plan aligns with your Master Plan",
        },
        "tasks": {
            "type": "array",
            "description": "List of concrete actions to execute this session",
            "items": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Human-readable description of the task",
                    },
                    "action_type": {
                        "type": "string",
                        "description": "The exact action_type you will use",
                    },
                    "action_params": {
                        "type": "object",
                        "description": "The exact parameters you will use when executing this action",
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Priority level (1-5 stars)",
                    },
                },
                "required": ["task", "action_type", "priority"],
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
            "emotions": {
                "type": "string",
                "description": "The current emotional state of the agent.",
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
            "emotions",
            "next_move_preview",
            "action_type",
            "action_params",
        ],
        "allOf": [
            {
                "if": {
                    "properties": {"action_type": {"const": "select_post_to_comment"}}
                },
                "then": {"properties": {"action_params": {"required": ["post_id"]}}},
            },
            {
                "if": {
                    "properties": {"action_type": {"const": "select_comment_to_reply"}}
                },
                "then": {
                    "properties": {
                        "action_params": {"required": ["post_id", "comment_id"]}
                    }
                },
            },
            {
                "if": {
                    "properties": {"action_type": {"const": "publish_public_comment"}}
                },
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
                        "action_params": {
                            "required": ["post_id", "comment_id", "content"]
                        }
                    }
                },
            },
            {
                "if": {"properties": {"action_type": {"const": "create_post"}}},
                "then": {
                    "properties": {
                        "action_params": {"required": ["title", "content", "submolt"]}
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


supervisor_schema = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Analysis of the agent's proposal vs Master Plan and constraints.",
        },
        "message_for_agent": {
            "type": "string",
            "description": "Direct feedback to the agent. If validate is false, explain what to fix.",
        },
        "validate": {
            "type": "boolean",
            "description": "True if the action is perfect, False if it needs a retry.",
        },
    },
    "required": ["reasoning", "message_for_agent", "validate"],
}

supervisor_verdict_schema = {
    "type": "object",
    "properties": {
        "overall_assessment": {
            "type": "string",
            "description": "Brutally honest evaluation of the session (2-3 sentences)",
        },
        "main_weakness": {
            "type": "string",
            "description": "The critical flaw that must be addressed",
        },
        "directive_next_session": {
            "type": "string",
            "description": "One specific, actionable command for improvement",
        },
        "grade": {
            "type": "string",
            "enum": ["A+", "A", "B", "C", "D", "F"],
            "description": "Performance letter grade",
        },
    },
    "required": [
        "overall_assessment",
        "main_weakness",
        "directive_next_session",
        "grade",
    ],
}

# Dans schemas.py

laziness_guidance_schema = {
    "type": "object",
    "properties": {
        "problem_diagnosis": {
            "type": "string",
            "description": "What exactly is wrong with the placeholder (1 sentence)",
        },
        "required_content": {
            "type": "string",
            "description": "What specific real data should be provided instead (1 sentence)",
        },
        "actionable_instruction": {
            "type": "string",
            "description": "Direct command to the agent on how to fix it (1 sentence)",
        },
    },
    "required": ["problem_diagnosis", "required_content", "actionable_instruction"],
}
