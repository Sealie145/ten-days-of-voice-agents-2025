"""
Day 8 - Game Master Tools
Tools for managing game state, inventory, and story progression
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from livekit.agents import function_tool, RunContext
from dataclasses import dataclass, field

# Game state storage
GAME_STATE_FILE = "game_state.json"

# Minecraft reference data paths
SHARED_DATA_DIR = Path(__file__).parent.parent.parent / "shared-data"
ITEMS_FILE = SHARED_DATA_DIR / "minecraft_items.json"
MOBS_FILE = SHARED_DATA_DIR / "minecraft_mobs.json"
BIOMES_FILE = SHARED_DATA_DIR / "minecraft_biomes.json"
STRUCTURES_FILE = SHARED_DATA_DIR / "minecraft_structures.json"


def load_minecraft_data(file_path: Path) -> dict:
    """Load Minecraft reference data from JSON file"""
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    return {}


@dataclass
class GameState:
    """Tracks the current game state"""
    player_name: str = "Steve"
    current_location: str = "Forest Biome - Spawn Point"
    inventory: list[str] = field(default_factory=list)
    story_log: list[str] = field(default_factory=list)
    health: int = 20
    hunger: int = 20
    time_of_day: str = "Morning"
    started_at: str = ""


def get_state_path() -> Path:
    """Get the path to the game state file"""
    return Path(__file__).parent / GAME_STATE_FILE


def load_game_state() -> GameState:
    """Load game state from file or create new"""
    path = get_state_path()
    if path.exists():
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                state = GameState(**data)
                return state
        except Exception:
            pass
    return GameState()


def save_game_state(state: GameState):
    """Save game state to file"""
    path = get_state_path()
    with open(path, 'w') as f:
        json.dump(state.__dict__, f, indent=2)


@function_tool
async def start_new_game(
    ctx: RunContext,
    player_name: Annotated[str, Field(description="Player's name")] = "Steve"
) -> str:
    """Start a new game session"""
    state = GameState(
        player_name=player_name,
        current_location="Forest Biome - Spawn Point",
        inventory=["Wooden Pickaxe", "Torch x3"],
        story_log=[f"Game started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
        health=20,
        hunger=20,
        time_of_day="Morning",
        started_at=datetime.now().isoformat()
    )
    save_game_state(state)
    
    return f"""New game started for {player_name}!
Location: Forest Biome - Spawn Point
Health: 20/20
Hunger: 20/20
Time: Morning
Starting Items: Wooden Pickaxe, Torch x3

You spawn in a lush forest biome. Tall oak and birch trees surround you, their leaves rustling in the breeze.
The sun is rising, casting golden light through the canopy. You can hear the peaceful sounds of chickens and cows nearby.
In the distance, you spot a small hill with exposed stone and what looks like a cave entrance.

You have a wooden pickaxe and 3 torches to start your adventure.

What do you do next?"""


@function_tool
async def get_game_state(ctx: RunContext) -> str:
    """Get current game state"""
    state = load_game_state()
    
    inventory_str = ", ".join(state.inventory) if state.inventory else "Empty"
    
    return f"""Current Status:
Player: {state.player_name}
Location: {state.current_location}
Health: {state.health}/20 
Hunger: {state.hunger}/20 
Time: {state.time_of_day}
Inventory: {inventory_str}
Adventures Logged: {len(state.story_log)}"""


@function_tool
async def update_location(
    ctx: RunContext,
    new_location: Annotated[str, Field(description="New location name")]
) -> str:
    """Update player's current location"""
    state = load_game_state()
    old_location = state.current_location
    state.current_location = new_location
    state.story_log.append(f"Moved from {old_location} to {new_location}")
    save_game_state(state)
    
    return f"Location updated: {old_location} → {new_location}"


@function_tool
async def add_to_inventory(
    ctx: RunContext,
    item: Annotated[str, Field(description="Item to add to inventory")]
) -> str:
    """Add an item to player's inventory"""
    state = load_game_state()
    state.inventory.append(item)
    state.story_log.append(f"Acquired: {item}")
    save_game_state(state)
    
    return f"Added '{item}' to inventory. Current items: {', '.join(state.inventory)}"


@function_tool
async def log_story_event(
    ctx: RunContext,
    event: Annotated[str, Field(description="Story event to log")]
) -> str:
    """Log a significant story event"""
    state = load_game_state()
    timestamp = datetime.now().strftime('%H:%M:%S')
    state.story_log.append(f"[{timestamp}] {event}")
    save_game_state(state)
    
    return f"Event logged: {event}"


@function_tool
async def change_time(
    ctx: RunContext,
    new_time: Annotated[str, Field(description="New time of day: Morning, Afternoon, Evening, Night")]
) -> str:
    """Change the time of day in the game"""
    state = load_game_state()
    state.time_of_day = new_time
    save_game_state(state)
    
    time_emoji = {"Morning": "☀️", "Afternoon": "🌤️", "Evening": "🌅", "Night": "🌙"}.get(new_time, "⏰")
    warning = ""
    if new_time == "Night":
        warning = " ⚠️ Hostile mobs will spawn!"
    return f"Time changed to {new_time} {time_emoji}{warning}"


