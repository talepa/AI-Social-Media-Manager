"""
agents/writer_agent.py

Module 6: Writer Agent

RESPONSIBILITY: Transform each PostIdea from the WeeklyContentPlan into a
fully-written, platform-specific social media post, complete with body copy,
hashtags, and a call-to-action (CTA).

KEY DESIGN DECISIONS:
1. BRAND VOICE SUPPORT — The agent accepts a `brand_voice` string that is
   injected directly into the system prompt. This lets callers swap the voice
   at runtime (e.g., "professional", "casual", "witty") without changing code.

2. PER-PLATFORM PROMPTS — LinkedIn, Instagram, and Twitter have fundamentally
   different optimal formats. Instead of one generic prompt, we define
   platform-specific guidelines in the system message so the LLM produces
   correctly-formatted output without post-processing.

3. STRUCTURED OUTPUT — We use Pydantic's WrittenPost schema to enforce output
   structure. The LLM cannot return plain prose; it must return validated JSON.
   This ensures the Reviewer Agent always receives a predictable object.

4. BATCH PROCESSING — The agent processes ALL PostIdeas from the plan in a
   single invocation loop, returning a WrittenContentBatch. This batched
   approach means one API call to the agent produces the full week's content.
"""

from typing import List
from langchain_core.prompts import ChatPromptTemplate

# Import the plan schema (input from Module 5)
from app.schemas.plan import WeeklyContentPlan, PostIdea

# Import the content schema (output of Module 6)
from app.schemas.content import WrittenPost, WrittenContentBatch


# ==========================================
# 1. Brand Voice Presets
# ==========================================
# WHY presets?
# Brand voice is a key differentiator in social media. By defining named presets,
# we give the UI/API a clean enum to offer users, while still keeping the system
# flexible enough to accept a custom string if needed.
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
# WHY inject these into the prompt?
# Each platform has its own culture, algorithm, and audience expectation.
# Providing explicit rules in the prompt is more reliable than hoping the LLM
# infers the correct format from examples alone.
PLATFORM_RULES = {
    "LinkedIn": (
        "LinkedIn Rules:\n"
        "- Word count: 150-300 words\n"
        "- Start with a strong hook line (no greeting)\n"
        "- Use short paragraphs (1-2 sentences each)\n"
        "- Add 3-5 relevant professional hashtags\n"
        "- CTA: invite professional discussion or link to a resource\n"
        "- Tone should align with brand voice but remain professional"
    ),
    "Instagram": (
        "Instagram Rules:\n"
        "- Word count: 100-150 words (caption body)\n"
        "- Start with an attention-grabbing first line (shows before 'more')\n"
        "- Use emojis sparingly to add visual rhythm (2-4 max)\n"
        "- Add 10-15 highly relevant hashtags at the end\n"
        "- CTA: direct to 'link in bio' or ask a question to drive comments\n"
        "- Tone should feel personal and visually descriptive"
    ),
    "Twitter": (
        "Twitter/X Rules:\n"
        "- HARD LIMIT: entire post body must be under 280 characters\n"
        "- Be direct and punchy — no filler words\n"
        "- Use 1-2 hashtags maximum (they count toward character limit)\n"
        "- CTA: ask for retweets, replies, or a yes/no opinion\n"
        "- Every word must earn its place"
    ),
    "Facebook": (
        "Facebook Rules:\n"
        "- Word count: 100-200 words\n"
        "- Conversational and community-oriented tone\n"
        "- Ask a question to drive comments and shares\n"
        "- Add 2-3 broad hashtags\n"
        "- CTA: encourage sharing or tagging a friend"
    ),
}


# ==========================================
# 3. Writer Prompt
# ==========================================
# WHY two-message structure (system + human)?
# - The "system" message sets the writer's persona, brand voice, and
#   platform-specific rules ONCE. This is the stable context.
# - The "human" message provides the dynamic per-post input.
# This separation is both a LangChain best practice and a token efficiency
# technique — in production, the system message can be cached by the LLM API.
WRITER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a professional social media copywriter with 10 years of experience.

Brand Voice: {brand_voice_description}

You are writing a {platform} post. Follow these rules EXACTLY:
{platform_rules}

