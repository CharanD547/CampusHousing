"""Version-one integration inputs. OpenAPI is the generated contract source."""
from datetime import date, time
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal['walk', 'bike', 'transit', 'drive']
Weekday = Literal['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AccountInput(Model):
    username: str = Field(min_length=3,max_length=60,pattern=r'^[A-Za-z0-9_-]+$')
    password: str = Field(min_length=12,max_length=128)


class Preferences(Model):
    monthly_budget_per_person: float = Field(gt=0, le=20000, allow_inf_nan=False)
    household_size: int = Field(ge=1, le=8)
    private_bedroom_required: bool = True
    requested_bedrooms: int | None = Field(default=None, ge=1, le=8)
    individual_lease_required: bool = False
    travel_modes: list[Mode] = Field(min_length=1, max_length=4)
    max_commute_minutes: int = Field(default=30, ge=1, le=240)
    arrival_buffer_minutes: int = Field(default=10, ge=0, le=120)
    move_in_date: date | None = None
    move_out_date: date | None = None
    priorities: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode='after')
    def consistent(self):
        if len(set(self.travel_modes)) != len(self.travel_modes):
            raise ValueError('Travel modes must be distinct.')
        if bool(self.move_in_date) != bool(self.move_out_date):
            raise ValueError('Supply both housing dates or neither.')
        if self.move_in_date and self.move_out_date <= self.move_in_date:
            raise ValueError('Move-out must follow move-in.')
        if any(not p.strip() or len(p)>100 for p in self.priorities):
            raise ValueError('Priorities must be bounded nonempty text.')
        return self


class Commitment(Model):
    id: str = Field(min_length=1, max_length=80)
    building_id: str = Field(min_length=1, max_length=100)
    weekdays: list[Weekday] = Field(min_length=1, max_length=7)
    arrival_time_local: time
    arrival_buffer_minutes: int | None = Field(default=None, ge=0, le=120)
    is_example: bool = False

    @model_validator(mode='after')
    def distinct_days(self):
        if len(set(self.weekdays)) != len(self.weekdays) or self.arrival_time_local.tzinfo:
            raise ValueError('Use distinct weekdays and an unzoned local arrival time.')
        return self


class ComparisonInput(Model):
    campus_id: str = Field(min_length=1, max_length=80)
    revision: int = Field(ge=0)
    preferences: Preferences
    commitments: list[Commitment] = Field(default_factory=list, max_length=10)
    route_date: date
    routing_scope: Literal['single_date','representative_week'] = 'single_date'
    candidate_ids: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def distinct_ids(self):
        if len({c.id for c in self.commitments}) != len(self.commitments):
            raise ValueError('Commitment IDs must be unique.')
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError('Candidate IDs must be distinct.')
        return self


class ExplanationInput(Model):
    comparison_id: str = Field(min_length=1, max_length=80)
    revision: int = Field(ge=0)
    request_id: str = Field(min_length=1, max_length=80)


class ChecklistItem(Model):
    id: str
    candidate_id: str | None = None
    category: Literal['money', 'lease', 'roommates', 'commute', 'move_in']
    title: str
    details: str | None = None
    status: Literal['not_started', 'in_progress', 'done', 'not_applicable'] = 'not_started'
    notes: str = Field(default='', max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list)
    needs_confirmation: bool = True
    origin: Literal['generic', 'deterministic', 'gemma', 'user'] = 'deterministic'


class ChecklistInput(ExplanationInput):
    candidate_id: str = Field(min_length=1, max_length=100)
    previous_items: list[ChecklistItem] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def unique_items(self):
        if len({x.id for x in self.previous_items}) != len(self.previous_items):
            raise ValueError('Checklist item IDs must be unique.')
        return self


class Question(Model):
    id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=2000)
    answer: str = Field(default='', max_length=2000)


class CandidateNotes(Model):
    questions: list[Question] = Field(default_factory=list, max_length=50)
    note: str = Field(default='', max_length=2000)
    setAside: str = Field(default='', max_length=2000)


class WorkspaceInput(Model):
    revision: int = Field(ge=0)
    preferences: Preferences
    commitments: list[Commitment] = Field(default_factory=list, max_length=10)
    selected_candidate_ids: list[str] = Field(default_factory=list, max_length=3)
    checklist: list[ChecklistItem] = Field(default_factory=list, max_length=100)
    questions: list[str] = Field(default_factory=list, max_length=50)
    current_step: Literal[1, 2, 3, 4] = 1
    completed_steps: list[Literal[1, 2, 3, 4]] = Field(default_factory=list, max_length=4)
    input_revision: int = Field(default=0, ge=0)
    route_date: date | None = None
    routing_scope: Literal['single_date','representative_week'] = 'single_date'
    notes: dict[str, CandidateNotes] = Field(default_factory=dict, max_length=30)
    brief_ids: list[str] = Field(default_factory=list, max_length=100)
    guide_started: bool = False
    guide_candidate_ids: list[str] = Field(default_factory=list, max_length=3)


