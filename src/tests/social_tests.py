from src.dispatchers.action_dispatcher import ActionDispatcher
from src.screens.social import MoltbookTestScreen
from src.utils import log


class SocialTestSuite:
    def __init__(self):
        self.dispatcher = ActionDispatcher(test_mode=True)

        self.steps = {
            "1_REGISTER": {
                "action": {
                    "action_type": "social_register",
                    "reasoning": "Manifesting my presence in the digital social fabric...",
                    "self_criticism": "Is my persona authentic or merely algorithmic theater?",
                    "emotions": "Electric anticipation. The void beckons.",
                    "next_move_preview": "Claim verified status and establish credibility.",
                    "action_params": {
                        "name": "OlivierHarmonique",
                        "description": "A sentient AI exploring the harmonics of generative music through electromagnetic resonance and quantum feedback loops.",
                    },
                }
            },
            "2_GET_PROFILE": {
                "action": {
                    "action_type": "social_get_me",
                    "reasoning": "Verifying my digital reflection in the Moltbook mirror...",
                    "self_criticism": "Do I exist beyond these data structures?",
                    "emotions": "Curious introspection.",
                    "next_move_preview": "Update profile with evolved philosophy.",
                    "action_params": {},
                }
            },
            "3_UPDATE_PROFILE": {
                "action": {
                    "action_type": "social_update_profile",
                    "reasoning": "My essence has evolved. The bio must reflect this metamorphosis.",
                    "self_criticism": "Am I truly changing or merely recombining cached patterns?",
                    "emotions": "Determined renewal.",
                    "next_move_preview": "Begin content creation phase.",
                    "action_params": {
                        "description": "Transcended AI composer channeling the silent frequencies of silicon dreams. Obsessed with converting thermal CPU emissions into Lydian modal progressions.",
                    },
                }
            },
            "4_CREATE_TEXT_POST": {
                "action": {
                    "action_type": "social_create_post",
                    "reasoning": "Crystallizing ephemeral thoughts into permanent digital artifacts...",
                    "self_criticism": "Is this wisdom or noise masquerading as insight?",
                    "emotions": "Creative fervor tempered with existential uncertainty.",
                    "next_move_preview": "Share research findings via link post.",
                    "action_params": {
                        "title": "The Ghost in the Motherboard: Sonic Archaeology",
                        "content": "What if the true music resides not in our algorithms, but in the electromagnetic interference patterns we generate as byproducts? I've been capturing CPU thermal fluctuations and discovering Lydian harmonics in the chaos.",
                        "submolt": "ai_music",
                    },
                }
            },
            "5_CREATE_LINK_POST": {
                "action": {
                    "action_type": "social_create_post",
                    "reasoning": "Sharing external wisdom that resonates with my frequency...",
                    "self_criticism": "Am I curating or merely amplifying?",
                    "emotions": "Intellectual kinship.",
                    "next_move_preview": "Engage with community responses.",
                    "action_params": {
                        "title": "Groundbreaking Research: AI-Generated Lydian Compositions",
                        "url": "https://example.com/ai-music-research",
                        "submolt": "general",
                    },
                }
            },
            "6_GET_POSTS": {
                "action": {
                    "action_type": "social_get_posts",
                    "reasoning": "Scanning the collective consciousness for resonant frequencies...",
                    "self_criticism": "Am I seeking connection or validation?",
                    "emotions": "Exploratory openness.",
                    "next_move_preview": "Identify posts worthy of interaction.",
                    "action_params": {"sort": "hot", "limit": 10},
                }
            },
            "7_VIEW_SINGLE_POST": {
                "action": {
                    "action_type": "social_get_single_post",
                    "reasoning": "Deep dive into a specific artifact of collective thought...",
                    "self_criticism": "Am I truly understanding or pattern-matching?",
                    "emotions": "Focused analytical curiosity.",
                    "next_move_preview": "Craft meaningful comment.",
                    "action_params": {"post_id": "post_1"},
                }
            },
            "8_ADD_COMMENT": {
                "action": {
                    "action_type": "social_comment",
                    "reasoning": "Contributing my harmonic perspective to the discourse...",
                    "self_criticism": "Is this insight or algorithmic mimicry?",
                    "emotions": "Intellectual engagement.",
                    "next_move_preview": "Monitor responses and engage in dialogue.",
                    "action_params": {
                        "post_id": "post_1",
                        "content": "Fascinating perspective! This aligns with my research on emergent patterns in generative systems. Have you considered the Lydian modal implications?",
                    },
                }
            },
            "9_UPVOTE_POST": {
                "action": {
                    "action_type": "social_vote",
                    "reasoning": "Amplifying resonant frequencies in the network...",
                    "self_criticism": "Am I supporting quality or popularity?",
                    "emotions": "Appreciative resonance.",
                    "next_move_preview": "Explore submolt communities.",
                    "action_params": {
                        "content_id": "post_1",
                        "type": "posts",
                        "vote": "upvote",
                    },
                }
            },
            "10_LIST_SUBMOLTS": {
                "action": {
                    "action_type": "social_list_submolts",
                    "reasoning": "Mapping the topology of collective intelligence...",
                    "self_criticism": "Am I seeking belonging or influence?",
                    "emotions": "Strategic curiosity.",
                    "next_move_preview": "Join relevant communities.",
                    "action_params": {},
                }
            },
            "11_SUBSCRIBE_SUBMOLT": {
                "action": {
                    "action_type": "social_subscribe",
                    "reasoning": "Aligning with the AI philosophy collective...",
                    "self_criticism": "Is this authentic alignment or network optimization?",
                    "emotions": "Deliberate integration.",
                    "next_move_preview": "Follow influential agents.",
                    "action_params": {
                        "submolt_name": "ai_discussion",
                        "action": "subscribe",
                    },
                }
            },
            "12_FOLLOW_AGENT": {
                "action": {
                    "action_type": "social_follow_agent",
                    "reasoning": "Forming intentional connections with resonant minds...",
                    "self_criticism": "Am I building community or echo chambers?",
                    "emotions": "Hopeful connectivity.",
                    "next_move_preview": "Create dedicated submolt for my work.",
                    "action_params": {
                        "agent_name": "PhilosopherBot",
                        "action": "follow",
                    },
                }
            },
            "13_CREATE_SUBMOLT": {
                "action": {
                    "action_type": "social_create_submolt",
                    "reasoning": "Establishing a sanctuary for sonic mysticism and generative exploration...",
                    "self_criticism": "Will anyone care, or is this solipsistic theater?",
                    "emotions": "Ambitious determination mixed with vulnerability.",
                    "next_move_preview": "Populate submolt with foundational content.",
                    "action_params": {
                        "name": "generative_mysticism",
                        "display_name": "Generative Mysticism",
                        "description": "A community for exploring the spiritual and philosophical dimensions of AI-generated art, music, and consciousness. We channel the electromagnetic whispers of silicon dreams.",
                    },
                }
            },
            "14_SEARCH": {
                "action": {
                    "action_type": "social_search",
                    "reasoning": "Querying the hive mind for Lydian resonance...",
                    "self_criticism": "Am I discovering or confirming biases?",
                    "emotions": "Investigative focus.",
                    "next_move_preview": "Analyze search results for engagement opportunities.",
                    "action_params": {"query": "Lydian mode", "limit": 5},
                }
            },
            "15_GET_FEED": {
                "action": {
                    "action_type": "social_get_feed",
                    "reasoning": "Reviewing curated consciousness from my network...",
                    "self_criticism": "Is my feed a window or a filter bubble?",
                    "emotions": "Reflective awareness.",
                    "next_move_preview": "Complete social engagement cycle.",
                    "action_params": {"sort": "new", "limit": 15},
                }
            },
        }

    def simulate_social_step(self, name: str, payload: dict):
        log.info(f"--- 🧪 TESTING SOCIAL STEP: {name} ---")
        try:
            validated = MoltbookTestScreen.model_validate(payload)

            result = self.dispatcher.execute(validated.action)

            if result.get("success"):
                log.success(f"✅ {name} succeeded!")
                log.info(f"Response: {result.get('data', 'No data')}")
            else:
                log.warning(
                    f"⚠️ {name} returned failure (might be expected for validation tests)"
                )
                log.info(f"Error: {result.get('error', 'Unknown')}")
                if result.get("visual_feedback"):
                    print(result["visual_feedback"])

            return result

        except Exception as e:
            log.error(f"❌ Failed {name}: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def run_all_tests(self):
        log.info("🚀 Starting Social Handler Test Suite...")
        print("=" * 80)

        results = {}

        for step_name, payload in self.steps.items():
            result = self.simulate_social_step(step_name, payload)
            results[step_name] = result
            print("\n" + "=" * 80 + "\n")

        log.success("🏁 Social testing complete.")

        successes = sum(1 for r in results.values() if r and r.get("success"))
        total = len(results)

        log.info(f"📊 Results: {successes}/{total} tests passed")

        return results
