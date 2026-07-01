from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from app.core.models import JSONResume, EvaluationData, CATEGORY_MAX_SCORES, ATSFormattingReport
from app.utils.llm_utils import initialize_llm_provider, extract_json_from_response
import logging
import json
import re
from app.core.prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
)
from app.prompts.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class ResumeEvaluator:
    def __init__(self, model_name: str = DEFAULT_MODEL, model_params: dict = None):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def _load_evaluation_prompt(self, resume_text: str, ats_report: Optional[ATSFormattingReport] = None) -> str:
        formatting_flags = ats_report.model_dump() if ats_report else None
        criteria_template = self.template_manager.render_template(
            "resume_evaluation_criteria", text_content=resume_text, category_maxes=CATEGORY_MAX_SCORES, formatting_flags=formatting_flags
        )
        if criteria_template is None:
            raise ValueError("Failed to load resume evaluation criteria template")
        return criteria_template

    def evaluate_resume(self, resume_text: str, ats_report: Optional[ATSFormattingReport] = None) -> EvaluationData:
        self._last_resume_text = resume_text
        full_prompt = self._load_evaluation_prompt(resume_text, ats_report)
        # logger.info(f"🔤 Evaluation prompt being sent: {full_prompt}")
        try:
            system_message = self.template_manager.render_template(
                "resume_evaluation_system_message", category_maxes=CATEGORY_MAX_SCORES
            )
            if system_message is None:
                raise ValueError(
                    "Failed to load resume evaluation system message template"
                )

            # Prepare chat parameters
            chat_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": full_prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": self.model_params.get("temperature", 0.5),
                    "top_p": self.model_params.get("top_p", 0.9),
                },
            }

            # Add format parameter for structured output
            kwargs = {"format": EvaluationData.model_json_schema()}
            # Use the appropriate provider to make the API call
            response = self.provider.chat(**chat_params, **kwargs)

            response_text = response["message"]["content"]
            response_text = extract_json_from_response(response_text)
            logger.debug(f"🔤 Prompt response: {response_text}")

            evaluation_dict = json.loads(response_text)
            evaluation_data = EvaluationData(**evaluation_dict)

            if evaluation_data.deductions.total > (evaluation_data.total_max * 0.3):
                logger.warning(
                    f"⚠️ Unusually large deductions ({evaluation_data.deductions.total}) "
                    f"relative to total max ({evaluation_data.total_max})."
                )

            return evaluation_data

        except Exception as e:
            logger.error(f"Error evaluating resume: {str(e)}")
            raise
