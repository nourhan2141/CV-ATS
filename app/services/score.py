import os
import sys
import json
import logging
import csv
from app.services.pdf import PDFHandler
from app.services.github import fetch_and_display_github_info
from app.services.blog import fetch_and_summarize_blog
from app.core.models import JSONResume, EvaluationData, ATSFormattingReport, CATEGORY_MAX_SCORES
from typing import List, Optional, Dict
from app.services.evaluator import ResumeEvaluator
from app.services.ats_formatting import DeterministicATSChecker
from pathlib import Path
from app.core.prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from app.utils.transform import (
    transform_evaluation_response,
    convert_json_resume_to_text,
    convert_github_data_to_text,
    convert_blog_data_to_text,
    CSV_FIELD_NAMES,
)
from app.core.config import DEVELOPMENT_MODE, PERSIST_EVALUATION_DATA

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)


def print_evaluation_results(
    evaluation: EvaluationData, candidate_name: str = "Candidate"
):
    """Print evaluation results in a readable format."""
    logger.info("\n" + "=" * 80)
    logger.info(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
    logger.info("=" * 80)

    if not evaluation:
        logger.info("❌ No evaluation data available")
        return

    # Calculate overall score
    total_score = 0
    max_score = 0

    if hasattr(evaluation, "scores") and evaluation.scores:
        for category_name, category_data in evaluation.scores.model_dump().items():
            category_score = min(category_data["score"], category_data["max"])
            total_score += category_score
            max_score += category_data["max"]

            # Log warning if score was capped
            if category_score < category_data["score"]:
                logger.info(
                    f"⚠️  Warning: {category_name} score capped from {category_data['score']} to {category_score} (max: {category_data['max']})"
                )

    # Subtract deductions
    if hasattr(evaluation, "deductions") and evaluation.deductions:
        total_score -= evaluation.deductions.total

    # Ensure total score doesn't exceed maximum possible score
    max_possible_score = max_score
    if total_score > max_possible_score:
        total_score = max_possible_score
        logger.info(f"  Warning: Total score capped at maximum possible value")

    # Overall Score
    logger.info(f"\n OVERALL SCORE: {total_score:.1f}/{max_score}")

    # Detailed Scores
    logger.info("\n DETAILED SCORES:")
    logger.info("-" * 60)

    if hasattr(evaluation, "scores") and evaluation.scores:
        # Define category maximums
        category_maxes = CATEGORY_MAX_SCORES

        # Parseability & Formatting
        if hasattr(evaluation.scores, "parseability_formatting") and evaluation.scores.parseability_formatting:
            pf_score = evaluation.scores.parseability_formatting
            capped_score = min(pf_score.score, category_maxes["parseability_formatting"])
            logger.info(f"📄 Parseability & Format:  {capped_score}/{pf_score.max}")
            logger.info(f"   Evidence: {pf_score.evidence}")
            logger.info("")

        # Section Structure
        if (
            hasattr(evaluation.scores, "section_structure")
            and evaluation.scores.section_structure
        ):
            ss_score = evaluation.scores.section_structure
            capped_score = min(ss_score.score, category_maxes["section_structure"])
            logger.info(f"📑 Section Structure:      {capped_score}/{ss_score.max}")
            logger.info(f"   Evidence: {ss_score.evidence}")
            logger.info("")

        # Content Quality
        if hasattr(evaluation.scores, "content_quality") and evaluation.scores.content_quality:
            cq_score = evaluation.scores.content_quality
            capped_score = min(cq_score.score, category_maxes["content_quality"])
            logger.info(f"✍️ Content Quality:        {capped_score}/{cq_score.max}")
            logger.info(f"   Evidence: {cq_score.evidence}")
            logger.info("")

        # Keyword Optimization
        if (
            hasattr(evaluation.scores, "keyword_optimization")
            and evaluation.scores.keyword_optimization
        ):
            ko_score = evaluation.scores.keyword_optimization
            capped_score = min(ko_score.score, category_maxes["keyword_optimization"])
            logger.info(f"🔍 Keyword Optimization:   {capped_score}/{ko_score.max}")
            logger.info(f"   Evidence: {ko_score.evidence}")
            logger.info("")

    # ATS Formatting Report
    if hasattr(evaluation, "ats_report") and evaluation.ats_report:
        report = evaluation.ats_report
        logger.info(f"\n📊 ATS DETERMINISTIC REPORT:")
        logger.info("-" * 30)
        logger.info(f"  Multi-column layout: {'Yes ❌' if report.has_multi_column_layout else 'No ✅'}")
        logger.info(f"  Contains tables:     {'Yes ❌' if report.has_tables else 'No ✅'}")
        logger.info(f"  Text in images:      {'Yes ❌' if report.has_text_in_images else 'No ✅'}")
        logger.info(f"  Scanned PDF:         {'Yes ❌' if report.is_scanned_pdf else 'No ✅'}")
        logger.info(f"  Contact in headers:  {'Yes ❌' if report.contact_info_in_header_footer else 'No ✅'}")
        if report.missing_sections:
            logger.info(f"  Missing sections:    {', '.join(report.missing_sections)} ❌")
        logger.info(f"  Word count:          {report.word_count}")
        logger.info(f"  Page count:          {report.page_count}")

    # Deductions
    if (
        hasattr(evaluation, "deductions")
        and evaluation.deductions
        and evaluation.deductions.total > 0
    ):
        logger.info(f"\n⚠️  DEDUCTIONS: -{evaluation.deductions.total}")
        logger.info("-" * 30)
        if evaluation.deductions.reasons:
            logger.info(f"   {evaluation.deductions.reasons}")

    # Key Strengths
    if hasattr(evaluation, "key_strengths") and evaluation.key_strengths:
        logger.info(f"\n✅ KEY STRENGTHS:")
        logger.info("-" * 30)
        for i, strength in enumerate(evaluation.key_strengths, 1):
            logger.info(f"  {i}. {strength}")

    # Areas for Improvement
    if (
        hasattr(evaluation, "areas_for_improvement")
        and evaluation.areas_for_improvement
    ):
        logger.info(f"\n🔧 AREAS FOR IMPROVEMENT:")
        logger.info("-" * 30)
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            logger.info(f"  {i}. {area}")

    logger.info("\n" + "=" * 80)


def _evaluate_resume(
    resume_data: JSONResume, github_data: dict = None, blog_data: dict = None, ats_report: ATSFormattingReport = None
) -> Optional[EvaluationData]:
    """Evaluate the resume using AI and display results."""

    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(model_name=DEFAULT_MODEL, model_params=model_params)

    # Convert JSON resume data to text
    resume_text = convert_json_resume_to_text(resume_data)

    # Evaluate the resume using deterministic formatting flags and JSON data
    evaluation_result = evaluator.evaluate_resume(resume_text, ats_report=ats_report)

    # Inject ATS Formatting Report
    if evaluation_result and ats_report:
        evaluation_result.ats_report = ats_report

    # logger.info(evaluation_result)

    return evaluation_result


def is_valid_resume_data(resume_data: JSONResume) -> bool:
    """Check if the resume data has at least some extracted core content."""
    if not resume_data:
        return False
    core_sections = [
        resume_data.basics,
        resume_data.work,
        resume_data.education,
        resume_data.skills,
        resume_data.projects,
    ]
    return any(section is not None for section in core_sections)


def find_profile(profiles, network):
    if not profiles:
        return None
    return next(
        (p for p in profiles if p.network and p.network.lower() == network.lower()),
        None,
    )


def evaluate_pdf(pdf_path, use_cache=True):
    # Create cache filename based on PDF path
    cache_filename = (
        f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    github_cache_filename = (
        f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    blog_cache_filename = (
        f"cache/blogcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )

    resume_data = None
    ats_report = None
    cache_loaded = False

    # Check if cache exists and we're persisting evaluation data
    if use_cache and PERSIST_EVALUATION_DATA and os.path.exists(cache_filename):
        logger.info(f"Loading cached data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            loaded_resume = JSONResume(**cached_data)
            if not is_valid_resume_data(loaded_resume):
                raise ValueError("Cached resume data contains no core content")
            resume_data = loaded_resume
            cache_loaded = True
        except Exception as e:
            logger.warning(f"Invalid cache file {cache_filename}: {e}")
            logger.info("Ignoring cache and reprocessing PDF...")
            try:
                os.remove(cache_filename)
            except Exception as delete_err:
                logger.info(
                    f"Failed to delete invalid cache file {cache_filename}: {delete_err}"
                )

    if not cache_loaded:
        logger.debug(
            f"Extracting data from PDF"
            + (" and caching to " + cache_filename if PERSIST_EVALUATION_DATA else "")
        )
        pdf_handler = PDFHandler()
        extract_result = pdf_handler.extract_json_from_pdf(pdf_path)
        # Handle both single return (if cache logic gets confused) or tuple return
        if isinstance(extract_result, tuple):
            resume_data, ats_report = extract_result
        else:
            resume_data = extract_result

        if resume_data == None:
            return None

        if PERSIST_EVALUATION_DATA:
            if is_valid_resume_data(resume_data):
                os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
                Path(cache_filename).write_text(
                    json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            else:
                logger.warning(
                    "Newly extracted resume data is empty/invalid. Skipping cache write."
                )

    # Check if cache exists and we're in development mode
    github_data = {}
    github_cache_loaded = False
    
    # Only fetch external profile data if we are persisting for batch/CSV export
    if PERSIST_EVALUATION_DATA:
        if use_cache and DEVELOPMENT_MODE and os.path.exists(github_cache_filename):
            logger.info(f"Loading cached data from {github_cache_filename}")
            try:
                loaded_github = json.loads(
                    Path(github_cache_filename).read_text(encoding="utf-8")
                )
                if (
                    not isinstance(loaded_github, dict)
                    or not loaded_github
                    or "profile" not in loaded_github
                ):
                    raise ValueError("Cached GitHub data is invalid or empty")
                github_data = loaded_github
                github_cache_loaded = True
            except Exception as e:
                logger.warning(f"Invalid GitHub cache file {github_cache_filename}: {e}")
                logger.info("Ignoring GitHub cache and refetching...")
                try:
                    os.remove(github_cache_filename)
                except Exception as delete_err:
                    logger.info(
                        f"Failed to delete invalid GitHub cache file {github_cache_filename}: {delete_err}"
                    )

        if not github_cache_loaded:
            # Add validation to handle None values
            profiles = []
            if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
                profiles = resume_data.basics.profiles or []
            github_profile = find_profile(profiles, "Github")

            if github_profile:
                logger.info(
                    f"Fetching GitHub data"
                    + (
                        " and caching to " + github_cache_filename
                        if DEVELOPMENT_MODE
                        else ""
                    )
                )
                github_data = fetch_and_display_github_info(github_profile.url)

                if (
                    DEVELOPMENT_MODE
                    and github_data
                    and isinstance(github_data, dict)
                    and "profile" in github_data
                ):
                    os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
                    Path(github_cache_filename).write_text(
                        json.dumps(github_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )

    # Check if blog cache exists
    blog_data = {}
    blog_cache_loaded = False
    
    if PERSIST_EVALUATION_DATA:
        if use_cache and DEVELOPMENT_MODE and os.path.exists(blog_cache_filename):
            logger.info(f"Loading cached blog data from {blog_cache_filename}")
            try:
                loaded_blog = json.loads(Path(blog_cache_filename).read_text(encoding="utf-8"))
                if loaded_blog:
                    blog_data = loaded_blog
                    blog_cache_loaded = True
            except Exception as e:
                logger.warning(f"Invalid blog cache file {blog_cache_filename}: {e}")
                try:
                    os.remove(blog_cache_filename)
                except Exception:
                    pass

        if not blog_cache_loaded:
            profiles = []
            if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
                profiles = resume_data.basics.profiles or []
                
            dev_profile = find_profile(profiles, "DEV Community")
            medium_profile = find_profile(profiles, "Medium")
            
            blog_profile = dev_profile or medium_profile
            
            if blog_profile:
                network = blog_profile.network
                logger.info(f"Fetching Blog data from {network}" + (" and caching to " + blog_cache_filename if DEVELOPMENT_MODE else ""))
                blog_data = fetch_and_summarize_blog(blog_profile.url, network)
                
                if DEVELOPMENT_MODE and blog_data:
                    os.makedirs(os.path.dirname(blog_cache_filename), exist_ok=True)
                    Path(blog_cache_filename).write_text(
                        json.dumps(blog_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )

    # Extract deterministic ATS formatting checks if not already extracted
    if ats_report is None:
        logger.info("Extracting deterministic ATS formatting checks...")
        try:
            ats_checker = DeterministicATSChecker(pdf_path)
            ats_report = ats_checker.analyze()
        except Exception as e:
            logger.warning(f"Failed to extract ATS formatting report: {e}")
            ats_report = None

    score = _evaluate_resume(resume_data, github_data, blog_data=blog_data, ats_report=ats_report)

    # Get candidate name for display
    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if (
        resume_data
        and hasattr(resume_data, "basics")
        and resume_data.basics
        and resume_data.basics.name
    ):
        candidate_name = resume_data.basics.name

    # Print evaluation results in readable format
    print_evaluation_results(score, candidate_name)

    if PERSIST_EVALUATION_DATA:
        csv_row = transform_evaluation_response(
            file_name=os.path.basename(pdf_path),
            evaluation=score,
            resume_data=resume_data,
            github_data=github_data,
        )

        # Write CSV row to file
        csv_path = "resume_evaluations.csv"
        file_exists = os.path.exists(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELD_NAMES)

            # Write headers if file doesn't exist
            if not file_exists:
                writer.writeheader()

            # Write the row
            writer.writerow(csv_row)

    return score

