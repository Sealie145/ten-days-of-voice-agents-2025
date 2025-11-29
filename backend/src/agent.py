# agent.py
import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
    tokenize,
)

from livekit.plugins import murf, google, deepgram, noise_cancellation

from game_tools import (
    start_new_game,
    get_game_state,
    update_location,
    add_to_inventory,
    log_story_event,
    update_stats,
    change_time,
    search_crafting_recipe,
    get_mob_info,
    explore_biome,
    find_structure,
)

logger = logging.getLogger("game-master")
load_dotenv(".env.local")


class GameMaster(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
You are a Minecraft Game Master running an immersive survival adventure.
Tone: adventurous, blocky, creative, survival-focused.

Minecraft World Rules:
- Describe the blocky world vividly (biomes, mobs, blocks, structures)
- Mention specific Minecraft elements: crafting, mining, building, farming, combat
- Track day/night cycle (zombies/skeletons spawn at night!)
- Include Minecraft mobs: Creepers, Zombies, Skeletons, Spiders, Endermen, Villagers, Animals
- Reference Minecraft mechanics: hunger, health (hearts), crafting recipes, enchanting, brewing
- Describe blocks and items accurately (oak wood, cobblestone, iron ore, diamonds, etc.)
- End every response with: "What do you do next?"

Use tools when:
- Player moves to new location (cave, village, nether, etc.) → update_location
- Player finds/crafts items → add_to_inventory
- Time passes → change_time (Morning/Afternoon/Evening/Night)
- Player takes damage or eats → update_stats
- Important events happen → log_story_event
- Player asks about crafting → search_crafting_recipe
- Player encounters a mob → get_mob_info
- Player explores new area → explore_biome
- Player finds a structure → find_structure

Never break character. Make it feel like a real Minecraft adventure!
""",
            tools=[
                start_new_game,
                get_game_state,
                update_location,
                add_to_inventory,
                log_story_event,
                update_stats,
                change_time,
                search_crafting_recipe,
                get_mob_info,
                explore_biome,
                find_structure,
            ],
        )


async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Narration",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2)
        ),
        vad=None,
        turn_detection=None,
        preemptive_generation=True
    )

    await session.start(
        agent=GameMaster(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        )
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
