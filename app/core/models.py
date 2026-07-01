from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator, computed_field, model_validator
from enum import Enum

CATEGORY_MAX_SCORES = {
    "parseability_formatting": 30,
    "section_structure": 25,
    "content_quality": 25,
    "keyword_optimization": 20,
}


class ModelProvider(Enum):
    """Enum for supported model providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    GROQ = "groq"


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to the LLM provider."""
        ...


import time
import random
import re
from typing import Callable, Type

def with_retry(func: Callable, exceptions: Tuple[Type[Exception], ...], provider_name: str) -> Any:
    MAX_RETRIES = 5
    BASE_DELAY = 10.0
    MAX_DELAY = 120.0
    
    for attempt in range(MAX_RETRIES):
        try:
            return func()
        except exceptions as e:
            if attempt == MAX_RETRIES - 1:
                raise
                
            match = re.search(r"retry[_ ]in\s+([\d.]+)s", str(e), re.IGNORECASE)
            api_hint = float(match.group(1)) if match else None

            exp_delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
            delay = api_hint if (api_hint and api_hint < exp_delay) else exp_delay
            sleep_time = round(delay * random.uniform(0.8, 1.2), 2)

            print(
                f"[{provider_name}] Rate limit or server error hit "
                f"(attempt {attempt + 1}/{MAX_RETRIES}). "
                f"Retrying in {sleep_time}s..."
            )
            time.sleep(sleep_time)


class Location(BaseModel):
    """Location information for JSON Resume format."""

    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None


class Profile(BaseModel):
    """Social profile information for JSON Resume format."""

    network: Optional[str] = None
    username: Optional[str] = None
    url: str


class Basics(BaseModel):
    """Basic information for JSON Resume format."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: Optional[List[Profile]] = None


class Work(BaseModel):
    """Work experience for JSON Resume format."""

    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class Volunteer(BaseModel):
    """Volunteer experience for JSON Resume format."""

    organization: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class Education(BaseModel):
    """Education information for JSON Resume format."""

    institution: Optional[str] = None
    url: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: Optional[List[str]] = None


class Award(BaseModel):
    """Award information for JSON Resume format."""

    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class Certificate(BaseModel):
    """Certificate information for JSON Resume format."""

    name: Optional[str] = None
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class Publication(BaseModel):
    """Publication information for JSON Resume format."""

    name: Optional[str] = None
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Skill(BaseModel):
    """Skill information for JSON Resume format."""

    name: Optional[str] = None
    level: Optional[str] = None
    keywords: Optional[List[str]] = None


class Language(BaseModel):
    """Language information for JSON Resume format."""

    language: Optional[str] = None
    fluency: Optional[str] = None


class Interest(BaseModel):
    """Interest information for JSON Resume format."""

    name: Optional[str] = None
    keywords: Optional[List[str]] = None


class Reference(BaseModel):
    """Reference information for JSON Resume format."""

    name: Optional[str] = None
    reference: Optional[str] = None


class Project(BaseModel):
    """Project information for JSON Resume format."""

    name: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None
    url: Optional[str] = None
    technologies: Optional[List[str]] = None
    skills: Optional[List[str]] = None


class BasicsSection(BaseModel):
    """Basics section containing basic information."""

    basics: Optional[Basics] = None


class WorkSection(BaseModel):
    """Work section containing a list of work experiences."""

    work: Optional[List[Work]] = None


class EducationSection(BaseModel):
    """Education section containing a list of education entries."""

    education: Optional[List[Education]] = None


class SkillsSection(BaseModel):
    """Skills section containing a list of skill categories."""

    skills: Optional[List[Skill]] = None


class ProjectsSection(BaseModel):
    """Projects section containing a list of projects."""

    projects: Optional[List[Project]] = None


class AwardsSection(BaseModel):
    """Awards section containing a list of awards."""

    awards: Optional[List[Award]] = None


class JSONResume(BaseModel):
    """Complete JSON Resume format model."""

    basics: Optional[Basics] = None
    work: Optional[List[Work]] = None
    volunteer: Optional[List[Volunteer]] = None
    education: Optional[List[Education]] = None
    awards: Optional[List[Award]] = None
    certificates: Optional[List[Certificate]] = None
    publications: Optional[List[Publication]] = None
    skills: Optional[List[Skill]] = None
    languages: Optional[List[Language]] = None
    interests: Optional[List[Interest]] = None
    references: Optional[List[Reference]] = None
    projects: Optional[List[Project]] = None


class CategoryScore(BaseModel):
    score: float = Field(ge=0, description="Score achieved in this category")
    max: int = Field(gt=0, description="Maximum possible score")
    evidence: str = Field(min_length=1, description="Evidence supporting the score")


class Scores(BaseModel):
    parseability_formatting: CategoryScore
    section_structure: CategoryScore
    content_quality: CategoryScore
    keyword_optimization: CategoryScore

    @model_validator(mode='after')
    def enforce_category_maxes(self) -> 'Scores':
        self.parseability_formatting.max = CATEGORY_MAX_SCORES["parseability_formatting"]
        self.section_structure.max = CATEGORY_MAX_SCORES["section_structure"]
        self.content_quality.max = CATEGORY_MAX_SCORES["content_quality"]
        self.keyword_optimization.max = CATEGORY_MAX_SCORES["keyword_optimization"]
        return self

MIN_FINAL_SCORE = 0.0
MAX_DEDUCTIONS = 50.0

class Deductions(BaseModel):
    total: float = Field(
        ge=0,
        le=MAX_DEDUCTIONS,
        description="Total deduction points (stored as positive, applied as negative)",
    )
    reasons: str = Field(description="Reasons for deductions")

class ATSFormattingReport(BaseModel):
    has_multi_column_layout: bool = False
    has_tables: bool = False
    has_text_in_images: bool = False
    is_scanned_pdf: bool = False
    missing_sections: List[str] = Field(default_factory=list)
    contact_info_in_header_footer: bool = False
    font_count: int = 0
    page_count: int = 0
    word_count: int = 0

class EvaluationData(BaseModel):
    scores: Scores
    deductions: Deductions
    ats_report: Optional[ATSFormattingReport] = None
    key_strengths: List[str] = Field(min_length=1, max_length=5)
    areas_for_improvement: List[str] = Field(min_length=1, max_length=3)

    @computed_field
    @property
    def total_score(self) -> float:
        base_score = sum(
            min(cat.score, cat.max)
            for cat in [
                self.scores.parseability_formatting,
                self.scores.section_structure,
                self.scores.content_quality,
                self.scores.keyword_optimization,
            ]
        )
        total = base_score - self.deductions.total
        max_possible = self.total_max
        return min(max(total, MIN_FINAL_SCORE), max_possible)

    @computed_field
    @property
    def total_max(self) -> int:
        return sum(
            cat.max
            for cat in [
                self.scores.parseability_formatting,
                self.scores.section_structure,
                self.scores.content_quality,
                self.scores.keyword_optimization,
            ]
        )


class GitHubProfile(BaseModel):
    """Pydantic model for GitHub profile data."""

    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    public_repos: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    avatar_url: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    hireable: Optional[bool] = None


class OllamaProvider:
    """Ollama LLM provider implementation."""

    def __init__(self):
        import ollama

        self.client = ollama

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama."""

        ollama_options = options.copy() if options else {}

        # remove steam from ollama options
        ollama_options.pop("stream", None)

        # Add num_ctx 32K context window to options
        ollama_options["num_ctx"] = 32768

        # convert to chat params
        chat_params = {
            "model": model,
            "messages": messages,
            "options": ollama_options,
        }

        # add it to top level
        if "stream" in kwargs:
            chat_params["stream"] = kwargs["stream"]

        if "format" in kwargs:
            chat_params["format"] = kwargs["format"]

        return self.client.chat(**chat_params)