Always return structured output with these fields:
- body: the main post text
- hashtags: a list of hashtag strings (without the # symbol)
- call_to_action: a single clear CTA sentence
- brand_voice_applied: a brief note on which brand voice rules you applied
""",
    ),
    (
        "human",
        """Write a {content_type} post for {platform} about the following topic:

Topic: {topic}
Content Summary: {content_summary}

Audience: {target_audience}

Now write the post following all platform and brand voice rules.
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
    Writes a single social media post for one PostIdea.

    WHY a private helper?
    The public `run_writer_agent` function handles the batch loop.
    Isolating the per-post logic here makes it independently testable
    and easier to parallelize in a future async implementation.
    """
    voice_description = BRAND_VOICE_PRESETS.get(
        brand_voice.lower(),
        brand_voice,  # If not a preset, use the raw string as the voice description
    )
    platform_rules = PLATFORM_RULES.get(post_idea.platform, "Follow standard social media best practices.")

    # --- Production Implementation (commented out until LLM keys configured) ---
    # from langchain_openai import ChatOpenAI
    # llm = ChatOpenAI(model="gpt-4-turbo")
    # structured_llm = llm.with_structured_output(WrittenPost)
    # chain = WRITER_PROMPT | structured_llm
    # return chain.invoke({
    #     "brand_voice_description": voice_description,
    #     "platform": post_idea.platform,
    #     "platform_rules": platform_rules,
    #     "content_type": post_idea.content_type,
    #     "topic": post_idea.topic,
    #     "content_summary": post_idea.content_summary,
    #     "target_audience": target_audience,
    # })

    # --- Mock Implementation ---
    # WHY mock here? Demonstrates the pipeline structure and validates
    # schemas end-to-end before a live LLM key is wired in.
    return _mock_post(post_idea, brand_voice, voice_description)


def _mock_post(post_idea: PostIdea, brand_voice: str, voice_description: str) -> WrittenPost:
    """
    Generates a realistic mock post based on platform and content type.
    Each mock demonstrates what the LLM output would look like in production.
    """
    platform = post_idea.platform

    # Platform-specific mock bodies to demonstrate correct format/length
    if platform == "LinkedIn":
        body = (
            f"The way we think about {post_idea.topic} is fundamentally changing.\n\n"
            f"Three years ago, most professionals dismissed this shift. Today, it's impossible to ignore.\n\n"
            f"Here's what {post_idea.content_type.lower()} leaders are doing differently:\n\n"
            f"→ They're treating it as a core business driver, not a side experiment.\n"
            f"→ They're investing in understanding the audience before creating content.\n"
            f"→ They're measuring outcomes, not just outputs.\n\n"
            f"The question isn't whether to adapt. It's how fast you can."
        )
        hashtags = ["SocialMediaStrategy", "ContentMarketing", "AIMarketing", "DigitalGrowth"]
        cta = "What's your biggest challenge with this right now? Drop it in the comments — let's figure it out together."

    elif platform == "Instagram":
        body = (
            f"✨ {post_idea.topic} — and here's why it matters to YOU.\n\n"
            f"We've been tracking this trend for months, and the data is clear:\n"
            f"brands that embrace this approach see 3x more engagement on average.\n\n"
            f"Swipe through to see exactly how we break it down 👉\n\n"
            f"Save this post — you'll want to come back to it. 🔖"
        )
        hashtags = [
            "ContentStrategy", "SocialMediaTips", "DigitalMarketing",
            "MarketingStrategy", "AITools", "GrowthHacking", "CreatorEconomy",
            "ContentCreator", "MarketingTips", "BrandBuilding",
        ]
        cta = "Link in bio for the full breakdown. Drop a 🔥 if you found this useful!"

    elif platform == "Twitter":
        body = f"Hot take: {post_idea.topic} is the most underrated growth lever in 2025. Change my mind. 👇"
        hashtags = ["AIMarketing", "ContentStrategy"]
        cta = "Retweet if you agree. Reply if you don't."

    else:  # Facebook
        body = (
            f"We've been thinking a lot about {post_idea.topic} lately, and we'd love your take on it.\n\n"
            f"{post_idea.content_summary}\n\n"
            f"Tell us — how is your business or team approaching this?"
        )
        hashtags = ["Marketing", "Business", "ContentMarketing"]
        cta = "Share this with a colleague who needs to see it!"

    return WrittenPost(
        platform=platform,
        topic=post_idea.topic,
        body=body,
        hashtags=hashtags,
        call_to_action=cta,
        content_type=post_idea.content_type,
        brand_voice_applied=(
            f"Applied '{brand_voice}' brand voice: {voice_description[:80]}... "
            f"Adjusted sentence length and vocabulary to match {platform} audience norms."
        ),
    )


def run_writer_agent(
    content_plan: WeeklyContentPlan,
    brand_voice: str = "professional",
) -> WrittenContentBatch:
    """
    Executes the Writer Agent for an entire week's content plan.

    Takes the WeeklyContentPlan (Module 5 output) and writes a fully-crafted
    post for EVERY PostIdea in the plan. Returns a WrittenContentBatch that is
    ready to be reviewed by the Reviewer Agent (Module 7).

    Args:
        content_plan:  A WeeklyContentPlan from the Planner Agent.
        brand_voice:   Voice preset ('professional', 'casual', 'witty',
                       'inspirational') or a custom voice description string.

    Returns:
        A WrittenContentBatch with one WrittenPost per PostIdea.
    """
    written_posts: List[WrittenPost] = []

    for post_idea in content_plan.post_ideas:
        # WHY iterate here and not inside the prompt?
        # Each post needs its own platform-specific context window.
        # Sending all posts in one prompt risks the LLM conflating formats
        # across platforms (e.g., writing LinkedIn-length text for Twitter).
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
