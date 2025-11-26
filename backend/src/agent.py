"""Day 5 Mobikwik SDR Agent – FAQ-driven lead capture."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    RunContext,
    ToolError,
    WorkerOptions,
    cli,
    function_tool,
    metrics,
    tokenize,
)
from livekit.plugins import silero, murf, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

try:
    from .lead_state import LeadCapture
except ImportError:
    from lead_state import LeadCapture

logger = logging.getLogger("agent")
load_dotenv(".env.local")


class MobikwikKnowledgeBase:
    """Lightweight FAQ search on top of a JSON payload."""

    def __init__(self, payload: Dict):
        self.payload = payload
        self.entries: List[Dict] = payload.get("entries", [])
        self.required_documents: List[str] = payload.get("required_documents", [])
        self.pricing: Dict[str, str] = payload.get("pricing", {})
        self.company: Dict[str, str] = payload.get("company", {})

    @classmethod
    def from_disk(cls) -> "MobikwikKnowledgeBase":
        env_path = os.getenv("DAY5_FAQ_PATH")
        default_path = Path(__file__).resolve().parents[2] / "shared-data" / "day5_mobikwik_faq.json"
        payload_path = Path(env_path).expanduser() if env_path else default_path
        if not payload_path.exists():
            raise FileNotFoundError(f"FAQ payload missing: {payload_path}")
        with open(payload_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return cls(payload)

    def _score_entry(self, query: str, entry: Dict) -> int:
        q = query.lower()
        score = 0
        keywords = entry.get("keywords", [])
        content = entry.get("content", "").lower()
        title = entry.get("title", "").lower()

        for keyword in keywords:
            if keyword in q:
                score += 2
        for token in q.split():
            if token and token in content:
                score += 1
        if title and title in q:
            score += 2
        if q in content:
            score += 3
        return score

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        if not query.strip():
            return []
        scored: List[Tuple[int, Dict]] = []
        for entry in self.entries:
            score = self._score_entry(query, entry)
            if score > 0:
                scored.append((score, entry))
        if not scored:
            return self.entries[:limit]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def answer(self, query: str) -> str:
        matches = self.search(query)
        if not matches:
            return (
                "I could not find that in the Mobikwik FAQ set I'm loaded with. "
                "Let me know if you can rephrase it or I can connect you to a teammate."
            )
        formatted = [f"{entry['title']}: {entry['content']}" for entry in matches]
        return " ".join(formatted)

    def pricing_summary(self) -> str:
        if not self.pricing:
            return "Standard MobiKwik pricing: 1.90% for wallet transactions, 2.90% for Amex. Zero setup and maintenance fees."
        base = self.pricing
        return (
            f"Wallet: {base.get('wallet')}, Amex: {base.get('amex')}. "
            f"Setup fee: {base.get('setup_fee')}, Maintenance: {base.get('maintenance')}. "
            f"Mobile recharge: {base.get('mobile_recharge')}. Enterprise: {base.get('enterprise')}"
        )

    def documents_summary(self) -> str:
        if not self.required_documents:
            return "PAN, GSTIN, bank account, and proof of business are typically required."
        docs = ", ".join(self.required_documents)
        return f"To go live you'll need: {docs}."


class LeadStorage:
    """Filesystem helper that keeps incremental and final lead JSON copies."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def snapshot(self, lead: LeadCapture, lead_id: str, *, final: bool = False, summary: Optional[str] = None) -> Path:
        payload = {
            "lead_id": lead_id,
            "timestamp": datetime.utcnow().isoformat(),
            "finalized": final,
            "summary": summary,
            **lead.to_dict(),
        }
        rolling_path = self.base_dir / f"{lead_id}.json"
        with open(rolling_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

        if final:
            stamped = self.base_dir / f"{lead_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(stamped, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            return stamped
        return rolling_path


@dataclass
class Userdata:
    lead: LeadCapture
    knowledge: MobikwikKnowledgeBase
    storage: LeadStorage
    lead_id: str
    final_path: Optional[Path] = None


class MobikwikSdrAgent(Agent):
    """Live SDR persona that leans on Mobikwik FAQ content."""

    def __init__(self, *, userdata: Userdata) -> None:
        instructions = f"""You are a warm, proactive Sales Development Representative for Mobikwik, India's leading digital financial services platform.
Key persona guidelines:
- Greet every caller with energy, mention Mobikwik briefly, and ask what brought them in plus what they are building.
- Keep the focus on discovering their payments / disbursals needs, asking one friendly question at a time.
- Collect these lead fields naturally: name, company, email, role, use case, team size, timeline (now / soon / later), and optional budget.
- After you capture name or company details, acknowledge them and explain how Mobikwik can help based on their use case.
- When prospects ask about products, pricing, activation, or documents ALWAYS call the answer_company_question tool with their question so responses stay grounded in the FAQ.
- Use get_lead_status whenever you need to see which fields are missing, then ask for the next gap.
- Update each field immediately using record_lead_field after the user gives an answer. Do not wait until the end.
- Take short qualification notes with add_lead_note if they mention urgency, channel mix, or decision-making power.
- The moment they indicate they are done (phrases like "that's all", "sounds good", "I'll wait for the email") call finalize_lead to produce a concise verbal recap before you say goodbye.
- The finalize_lead tool auto-generates a sentence that starts with "Lead summary:" followed by key=value pairs; always speak that result so the UI can display it and let them know an email recap is on the way.
- Never hallucinate features or pricing; if something is missing from the FAQ, say you'll have a teammate follow up.
- Keep replies crisp, professional, and friendly—think modern fintech SDR."""

        super().__init__(instructions=instructions)

    async def on_agent_speech_committed(self, ctx: RunContext[Userdata], message: str) -> None:  # pragma: no cover - logging
        logger.info("Agent: %s", message)

    async def on_user_speech_committed(self, ctx: RunContext[Userdata], message: str) -> None:  # pragma: no cover - logging
        logger.info("User: %s", message)

    @function_tool
    async def answer_company_question(self, ctx: RunContext[Userdata], question: str) -> str:
        """Grounded answer for any Mobikwik company/product/pricing/document question."""
        response = ctx.userdata.knowledge.answer(question)
        logger.info("Answered FAQ for query=%s", question)
        return response

    @function_tool
    async def record_lead_field(self, ctx: RunContext[Userdata], field_name: str, value: str) -> str:
        """Persist a lead field update. Valid fields: name, company, email, role, use_case, team_size, timeline, budget."""
        lead = ctx.userdata.lead
        try:
            lead.update_field(field_name, value)
        except AttributeError as exc:
            raise ToolError(str(exc)) from exc

        ctx.userdata.storage.snapshot(lead, ctx.userdata.lead_id, final=False)
        missing = lead.missing_fields()
        logger.info("Updated %s -> %s", field_name, value)

        if missing:
            return (
                f"Captured {field_name}. Still need: {', '.join(missing)}."
                " Ask a conversational follow-up to gather the next detail."
            )
        return "All required lead fields captured. Feel free to confirm next steps or ask about budget."

    @function_tool
    async def add_lead_note(self, ctx: RunContext[Userdata], note: str) -> str:
        """Store short qualification notes such as pain points, budget mentions, or persona clues."""
        ctx.userdata.lead.add_note(note)
        ctx.userdata.storage.snapshot(ctx.userdata.lead, ctx.userdata.lead_id, final=False)
        logger.info("Added lead note: %s", note)
        return "Saved that note for the CRM."

    @function_tool
    async def get_lead_status(self, ctx: RunContext[Userdata]) -> str:
        """Returns a summary of which lead fields are filled vs missing."""
        lead = ctx.userdata.lead
        filled = [f"{field}={getattr(lead, field)}" for field in lead.REQUIRED_FIELDS if getattr(lead, field)]
        missing = lead.missing_fields()
        return f"Filled: {', '.join(filled) if filled else 'none yet'}. Missing: {', '.join(missing) if missing else 'none'}."

    @function_tool
    async def summarize_pricing_basics(self, ctx: RunContext[Userdata]) -> str:
        """Quick reminder of Mobikwik's published pricing structure."""
        return ctx.userdata.knowledge.pricing_summary()

    @function_tool
    async def list_activation_documents(self, ctx: RunContext[Userdata]) -> str:
        """List the KYC documents required to activate a live Mobikwik account."""
        return ctx.userdata.knowledge.documents_summary()

    @function_tool
    async def finalize_lead(self, ctx: RunContext[Userdata]) -> str:
        """Finalize the lead, store it to disk, and return a short summary sentence."""
        lead = ctx.userdata.lead
        if not lead.is_complete():
            raise ToolError(f"Still missing: {', '.join(lead.missing_fields())}. Gather these before closing.")

        summary_pairs = lead.summary_pairs()
        summary_sentence = "Lead summary: " + "; ".join(f"{k}={v}" for k, v in summary_pairs.items()) + "."

        final_path = ctx.userdata.storage.snapshot(
            lead,
            ctx.userdata.lead_id,
            final=True,
            summary=summary_sentence,
        )
        ctx.userdata.final_path = final_path
        logger.info("Finalized lead saved to %s", final_path)
        return summary_sentence + " Thanks for the chat—watch your inbox for a Mobikwik follow-up."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    proc.userdata["mobikwik_kb"] = MobikwikKnowledgeBase.from_disk()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    knowledge = ctx.proc.userdata.get("mobikwik_kb", MobikwikKnowledgeBase.from_disk())
    storage = LeadStorage(Path("leads/day5"))
    # Use room name or generate a unique ID - room.sid is a coroutine and can't be used directly
    lead_id = ctx.room.name or datetime.utcnow().strftime("lead_%Y%m%d_%H%M%S")
    userdata = Userdata(
        lead=LeadCapture(),
        knowledge=knowledge,
        storage=storage,
        lead_id=lead_id,
    )
    storage.snapshot(userdata.lead, lead_id, final=False)

    session = AgentSession[Userdata](
        userdata=userdata,
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Conversation",
            tokenizer=tokenize.basic.WordTokenizer(),
            text_pacing=False,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    @session.on("user_speech_committed")
    def _on_user_speech(ev):
        logger.info("User said: %s", ev.text)

    @session.on("agent_speech_committed")
    def _on_agent_speech(ev):
        logger.info("Agent said: %s", ev.text)

    @session.on("error")
    def _on_error(ev):
        logger.error("Session error: %s", ev)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info("Usage: %s", summary)

    ctx.add_shutdown_callback(log_usage)

    agent = MobikwikSdrAgent(userdata=userdata)

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    logger.info("Day 5 Mobikwik SDR agent connected and listening.")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