class GeminiProvider:
    """Google Gemini API provider implementation."""

    def __init__(self, api_key: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.client = genai

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Google Gemini API."""
        from google.api_core.exceptions import ResourceExhausted

        # Map options to Gemini parameters
        generation_config = {}
        if options:
            if "temperature" in options:
                generation_config["temperature"] = options["temperature"]
            if "top_p" in options:
                generation_config["top_p"] = options["top_p"]
                
        # Support JSON output if requested
        if "format" in kwargs and kwargs["format"]:
            generation_config["response_mime_type"] = "application/json"
            if isinstance(kwargs["format"], dict):
                generation_config["response_schema"] = kwargs["format"]

        # Create a Gemini model
        gemini_model = self.client.GenerativeModel(
            model_name=model, generation_config=generation_config
        )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})

        def _do_gemini_chat():
            response = gemini_model.generate_content(gemini_messages)
            return {"message": {"role": "assistant", "content": response.text}}
            
        return with_retry(_do_gemini_chat, (ResourceExhausted,), "GeminiProvider")


class GroqProvider:
    """Groq API provider implementation."""

    def __init__(self, api_key: str):
        import groq
        self.client = groq.Groq(api_key=api_key)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Groq."""
        
        chat_params = {
            "model": model,
            "messages": messages,
        }

        if options:
            if "temperature" in options:
                chat_params["temperature"] = options["temperature"]
            if "top_p" in options:
                chat_params["top_p"] = options["top_p"]

        # Support JSON output if requested
        if "format" in kwargs and kwargs["format"]:
            chat_params["response_format"] = {"type": "json_object"}

        def _do_groq_chat():
            response = self.client.chat.completions.create(**chat_params)
            # Convert Groq response to Ollama-like format for compatibility
            return {"message": {"role": "assistant", "content": response.choices[0].message.content}}

        import groq
        return with_retry(
            _do_groq_chat, 
            (groq.RateLimitError, groq.APIStatusError, groq.InternalServerError), 
            "GroqProvider"
        )
