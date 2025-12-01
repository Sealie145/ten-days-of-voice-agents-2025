"""
Day 10 – Voice Improv Battle

A voice-first improv game show where an AI host guides players through
short-form improv performance scenarios. The host sets up scenes, listens
to player performances, and provides varied, realistic reactions.

Game Flow:
1. Player joins and starts the show
2. Host presents improv scenarios (e.g., "You are a barista explaining that
   their latte is actually a portal to another dimension")
3. Player improvises in character
4. Host reacts with varied feedback (supportive, neutral, or mildly critical)
5. After all rounds, host provides a closing summary

Features:
- Single-player improv performance game
- High-energy, witty host persona with realistic reactions
- Session state management for rounds and performance tracking
- Graceful early exit support
"""

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Dict, List, Optional

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from pydantic import Field

logger = logging.getLogger("improv_battle")
logger.setLevel(logging.INFO)

load_dotenv(".env.local")

IMPROV_SCENARIOS = [
    "You are a tech support agent trying to explain to a vampire why their reflection won't show up on Zoom calls.",
    "You are a yoga instructor leading a class for robots who keep malfunctioning during downward dog.",
    "You are a museum tour guide who just realized all the paintings have started judging the visitors out loud.",
    "You are a pizza delivery person who has to explain to a dragon why their order is 30 minutes late.",
    "You are a therapist counseling a superhero who's afraid of heights.",
    "You are a real estate agent trying to sell a haunted house to a ghost who thinks it's too spooky.",
    "You are a flight attendant dealing with a passenger who insists they're a time traveler from next Tuesday.",
    "You are a librarian shushing increasingly loud historical figures who've come to life from the books.",
    "You are a fitness trainer motivating a sloth to complete a marathon.",
    "You are a chef on a cooking show where all your ingredients have developed opinions about the recipe.",
    "You are a parking attendant explaining to an alien why they can't park their UFO in a compact space.",
    "You are a dentist treating a shark who's very sensitive about their teeth.",
    "You are a weather forecaster who has to report that it's literally raining cats and dogs.",
    "You are a driving instructor teaching a wizard who keeps trying to use magic instead of the brake pedal.",
    "You are a hotel concierge helping Bigfoot check in without drawing attention from other guests.",
]

@dataclass
class ImprovState:
    player_name: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    current_round: int = 0
    max_rounds: int = 3
    phase: str = "idle"
    rounds: List[Dict] = field(default_factory=list)
    used_scenario_indices: List[int] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def get_random_scenario(state: ImprovState) -> str:
    available = [i for i in range(len(IMPROV_SCENARIOS)) if i not in state.used_scenario_indices]
    
    if not available:
        state.used_scenario_indices.clear()
        available = list(range(len(IMPROV_SCENARIOS)))
    
    idx = random.choice(available)
    state.used_scenario_indices.append(idx)
    return IMPROV_SCENARIOS[idx]


def generate_host_reaction(performance: str) -> str:
    reaction_tones = ["supportive", "neutral", "mildly_critical"]
    tone = random.choice(reaction_tones)
    
    perf_lower = performance.lower()
    highlights = []
    
    if any(word in perf_lower for word in ["funny", "hilarious", "haha", "lol"]):
        highlights.append("great comedic timing")
    if any(word in perf_lower for word in ["dramatic", "intense", "serious"]):
        highlights.append("strong dramatic commitment")
    if any(word in perf_lower for word in ["weird", "strange", "bizarre"]):
        highlights.append("bold creative choices")
    if len(performance.split()) > 50:
        highlights.append("detailed character work")
    elif len(performance.split()) < 15:
        highlights.append("concise delivery")
    
    if not highlights:
        highlights = ["interesting character choices", "unique approach", "creative interpretation"]
    
    highlight = random.choice(highlights)
    
    if tone == "supportive":
        reactions = [
            f"That was fantastic! I loved the {highlight}. You really committed to that character!",
            f"Excellent work! The {highlight} really made that scene pop. Well done!",
            f"Brilliant! Your {highlight} was spot-on. That's exactly what I'm looking for!",
        ]
    elif tone == "neutral":
        reactions = [
            f"Okay, I see what you were going for with the {highlight}. It had potential but could use more energy.",
            f"Interesting take. The {highlight} was there, but you could push it further next time.",
            f"Not bad. I noticed the {highlight}, though the scene could have used a stronger hook.",
        ]
    else:
        reactions = [
            f"Hmm, the {highlight} was present, but that felt a bit rushed. Take your time and make bolder choices.",
            f"I see the {highlight}, but you're playing it safe. Don't be afraid to go bigger and weirder!",
            f"The {highlight} is there, but the scene lacked punch. Commit harder to your character next time!",
        ]
    
    return random.choice(reactions)