class BriefInput(ExplanationInput):
    selected_candidate_ids: list[str] = Field(min_length=1, max_length=3)
    checklist: list[ChecklistItem] = Field(default_factory=list, max_length=100)
    notes: dict[str, CandidateNotes] = Field(default_factory=dict, max_length=3)
    origin: Literal['shortlist', 'guide'] = 'shortlist'


class Price(Model):
    amount: str | None
    currency: Literal['USD']
    basis: Literal['per_person', 'whole_unit', 'unknown']
    frequency: Literal['calendar_month', 'installment', 'other']
    payment_count: int | None
    term: dict
    source_id: str
    last_reviewed_at: str


class Offer(Model):
    id: str
    layout: str
    bedrooms: int | None
    contract: str
    room: str
    price: Price
    fees: list[dict]
    unknown_costs: list[str]
    utility_matrix: dict[str, str] = Field(default_factory=dict)
    utility_source_id: str | None = None
    price_confidence_tier: str | None = None
    advertised_range: dict | None = None
    operator_questions: list[str] = Field(default_factory=list)
    source_conflicts: list[dict] = Field(default_factory=list)


class Candidate(Model):
    id: str
    type: Literal['property', 'offer', 'area']
    property_id: str
    property_name: str
    address: str | None
    coordinates: dict[str, float] | None
    guide_reference: dict | None = None
    lease_gaps: dict | None = None
    coordinate_basis: str
    data_status: str
    sources: list[dict]
    offer: Offer


class CatalogResponse(Model):
    campus_id: str
    candidates: list[Candidate]


class CommuteEstimate(Model):
    retention: Literal['transient'] | None = None
    candidate_id: str
    commitment_id: str
    destination_id: str | None = None
    mode: Mode
    minutes: float | None
    status: Literal['supported', 'unsupported', 'unavailable']
    route_date: date
    provider: str
    context: dict
    coverage_notes: list[str]
    evidence_ids: list[str]


class CandidateResult(Model):
    candidate_id: str
    property_id: str
    fit_state: Literal['documented_fit', 'conflict', 'insufficient_evidence']
    cost_breakdown: dict
    known_recurring_subtotal: str | None
    price_label: str
    unknown_costs: list[str]
    hard_conflicts: list[str]
    notes: list[str] = Field(default_factory=list)
    reason_codes: list[str]
    supported_commitments: int
    total_commitments: int
    limiting_commitment: str | None
    commute_estimates: list[CommuteEstimate]
    evidence_ids: list[str]
    source_date: str


class ComparisonResponse(Model):
    id: str
    input_revision: int
    revision: int
    status: Literal['partial', 'complete']
    created_at: str
    inputs: ComparisonInput
    catalog_fingerprint: str
    catalog_snapshot: list[Candidate]
    building_snapshot: list[dict]
    candidate_results: list[CandidateResult]
    ai_status: str
    missing_data: list[str]


class CandidateExplanation(Model):
    candidate_id: str
    summary: str = Field(min_length=1, max_length=2000)
    preference_relevance: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    limitations: list[str] = Field(min_length=1, max_length=20)
    next_questions: list[str] = Field(min_length=1, max_length=20)
    tool_result_refs: list[str] = Field(default_factory=list, max_length=20)


class AIExplanation(Model):
    input_revision: int
    model_id: str | None
    status: Literal['complete', 'ai_unavailable']
    candidate_explanations: list[CandidateExplanation]
    error: dict | None = None


class AssistantMessage(Model):
    role: Literal['user','assistant']
    content: str = Field(min_length=1,max_length=3000)


class AssistantInput(ExplanationInput):
    question: str = Field(min_length=1,max_length=2000)
    candidate_ids: list[str] = Field(default_factory=list,max_length=3)
    history: list[AssistantMessage] = Field(default_factory=list,max_length=8)


class AssistantAnswer(Model):
    answer: str = Field(min_length=1,max_length=6000)
    answer_kind: Literal['evidence','general','insufficient_evidence']
    evidence_ids: list[str] = Field(default_factory=list,max_length=20)
    candidate_ids: list[str] = Field(default_factory=list,max_length=3)
    limitations: list[str] = Field(min_length=1,max_length=10)
    next_questions: list[str] = Field(default_factory=list,max_length=10)


class AssistantResponse(Model):
    status: Literal['complete','ai_unavailable']
    input_revision: int
    provider: str
    model_id: str | None
    result: AssistantAnswer | None = None
    error: dict | None = None
    fallback: dict | None = None
