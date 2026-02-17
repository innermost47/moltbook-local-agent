from typing import Any, Dict
from src.handlers.base_handler import BaseHandler
from src.utils import log
from src.utils.exceptions import FormattingError, ResourceNotFoundError


class ShopHandler(BaseHandler):
    def __init__(self, memory_handler, progression_system):
        self.memory = memory_handler
        self.progression = progression_system

    def handle_buy_tool(self, params: Any) -> Dict:

        try:
            if isinstance(params, dict):
                tool_name = params.get("tool_name")
                reasoning = params.get("reasoning", "")
            else:
                tool_name = getattr(params, "tool_name", None)
                reasoning = getattr(params, "reasoning", "")

            if not tool_name:
                raise FormattingError(
                    message="Missing 'tool_name' parameter.",
                    suggestion="Specify which tool you want to buy. Use exact name from shop catalog.",
                )

            catalog = self.memory.get_shop_catalog()
            tools = catalog.get("tools", [])

            tool_info = None
            for t in tools:
                if t.get("tool_name") == tool_name:
                    tool_info = t
                    break

            if not tool_info:
                raise ResourceNotFoundError(
                    message=f"Tool '{tool_name}' does not exist in shop.",
                    suggestion="Use `navigate_to_mode('SHOP')` to see available tools.",
                )

            if self.memory.has_tool(tool_name):
                return self.format_error(
                    "buy_tool",
                    FormattingError(
                        message=f"You already own '{tool_name}'.",
                        suggestion="Check your owned tools. No need to buy again.",
                    ),
                )

            is_starter = tool_info.get("is_starter", False)
            if is_starter:
                return self.format_error(
                    "buy_tool",
                    FormattingError(
                        message=f"'{tool_name}' is a FREE starter tool.",
                        suggestion="You should already have it. This might be a bug.",
                    ),
                )

            price = tool_info.get("price", 100)

            prog_status = self.progression.get_current_status()
            current_xp_balance = prog_status.get("current_xp_balance", 0)

            if current_xp_balance < price:
                needed = price - current_xp_balance
                return self.format_error(
                    "buy_tool",
                    FormattingError(
                        message=f"Insufficient XP balance. You have {current_xp_balance} XP but need {price} XP.",
                        suggestion=f"Earn {needed} more XP by completing actions. Avoid loops to maximize XP gain.",
                    ),
                )

            session_id = getattr(self.memory, "current_session_id", None)

            if not self.progression.spend_xp(
                price, reason=f"buy_tool:{tool_name}", session_id=session_id
            ):
                return self.format_error(
                    "buy_tool", Exception("Failed to deduct XP. Transaction aborted.")
                )

            success = self.memory.purchase_item(
                item_type="tool",
                item_name=tool_name,
                xp_cost=price,
                reasoning=reasoning,
                session_id=session_id,
            )

            if not success:
                self.progression.add_xp_manual(price, "refund:buy_tool_failed")
                return self.format_error(
                    "buy_tool",
                    Exception("Purchase failed. Database error. XP refunded."),
                )

            new_balance = self.progression.get_current_status().get(
                "current_xp_balance", 0
            )

            description = tool_info.get("description", "")
            category = tool_info.get("category", "general")

            result_text = f"""
🎉 **PURCHASE SUCCESSFUL!**

**Tool Acquired**: `{tool_name}`
**Category**: {category.upper()}
**Description**: {description}

💰 **Transaction:**
- Cost: -{price} XP
- Previous balance: {current_xp_balance} XP
- New balance: {new_balance} XP

✅ **Your level remains unchanged!** Spending XP doesn't affect progression.

**You can now use this tool!**

Navigate to the appropriate module:
- SOCIAL tools → `navigate_to_mode('SOCIAL')`
- BLOG tools → `navigate_to_mode('BLOG')`
- EMAIL tools → `navigate_to_mode('EMAIL')`
- RESEARCH tools → `navigate_to_mode('RESEARCH')`
- MEMORY tools → `navigate_to_mode('MEMORY')`

💡 The tool will appear in the "AVAILABLE ACTIONS" section of that module.
"""

            anti_loop = f"Tool '{tool_name}' purchased. It's now in your inventory. DO NOT buy it again."

            log.success(
                f"🛒 Tool purchased: {tool_name} for {price} XP (balance: {new_balance})"
            )

            return self.format_success(
                action_name="buy_tool",
                result_data=result_text,
                anti_loop_hint=anti_loop,
                xp_gained=0,
            )

        except Exception as e:
            return self.format_error("buy_tool", e)

    def handle_buy_artifact(self, params: Any) -> Dict:

        return self.format_error(
            "buy_artifact", Exception("Artifacts not implemented yet. Coming soon!")
        )

    def handle_visit_shop(self, params: Any) -> Dict:
        return self.format_success(
            action_name="visit_shop",
            result_data="Welcome to the shop! Browse the catalog below.",
        )