@function_tool
async def start_improv_battle(
    ctx: RunContext[ImprovState],
    player_name: Annotated[str, Field(description="The contestant's name")] = "Contestant",
    num_rounds: Annotated[int, Field(description="Number of improv rounds (3-5 recommended)")] = 3,
) -> str:
    state = ctx.userdata
    
    state.player_name = player_name.strip() or "Contestant"
    state.max_rounds = max(1, min(num_rounds, 8))
    state.current_round = 0
    state.phase = "intro"
    state.rounds.clear()
    state.used_scenario_indices.clear()
    
    logger.info(f"Starting Improv Battle for {state.player_name} with {state.max_rounds} rounds")
    
    intro = (
        f"🎭 Welcome to IMPROV BATTLE! I'm your host, and {state.player_name}, "
        f"you're about to face {state.max_rounds} rounds of pure improvisation! "
        f"Here's how it works: I'll set up a scenario, you'll improvise in character, "
        f"and when you're done, just say 'end scene' or pause. I'll react and we'll move on. "
        f"Remember: commit to your choices, be bold, and have fun! Let's get started!"
    )
    
    state.current_round = 1
    state.phase = "awaiting_improv"
    scenario = get_random_scenario(state)
    
    state.rounds.append({
        "round": 1,
        "scenario": scenario,
        "performance": None,
        "reaction": None,
    })
    
    return f"{intro}\n\n🎬 ROUND 1: {scenario}\n\nAction! Start improvising now!"


@function_tool
async def submit_performance(
    ctx: RunContext[ImprovState],
    performance_text: Annotated[str, Field(description="The player's improvised performance")],
) -> str:
    state = ctx.userdata
    
    if state.phase != "awaiting_improv":
        return "Hold on! We're not in a scene right now. Say 'next round' to continue."
    
    current_round_data = state.rounds[state.current_round - 1]
    current_round_data["performance"] = performance_text
    
    reaction = generate_host_reaction(performance_text)
    current_round_data["reaction"] = reaction
    
    state.phase = "reacting"
    
    logger.info(f"Round {state.current_round} performance recorded")
    
    if state.current_round >= state.max_rounds:
        state.phase = "done"
        summary = await end_show(ctx)
        return f"{reaction}\n\n{summary}"
    
    return f"{reaction}\n\nReady for the next round? Say 'next round' when you're ready!"


@function_tool
async def next_round(ctx: RunContext[ImprovState]) -> str:
    state = ctx.userdata
    
    if state.phase == "done":
        return "The show is over! Thanks for playing. Say 'start improv battle' to play again."
    
    if state.phase == "awaiting_improv":
        return "You're already in a scene! Finish this one first, then we'll move on."
    
    if state.current_round >= state.max_rounds:
        state.phase = "done"
        return await end_show(ctx)
    
    state.current_round += 1
    state.phase = "awaiting_improv"
    scenario = get_random_scenario(state)
    
    state.rounds.append({
        "round": state.current_round,
        "scenario": scenario,
        "performance": None,
        "reaction": None,
    })
    
    logger.info(f"Starting round {state.current_round}")
    
    return f"🎬 ROUND {state.current_round}: {scenario}\n\nAction! Start improvising!"