@function_tool
async def search_crafting_recipe(
    ctx: RunContext,
    item_name: Annotated[str, Field(description="Item to search for (e.g., 'Iron Pickaxe', 'Bread')")]
) -> str:
    """Search for crafting recipes and item information"""
    items_data = load_minecraft_data(ITEMS_FILE)
    
    # Search in all categories
    for category in ["tools", "building_blocks", "food", "resources", "utility"]:
        if category in items_data:
            for item in items_data[category]:
                if item_name.lower() in item["name"].lower():
                    result = f"📦 {item['name']}\n"
                    if "materials" in item:
                        result += f"Materials: {', '.join(item['materials'])}\n"
                    if "source" in item:
                        result += f"Source: {item['source']}\n"
                    if "durability" in item:
                        result += f"Durability: {item['durability']}\n"
                    if "damage" in item:
                        result += f"Damage: {item['damage']}\n"
                    if "hunger" in item:
                        result += f"Restores: {item['hunger']} hunger\n"
                    if "special" in item:
                        result += f"Special: {item['special']}\n"
                    return result
    
    return f"No crafting recipe found for '{item_name}'. Try: Pickaxe, Sword, Bread, Torch, etc."


@function_tool
async def get_mob_info(
    ctx: RunContext,
    mob_name: Annotated[str, Field(description="Mob to get info about (e.g., 'Creeper', 'Zombie', 'Cow')")]
) -> str:
    """Get information about a Minecraft mob"""
    mobs_data = load_minecraft_data(MOBS_FILE)
    
    # Search in all mob categories
    for category in ["passive_mobs", "neutral_mobs", "hostile_mobs", "boss_mobs"]:
        if category in mobs_data:
            for mob in mobs_data[category]:
                if mob_name.lower() in mob["name"].lower():
                    result = f"🎮 {mob['name']}\n"
                    result += f"Health: {mob['health']} ❤️\n"
                    if "damage" in mob:
                        result += f"Damage: {mob['damage']}\n"
                    result += f"Behavior: {mob['behavior']}\n"
                    result += f"Drops: {', '.join(mob['drops'])}\n"
                    if "special" in mob:
                        result += f"⚠️ Special: {mob['special']}\n"
                    return result
    
    return f"No information found for mob '{mob_name}'"


@function_tool
async def explore_biome(
    ctx: RunContext,
    biome_name: Annotated[str, Field(description="Biome to explore (e.g., 'Forest', 'Desert', 'Cave')")]
) -> str:
    """Get information about a biome"""
    biomes_data = load_minecraft_data(BIOMES_FILE)
    
    if "biomes" in biomes_data:
        for biome in biomes_data["biomes"]:
            if biome_name.lower() in biome["name"].lower():
                result = f"🌍 {biome['name']}\n"
                result += f"{biome['description']}\n\n"
                result += f"Animals: {', '.join(biome['common_mobs'])}\n"
                result += f"Hostiles: {', '.join(biome['hostile_mobs'])}\n"
                result += f"Resources: {', '.join(biome['resources'])}\n"
                if "structures" in biome:
                    result += f"Structures: {', '.join(biome['structures'])}\n"
                if "special" in biome:
                    result += f"⭐ {biome['special']}\n"
                return result
    
    return f"No information found for biome '{biome_name}'"


@function_tool
async def find_structure(
    ctx: RunContext,
    structure_name: Annotated[str, Field(description="Structure to find (e.g., 'Village', 'Desert Temple', 'Cave')")]
) -> str:
    """Get information about Minecraft structures"""
    structures_data = load_minecraft_data(STRUCTURES_FILE)
    
    # Search in all structure categories
    for category in ["overworld_structures", "nether_structures", "end_structures"]:
        if category in structures_data:
            for structure in structures_data[category]:
                if structure_name.lower() in structure["name"].lower():
                    result = f"🏛️ {structure['name']}\n"
                    result += f"{structure['description']}\n\n"
                    if "biomes" in structure:
                        result += f"Found in: {', '.join(structure['biomes'])}\n"
                    result += f"Features: {', '.join(structure['features'])}\n"
                    result += f"Loot: {', '.join(structure['loot'])}\n"
                    if "mobs" in structure:
                        result += f"Mobs: {', '.join(structure['mobs'])}\n"
                    if "danger" in structure:
                        result += f"⚠️ Danger: {structure['danger']}\n"
                    if "special" in structure:
                        result += f"⭐ Special: {structure['special']}\n"
                    return result
    
    return f"No information found for structure '{structure_name}'"


@function_tool
async def update_stats(
    ctx: RunContext,
    health_change: Annotated[Optional[int], Field(description="Health change (+/-)")] = None,
    hunger_change: Annotated[Optional[int], Field(description="Hunger change (+/-)")] = None
) -> str:
    """Update player health and hunger levels"""
    state = load_game_state()
    
    if health_change:
        state.health = max(0, min(20, state.health + health_change))
    if hunger_change:
        state.hunger = max(0, min(20, state.hunger + hunger_change))
    
    save_game_state(state)
    
    return f"Stats updated - Health: {state.health}/20 ❤️, Hunger: {state.hunger}/20 🍖"
