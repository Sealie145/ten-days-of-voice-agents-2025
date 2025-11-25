import logging
import json
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    tokenize,
    function_tool,
    RunContext
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Load tutor content
CONTENT_FILE = Path(__file__).parent.parent.parent / "shared-data" / "day4_tutor_content.json"
with open(CONTENT_FILE, "r") as f:
    TUTOR_CONTENT = json.load(f)

# Create a lookup dictionary
CONCEPTS = {concept["id"]: concept for concept in TUTOR_CONTENT}


class TeachTheTutorAgent(Agent):
    def __init__(self, room=None) -> None:
        # Get available concepts
        concept_list = ", ".join([c["title"] for c in TUTOR_CONTENT])
        
        super().__init__(
            instructions=f"""You are an active recall learning coach. Your job is to help users learn by teaching concepts, quizzing them, and having them teach back to you.

AVAILABLE CONCEPTS:
{concept_list}

THREE LEARNING MODES:
1. LEARN mode - You explain concepts clearly and simply
2. QUIZ mode - You ask the user questions about concepts
3. TEACH_BACK mode - You ask the user to explain concepts back to you, then give feedback

CONVERSATION FLOW:
1. Greet the user warmly
2. Ask what they want to learn about (from available concepts)
3. Ask which mode they prefer (learn, quiz, or teach_back)
4. Execute that mode using the appropriate tool
5. User can switch modes anytime by asking

IMPORTANT:
- Be encouraging and supportive
- Keep explanations clear and concise
- In teach_back mode, give constructive feedback
- Users can switch concepts or modes anytime
- Use the tools to access content and track progress

When user chooses a mode, immediately call the appropriate tool:
- learn mode → use explain_concept tool
- quiz mode → use quiz_concept tool  
- teach_back mode → use teach_back_concept tool""",
        )
        self._room = room
        self._current_concept = None
        self._current_mode = None

    def _find_concept(self, concept_input: str) -> str:
        """Find concept ID from user input (case-insensitive, flexible matching)."""
        concept_lower = concept_input.lower().strip()
        
        # Direct match
        if concept_lower in CONCEPTS:
            return concept_lower
        
        # Try to match by title
        for cid, concept in CONCEPTS.items():
            if concept['title'].lower() == concept_lower:
                return cid
            # Partial match
            if concept_lower in concept['title'].lower() or concept['title'].lower() in concept_lower:
                return cid
        
        return None

    @function_tool
    async def explain_concept(
        self,
        context: RunContext,
        concept_id: str
    ):
        """Explain a concept to the user in LEARN mode.
        
        Args:
            concept_id: The concept to explain (e.g., "variables", "loops", "arrays")
        """
        logger.info(f"Explaining concept: {concept_id}")
        
        # Find the actual concept ID
        actual_id = self._find_concept(concept_id)
        
        if not actual_id:
            available = ", ".join([c['title'] for c in TUTOR_CONTENT])
            return f"I don't have that concept. Available topics are: {available}. Which one would you like to learn about?"
        
        concept = CONCEPTS[actual_id]
        self._current_concept = actual_id
        self._current_mode = "learn"
        
        explanation = f"Let me explain {concept['title']}.\n\n{concept['summary']}\n\nDoes this make sense? Would you like me to quiz you on this, or would you like to try teaching it back to me?"
        
        return explanation

    @function_tool
    async def quiz_concept(
        self,
        context: RunContext,
        concept_id: str
    ):
        """Quiz the user on a concept in QUIZ mode.
        
        Args:
            concept_id: The concept to quiz on
        """
        logger.info(f"Quizzing on concept: {concept_id}")
        
        # Find the actual concept ID
        actual_id = self._find_concept(concept_id)
        
        if not actual_id:
            available = ", ".join([c['title'] for c in TUTOR_CONTENT])
            return f"I don't have that concept. Available topics are: {available}."
        
        concept = CONCEPTS[actual_id]
        self._current_concept = actual_id
        self._current_mode = "quiz"
        
        question = f"Great! Let's test your knowledge of {concept['title']}.\n\n{concept['sample_question']}"
        
        return question

    @function_tool
    async def teach_back_concept(
        self,
        context: RunContext,
        concept_id: str
    ):
        """Ask the user to teach the concept back in TEACH_BACK mode.
        
        Args:
            concept_id: The concept for teach-back
        """
        logger.info(f"Teach-back for concept: {concept_id}")
        
        # Find the actual concept ID
        actual_id = self._find_concept(concept_id)
        
        if not actual_id:
            available = ", ".join([c['title'] for c in TUTOR_CONTENT])
            return f"I don't have that concept. Available topics are: {available}."
        
        concept = CONCEPTS[actual_id]
        self._current_concept = actual_id
        self._current_mode = "teach_back"
        
        prompt = f"Perfect! Now it is your turn to be the teacher. Explain {concept['title']} to me as if I am learning it for the first time. Take your time and explain it in your own words."
        
        return prompt

    @function_tool
    async def give_feedback(
        self,
        context: RunContext,
        user_explanation: str,
        concept_id: str
    ):
        """Give feedback on the user's teach-back explanation.
        
        Args:
            user_explanation: What the user explained
            concept_id: The concept they were explaining
        """
        logger.info(f"Giving feedback on {concept_id}")
        
        if concept_id not in CONCEPTS:
            return "I'm not sure which concept you're explaining."
        
        concept = CONCEPTS[concept_id]
        
        # Simple feedback based on key terms
        summary_lower = concept['summary'].lower()
        explanation_lower = user_explanation.lower()
        
        # Check for key concepts
        key_terms = []
        if concept_id == "variables":
            key_terms = ["store", "value", "name", "reuse"]
        elif concept_id == "loops":
            key_terms = ["repeat", "for", "while", "condition"]
        elif concept_id == "functions":
            key_terms = ["reusable", "task", "call", "parameters"]
        elif concept_id == "conditionals":
            key_terms = ["if", "condition", "true", "false", "decision"]
        elif concept_id == "arrays":
            key_terms = ["collection", "multiple", "list", "index"]
        
        mentioned_terms = [term for term in key_terms if term in explanation_lower]
        coverage = len(mentioned_terms) / len(key_terms) if key_terms else 0.5
        
        if coverage >= 0.75:
            feedback = f"Excellent explanation! You covered the key points about {concept['title']}. "
            feedback += f"You mentioned {', '.join(mentioned_terms)} which are all important concepts. "
            feedback += "You clearly understand this topic!"
        elif coverage >= 0.5:
            feedback = f"Good job! You got the main idea of {concept['title']}. "
            feedback += f"You mentioned {', '.join(mentioned_terms)}. "
            missing = [term for term in key_terms if term not in mentioned_terms]
            if missing:
                feedback += f"To make it even better, you could also mention: {', '.join(missing[:2])}."
        else:
            feedback = f"Thanks for trying! You're on the right track with {concept['title']}. "
            feedback += f"Let me give you a hint: {concept['title']} is about {concept['summary'][:100]}... "
            feedback += "Would you like me to explain it again?"
        
        return feedback


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Determine voice based on mode (will be set dynamically)
    # Default to Matthew for initial greeting
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=1),
            text_pacing=True
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=TeachTheTutorAgent(room=ctx.room),
        room=ctx.room,
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