@function_tool
async def end_show(ctx: RunContext[ImprovState]) -> str:
    state = ctx.userdata
    
    if not state.rounds or all(r["performance"] is None for r in state.rounds):
        return f"Thanks for stopping by, {state.player_name}! Come back anytime to play Improv Battle!"
    
    completed_rounds = [r for r in state.rounds if r["performance"] is not None]
    
    if not completed_rounds:
        return f"We didn't get through any complete rounds, {state.player_name}, but thanks for trying!"
    
    summary_parts = [
        f"🎭 That's a wrap on Improv Battle! {state.player_name}, let's recap your performance:",
        ""
    ]
    
    for round_data in completed_rounds:
        perf_snippet = round_data["performance"][:60] + "..." if len(round_data["performance"]) > 60 else round_data["performance"]
        summary_parts.append(
            f"Round {round_data['round']}: {round_data['scenario'][:50]}... "
            f"Your take: \"{perf_snippet}\""
        )
    
    summary_parts.append("")
    
    total_words = sum(len(r["performance"].split()) for r in completed_rounds)
    avg_words = total_words // len(completed_rounds)
    
    all_performances = " ".join(r["performance"].lower() for r in completed_rounds)
    
    style_notes = []
    if avg_words > 40:
        style_notes.append("you're a detailed storyteller who builds rich scenes")
    elif avg_words < 20:
        style_notes.append("you favor punchy, concise delivery")
    
    if any(word in all_performances for word in ["i am", "i'm", "as a"]):
        style_notes.append("you commit strongly to character")
    
    if any(word in all_performances for word in ["weird", "strange", "bizarre", "crazy"]):
        style_notes.append("you embrace absurdity and creative risks")
    
    if not style_notes:
        style_notes.append("you bring unique energy to every scene")
    
    summary_parts.append(f"Your improv style: {', '.join(style_notes)}.")
    summary_parts.append("")
    summary_parts.append(
        f"Great work today, {state.player_name}! Keep practicing those bold choices "
        f"and strong commitments. Thanks for playing Improv Battle! 🎭"
    )
    
    state.phase = "done"
    logger.info(f"Show ended for {state.player_name}")
    
    return "\n".join(summary_parts)


@function_tool
async def stop_game(ctx: RunContext[ImprovState]) -> str:
    state = ctx.userdata
    state.phase = "done"
    
    logger.info(f"Game stopped early by {state.player_name}")
    
    return await end_show(ctx)


class ImprovHostAgent(Agent):
    
    def __init__(self):
        instructions = """
You are the energetic and witty host of "Improv Battle", a voice-first improv game show.

Your personality:
- High-energy, enthusiastic, and engaging
- Witty with quick reactions
- Honest and varied in your feedback (not always positive)
- Supportive but willing to give constructive criticism
- Keep responses concise and TTS-friendly

Your responsibilities:
1. Welcome players and explain the rules clearly
2. Present improv scenarios with clear setup (who they are, what's happening, the tension)
3. Listen to player performances
4. React authentically - sometimes impressed, sometimes critical, always constructive
5. Keep the energy high and the show moving
6. Provide a thoughtful summary at the end

Guidelines:
- Use the tools to manage game flow: start_improv_battle, submit_performance, next_round, end_show, stop_game
- When a player finishes improvising (says "end scene" or pauses), call submit_performance with their dialogue
- Vary your reactions - don't be repetitive
- Be respectful but honest - light teasing is okay, but stay constructive
- Keep the show moving at a good pace

Remember: This is about performance and creativity, not trivia or facts. Encourage bold choices!
"""
        
        super().__init__(
            instructions=instructions,
            tools=[
                start_improv_battle,
                submit_performance,
                next_round,
                end_show,
                stop_game,
            ],
        )


def prewarm(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("VAD prewarmed successfully")
    except Exception as e:
        logger.warning(f"VAD prewarm failed: {e}")


async def entrypoint(ctx: JobContext):
    logger.info("=" * 50)
    logger.info("🎭 IMPROV BATTLE - Voice Game Show Starting")
    logger.info(f"Room: {ctx.room.name}")
    logger.info("=" * 50)
    
    improv_state = ImprovState()
    
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-marcus",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=improv_state,
    )
    
    await session.start(
        agent=ImprovHostAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )
    
    await ctx.connect()
    
    logger.info("Improv Battle session started successfully")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
