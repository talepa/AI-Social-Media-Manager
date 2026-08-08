"""
agents/writer_agent.py

Module 6: Writer Agent

RESPONSIBILITY: Transform each PostIdea from the WeeklyContentPlan into a
fully-written, platform-specific social media post using Google Gemini.

KEY DESIGN DECISIONS:
1. BRAND VOICE — injected into the system prompt at runtime so callers can
   swap voice without changing any code.
2. PER-PLATFORM PROMPTS — platform-specific rules in the system message so
   Gemini produces correctly-formatted output without post-processing.
3. STRUCTURED OUTPUT — WrittenPost schema enforced via Gemini's function calling.
4. TEMPERATURE 0.8 — higher creativity for writing vs. research/planning.
"""

from typing import List
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_llm
from app.schemas.plan import WeeklyContentPlan, PostIdea
from app.schemas.content import WrittenPost, WrittenContentBatch


# ==========================================
# 1. Brand Voice Presets
# ==========================================
BRAND_VOICE_PRESETS = {
    "professional": (
        "authoritative, data-driven, and formal. Use industry terminology. "
        "Avoid slang. Lead with insights, back them with evidence."
    ),
    "casual": (
        "friendly, conversational, and approachable. Use contractions. "
        "Write as if talking to a smart friend. Keep sentences short."
    ),
    "witty": (
        "clever, slightly humorous, and punchy. Use wordplay where appropriate. "
        "Keep the tone light but ensure the core message is always clear."
    ),
    "inspirational": (
        "motivating, uplifting, and forward-looking. Use active voice. "
        "Avoid negativity. End with an empowering call to action."
    ),
}


# ==========================================
# 2. Platform-Specific Writing Rules
# ==========================================
PLATFORM_RULES = {
    "LinkedIn": (
        "LinkedIn Rules:\n"
        "- Word count: 150-300 words\n"
        "- Start with a strong hook line (NO greeting like 'Hey everyone')\n"
        "- Use short paragraphs (1-2 sentences each)\n"
        "- Add 3-5 relevant professional hashtags (without the # symbol)\n"
        "- CTA: invite professional discussion or link to a resource\n"
        "- Do NOT use emojis excessively — max 2-3 subtle ones"
    ),
    "Instagram": (
        "Instagram Rules:\n"
        "- Word count: 100-150 words (caption body)\n"
        "- Start with an attention-grabbing first line (shows before 'more')\n"
        "- Use 3-5 emojis to add visual rhythm\n"
        "- Add 10-15 highly relevant hashtags (without the # symbol)\n"
        "- CTA: direct to 'link in bio' or ask a question to drive comments\n"
        "- Tone should feel personal and visually descriptive"
    ),
    "Twitter": (
        "Twitter/X Rules:\n"
        "- HARD LIMIT: entire post body must be under 280 characters (count carefully!)\n"
        "- Be direct and punchy — every word earns its place\n"
        "- Use 1-2 hashtags MAXIMUM (they count toward character limit)\n"
        "- CTA: ask for retweets, replies, or a yes/no opinion\n"
        "- Can use 1-2 emojis if they add meaning"
    ),
    "Facebook": (
        "Facebook Rules:\n"
        "- Word count: 100-200 words\n"
        "- Conversational and community-oriented tone\n"
        "- Ask a question to drive comments and shares\n"
        "- Add 2-3 broad hashtags (without the # symbol)\n"
        "- CTA: encourage sharing or tagging a friend"
    ),
}


# ==========================================
# 3. Writer Prompt
# ==========================================
WRITER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a professional social media copywriter with 10 years of experience.

Brand Voice: {brand_voice_description}

You are writing a {platform} post. Follow these platform rules EXACTLY:
{platform_rules}

Return structured output with these fields:
- body: the complete post text (follow word/character limits strictly)
- hashtags: list of hashtag strings WITHOUT the # symbol
- call_to_action: a single clear CTA sentence (already included at end of body, but also return standalone)
- brand_voice_applied: brief note (1 sentence) on how you applied the brand voice
""",
    ),
    (
        "human",
        """Write a {content_type} post for {platform} about:

Topic: {topic}
What to convey: {content_summary}
Target audience: {target_audience}

Write the full post now following all platform and brand voice rules.
""",
    ),
])


# ==========================================
# 4. Writer Agent Runner
# ==========================================
def _write_single_post(
    post_idea: PostIdea,
    brand_voice: str,
    target_audience: str,
) -> WrittenPost:
    """
    Writes a single social media post for one PostIdea using Gemini.

    WHY a private helper?
    The public run_writer_agent handles the batch loop. Isolating per-post
    logic here makes it independently testable and easier to parallelise later.
    """
    voice_description = BRAND_VOICE_PRESETS.get(
        brand_voice.lower(),
        brand_voice,  # If not a preset key, use the raw string as voice description
    )
    platform_rules = PLATFORM_RULES.get(
        post_idea.platform,
        "Follow standard social media best practices.",
    )

    # Higher temperature (0.8) for writing — we want creative, varied output
    llm = get_llm(temperature=0.8)
    structured_llm = llm.with_structured_output(WrittenPost)

    chain = WRITER_PROMPT | structured_llm

    return chain.invoke({
        "brand_voice_description": voice_description,
        "platform": post_idea.platform,
        "platform_rules": platform_rules,
        "content_type": post_idea.content_type,
        "topic": post_idea.topic,
        "content_summary": post_idea.content_summary,
        "target_audience": target_audience,
    })


def run_writer_agent(
    content_plan: WeeklyContentPlan,
    brand_voice: str = "professional",
) -> WrittenContentBatch:
    """
    Executes the Writer Agent for an entire week's content plan.

    Iterates over every PostIdea in the plan and calls Gemini once per post
    to generate platform-specific, brand-voice-consistent content.

    WHY one LLM call per post (not one call for all)?
    Each post needs its own platform-specific context. Sending all posts in
    one prompt risks Gemini mixing formats (e.g. writing LinkedIn-length text
    for a Twitter post). One call per post = clean, correct output every time.

    Args:
        content_plan:  A WeeklyContentPlan from the Planner Agent.
        brand_voice:   Voice preset key or custom description string.

    Returns:
        A WrittenContentBatch with one WrittenPost per PostIdea.
    """
    written_posts: List[WrittenPost] = []

    for post_idea in content_plan.post_ideas:
        written_post = _write_single_post(
            post_idea=post_idea,
            brand_voice=brand_voice,
            target_audience=content_plan.target_audience,
        )
        written_posts.append(written_post)

    return WrittenContentBatch(
        research_topic=content_plan.research_topic,
        brand_voice=brand_voice,
        posts=written_posts,
    )
