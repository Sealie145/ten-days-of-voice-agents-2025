"""Lead capture state management for SDR agent."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class LeadCapture:
    """Tracks lead information collected during the conversation."""

    REQUIRED_FIELDS = ["name", "company", "email", "role", "use_case", "team_size", "timeline"]

    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    use_case: Optional[str] = None
    team_size: Optional[str] = None
    timeline: Optional[str] = None
    budget: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def update_field(self, field_name: str, value: str) -> None:
        """Update a lead field with validation."""
        if not hasattr(self, field_name):
            raise AttributeError(f"Invalid field: {field_name}")
        setattr(self, field_name, value)

    def add_note(self, note: str) -> None:
        """Add a qualification note."""
        self.notes.append(note)

    def missing_fields(self) -> List[str]:
        """Return list of required fields that are still empty."""
        return [field for field in self.REQUIRED_FIELDS if not getattr(self, field)]

    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return len(self.missing_fields()) == 0

    def to_dict(self) -> Dict:
        """Convert lead to dictionary format."""
        return {
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "role": self.role,
            "use_case": self.use_case,
            "team_size": self.team_size,
            "timeline": self.timeline,
            "budget": self.budget,
            "notes": self.notes,
        }

    def summary_pairs(self) -> Dict[str, str]:
        """Return key-value pairs for summary."""
        return {
            "name": self.name or "N/A",
            "company": self.company or "N/A",
            "email": self.email or "N/A",
            "role": self.role or "N/A",
            "use_case": self.use_case or "N/A",
            "team_size": self.team_size or "N/A",
            "timeline": self.timeline or "N/A",
        }
