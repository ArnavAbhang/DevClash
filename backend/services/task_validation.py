"""
services/task_validation.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Production-grade task validation service for MeetNova.
Provides comprehensive validation, normalization, and enrichment capabilities
for detected tasks to ensure data integrity and quality.
"""

import re
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from collections import defaultdict
import hashlib
import json

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of task validation with detailed feedback."""
    is_valid: bool
    confidence_score: float
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]
    normalized_data: Dict[str, Any]


@dataclass
class ParticipantMatch:
    """Result of participant matching with confidence."""
    matched_name: Optional[str]
    confidence: float
    match_type: str  # "exact", "fuzzy", "alias", "partial"
    original_input: str


@dataclass
class DeadlineParseResult:
    """Result of deadline parsing with metadata."""
    parsed_date: Optional[str]  # ISO format date
    confidence: float
    parse_method: str  # "pattern", "nlp", "explicit"
    original_input: str
    relative_days: Optional[int] = None


@dataclass
class TaskSimilarity:
    """Similarity analysis between two tasks."""
    similarity_score: float
    title_similarity: float
    assignee_match: bool
    deadline_match: bool
    context_similarity: float
    is_duplicate: bool


class TaskValidation:
    """
    Production-grade task validation service providing comprehensive
    validation, normalization, and enrichment capabilities.
    
    Features:
    - Data integrity validation with detailed feedback
    - Advanced participant matching with fuzzy logic
    - Sophisticated deadline parsing with natural language support
    - Multi-factor confidence calculation
    - Intelligent task deduplication with similarity detection
    - Task enrichment with additional context and metadata
    - Performance optimization with caching
    """
    
    def __init__(self):
        # Known participants with aliases and variations
        self.known_participants = [
            "arnav", "kunal", "john", "sarah", "mike", "alex", "priya", "david", "emma", "ryan"
        ]
        
        self.participant_aliases = {
            "arnie": "arnav", "kun": "kunal", "johnny": "john", "sara": "sarah",
            "michael": "mike", "alexander": "alex", "dave": "david", "em": "emma"
        }
        
        # Common name variations and nicknames
        self.name_variations = {
            "john": ["johnny", "jon", "johnnie"],
            "sarah": ["sara", "sally"],
            "michael": ["mike", "mick", "mickey"],
            "alexander": ["alex", "al", "xander"],
            "david": ["dave", "davey"],
            "emma": ["em", "emmy"]
        }
        
        # Enhanced deadline patterns with confidence scores
        self.deadline_patterns = {
            # Immediate timeframes (high confidence)
            r'\b(right\s+now|immediately|asap|urgent|today)\b': (0, 0.95),
            r'\b(this\s+afternoon|tonight|this\s+evening|end\s+of\s+day|eod)\b': (0, 0.9),
            r'\b(by\s+end\s+of\s+day|by\s+eod|before\s+5)\b': (0, 0.9),
            
            # Tomorrow (high confidence)
            r'\b(tomorrow|by\s+tomorrow|tomorrow\s+morning)\b': (1, 0.9),
            r'\b(next\s+business\s+day|first\s+thing\s+tomorrow)\b': (1, 0.85),
            
            # This week (medium-high confidence)
            r'\b(this\s+week|by\s+friday|end\s+of\s+week|eow)\b': (self._days_until_friday, 0.8),
            r'\b(by\s+the\s+end\s+of\s+the\s+week|before\s+weekend)\b': (self._days_until_friday, 0.8),
            
            # Next week (medium confidence)
            r'\b(next\s+week|early\s+next\s+week|beginning\s+of\s+next\s+week)\b': (self._days_until_next_monday, 0.75),
            r'\b(by\s+next\s+friday|end\s+of\s+next\s+week)\b': (self._days_until_next_friday, 0.75),
            
            # Specific weekdays (medium confidence)
            r'\b(by\s+)?monday\b': (lambda: self._days_until_weekday(0), 0.8),
            r'\b(by\s+)?tuesday\b': (lambda: self._days_until_weekday(1), 0.8),
            r'\b(by\s+)?wednesday\b': (lambda: self._days_until_weekday(2), 0.8),
            r'\b(by\s+)?thursday\b': (lambda: self._days_until_weekday(3), 0.8),
            r'\b(by\s+)?friday\b': (lambda: self._days_until_weekday(4), 0.8),
            r'\b(by\s+)?saturday\b': (lambda: self._days_until_weekday(5), 0.7),
            r'\b(by\s+)?sunday\b': (lambda: self._days_until_weekday(6), 0.7),
            
            # Longer timeframes (lower confidence)
            r'\b(in\s+a\s+few\s+days|few\s+days)\b': (3, 0.6),
            r'\b(next\s+month|by\s+month\s+end)\b': (30, 0.5),
            r'\b(quarter\s+end|end\s+of\s+quarter)\b': (90, 0.4),
        }
        
        # Task quality indicators
        self.quality_indicators = {
            "high_quality": [
                "implement", "fix", "deploy", "create", "build", "update", "test", "review",
                "complete", "finish", "deliver", "prepare", "setup", "configure"
            ],
            "medium_quality": [
                "check", "verify", "validate", "analyze", "investigate", "research",
                "document", "write", "design", "plan"
            ],
            "low_quality": [
                "think about", "consider", "maybe", "perhaps", "possibly", "might"
            ]
        }
        
        # Priority indicators with weights
        self.priority_weights = {
            "urgent": 1.0, "asap": 1.0, "critical": 0.9, "important": 0.8,
            "high priority": 0.8, "must have": 0.7, "blocker": 0.9,
            "low priority": -0.5, "nice to have": -0.3, "optional": -0.4,
            "when possible": -0.3, "eventually": -0.6, "someday": -0.7
        }
        
        # Task categories for enrichment
        self.task_categories = {
            "development": ["code", "implement", "build", "develop", "program", "debug", "fix"],
            "testing": ["test", "qa", "verify", "validate", "check"],
            "deployment": ["deploy", "release", "launch", "publish", "go live"],
            "documentation": ["document", "write", "update docs", "readme", "documentation"],
            "meeting": ["schedule", "meet", "call", "discuss", "sync"],
            "research": ["research", "investigate", "analyze", "study", "explore"],
            "design": ["design", "mockup", "wireframe", "prototype", "ui", "ux"],
            "infrastructure": ["setup", "configure", "install", "provision"]
        }
        
        # Validation cache for performance
        self.validation_cache: Dict[str, ValidationResult] = {}
        self.similarity_cache: Dict[str, TaskSimilarity] = {}
        
    @staticmethod
    def _days_until_weekday(target_weekday: int) -> int:
        """Calculate days until target weekday (0=Monday, 6=Sunday)."""
        today = datetime.now().weekday()
        days_ahead = target_weekday - today
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return days_ahead
    
    @staticmethod
    def _days_until_friday() -> int:
        """Calculate days until Friday."""
        return TaskValidation._days_until_weekday(4)
    
    @staticmethod
    def _days_until_next_monday() -> int:
        """Calculate days until next Monday."""
        today = datetime.now().weekday()
        days_ahead = 7 - today
        return days_ahead
    
    @staticmethod
    def _days_until_next_friday() -> int:
        """Calculate days until next Friday."""
        return TaskValidation._days_until_friday() + 7
    
    def validateTaskStructure(self, task_data: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive task structure validation with detailed feedback.
        
        Args:
            task_data: Dictionary containing task information
            
        Returns:
            ValidationResult with validation status and detailed feedback
        """
        # Check cache first
        cache_key = self._generate_validation_cache_key(task_data)
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]
        
        issues = []
        warnings = []
        suggestions = []
        normalized_data = task_data.copy()
        confidence_factors = []
        
        # Validate required fields
        if not task_data.get("title"):
            issues.append("Task title is required")
        else:
            title = task_data["title"].strip()
            if len(title) < 3:
                issues.append("Task title must be at least 3 characters long")
            elif len(title) > 200:
                warnings.append("Task title is very long, consider shortening")
                normalized_data["title"] = title[:200]
            else:
                confidence_factors.append(0.8)  # Good title length
        
        # Validate confidence score
        confidence = task_data.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            issues.append("Confidence must be a number")
        elif not 0.0 <= confidence <= 1.0:
            issues.append("Confidence must be between 0.0 and 1.0")
            normalized_data["confidence"] = max(0.0, min(1.0, float(confidence)))
        else:
            confidence_factors.append(confidence)
        
        # Validate priority
        priority = task_data.get("priority", "medium")
        if priority not in ["low", "medium", "high"]:
            warnings.append(f"Invalid priority '{priority}', defaulting to 'medium'")
            normalized_data["priority"] = "medium"
        else:
            confidence_factors.append(0.7)
        
        # Validate status
        status = task_data.get("status", "pending")
        if status not in ["pending", "in-progress", "done"]:
            warnings.append(f"Invalid status '{status}', defaulting to 'pending'")
            normalized_data["status"] = "pending"
        
        # Validate assignee if present
        assignee = task_data.get("assignee")
        if assignee:
            if not isinstance(assignee, str):
                issues.append("Assignee must be a string")
            elif len(assignee.strip()) == 0:
                warnings.append("Empty assignee, removing")
                normalized_data["assignee"] = None
            else:
                confidence_factors.append(0.6)  # Bonus for having assignee
        
        # Validate deadline if present
        deadline = task_data.get("deadline")
        if deadline:
            if not isinstance(deadline, str):
                issues.append("Deadline must be a string")
            else:
                # Try to parse the deadline
                parse_result = self.parseDeadline(deadline)
                if parse_result.parsed_date:
                    normalized_data["deadline"] = parse_result.parsed_date
                    confidence_factors.append(parse_result.confidence * 0.5)
                else:
                    warnings.append(f"Could not parse deadline '{deadline}'")
        
        # Validate description
        description = task_data.get("description", "")
        if description and len(description) > 1000:
            warnings.append("Description is very long, consider shortening")
            normalized_data["description"] = description[:1000]
        
        # Validate source_text
        source_text = task_data.get("source_text", "")
        if not source_text:
            warnings.append("No source text provided, context may be limited")
        elif len(source_text) > 2000:
            normalized_data["source_text"] = source_text[:2000]
        
        # Quality assessment
        title_lower = normalized_data.get("title", "").lower()
        quality_score = self._assess_task_quality(title_lower, description)
        confidence_factors.append(quality_score)
        
        if quality_score < 0.5:
            warnings.append("Task appears to be low quality or vague")
            suggestions.append("Consider making the task more specific and actionable")
        
        # Calculate overall confidence
        overall_confidence = (
            sum(confidence_factors) / len(confidence_factors) 
            if confidence_factors else 0.0
        )
        
        # Generate suggestions
        if not assignee:
            suggestions.append("Consider assigning this task to a specific person")
        if not deadline:
            suggestions.append("Consider adding a deadline for better tracking")
        if len(description) < 20:
            suggestions.append("Consider adding more details to the description")
        
        # Determine if valid
        is_valid = len(issues) == 0 and overall_confidence >= 0.5
        
        result = ValidationResult(
            is_valid=is_valid,
            confidence_score=overall_confidence,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions,
            normalized_data=normalized_data
        )
        
        # Cache result
        self.validation_cache[cache_key] = result
        if len(self.validation_cache) > 1000:  # Limit cache size
            oldest_key = next(iter(self.validation_cache))
            del self.validation_cache[oldest_key]
        
        logger.debug(f"Task validation: valid={is_valid}, confidence={overall_confidence:.2f}")
        return result
    
    def normalizeAssignee(self, assignee_input: Optional[str], 
                         context_participants: Optional[List[str]] = None) -> ParticipantMatch:
        """
        Advanced assignee normalization with participant matching.
        
        Args:
            assignee_input: Raw assignee string from task detection
            context_participants: List of participants mentioned in the meeting context
            
        Returns:
            ParticipantMatch with normalized name and confidence
        """
        if not assignee_input:
            return ParticipantMatch(
                matched_name=None,
                confidence=0.0,
                match_type="none",
                original_input=""
            )
        
        assignee_lower = assignee_input.lower().strip()
        
        # Combine known participants with context participants
        all_participants = self.known_participants.copy()
        if context_participants:
            all_participants.extend([p.lower() for p in context_participants])
        all_participants = list(set(all_participants))  # Remove duplicates
        
        # 1. Exact match with known participants (highest confidence)
        for participant in all_participants:
            if participant == assignee_lower:
                return ParticipantMatch(
                    matched_name=participant.title(),
                    confidence=0.95,
                    match_type="exact",
                    original_input=assignee_input
                )
        
        # 2. Exact alias match (high confidence)
        for alias, real_name in self.participant_aliases.items():
            if assignee_lower == alias and real_name in all_participants:
                return ParticipantMatch(
                    matched_name=real_name.title(),
                    confidence=0.9,
                    match_type="alias",
                    original_input=assignee_input
                )
        
        # 3. Name variation match (high confidence)
        for base_name, variations in self.name_variations.items():
            if assignee_lower in variations and base_name in all_participants:
                return ParticipantMatch(
                    matched_name=base_name.title(),
                    confidence=0.85,
                    match_type="variation",
                    original_input=assignee_input
                )
        
        # 4. Fuzzy matching with known participants (medium confidence)
        best_match = None
        best_ratio = 0.0
        
        for participant in all_participants:
            ratio = SequenceMatcher(None, assignee_lower, participant).ratio()
            if ratio > best_ratio and ratio > 0.7:  # 70% similarity threshold
                best_ratio = ratio
                best_match = participant
        
        if best_match:
            confidence = 0.6 + (best_ratio - 0.7) * 0.2  # Scale to 0.6-0.8
            return ParticipantMatch(
                matched_name=best_match.title(),
                confidence=confidence,
                match_type="fuzzy",
                original_input=assignee_input
            )
        
        # 5. Partial match (lower confidence)
        for participant in all_participants:
            if assignee_lower in participant or participant in assignee_lower:
                if len(assignee_lower) >= 3:  # Avoid matching very short strings
                    return ParticipantMatch(
                        matched_name=participant.title(),
                        confidence=0.5,
                        match_type="partial",
                        original_input=assignee_input
                    )
        
        # 6. Check for common pronouns and convert to generic
        pronouns = ["i", "me", "myself", "we", "us", "our"]
        if assignee_lower in pronouns:
            return ParticipantMatch(
                matched_name="Speaker",
                confidence=0.6,
                match_type="pronoun",
                original_input=assignee_input
            )
        
        # 7. Return cleaned version if no match found
        cleaned = assignee_input.strip().title()
        return ParticipantMatch(
            matched_name=cleaned,
            confidence=0.3,  # Low confidence for unknown names
            match_type="unknown",
            original_input=assignee_input
        )
    
    def parseDeadline(self, deadline_input: str) -> DeadlineParseResult:
        """
        Advanced deadline parsing with natural language support.
        
        Args:
            deadline_input: Raw deadline string from task detection
            
        Returns:
            DeadlineParseResult with parsed date and metadata
        """
        if not deadline_input:
            return DeadlineParseResult(
                parsed_date=None,
                confidence=0.0,
                parse_method="none",
                original_input=""
            )
        
        deadline_lower = deadline_input.lower().strip()
        
        # 1. Pattern-based parsing (highest confidence)
        for pattern, (days_offset, confidence) in self.deadline_patterns.items():
            match = re.search(pattern, deadline_lower)
            if match:
                try:
                    if callable(days_offset):
                        days_offset = days_offset()
                    
                    target_date = datetime.now() + timedelta(days=days_offset)
                    date_str = target_date.strftime("%Y-%m-%d")
                    
                    return DeadlineParseResult(
                        parsed_date=date_str,
                        confidence=confidence,
                        parse_method="pattern",
                        original_input=deadline_input,
                        relative_days=days_offset
                    )
                except Exception as e:
                    logger.warning(f"Error calculating date offset: {e}")
                    continue
        
        # 2. Explicit date parsing (high confidence)
        date_patterns = [
            (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', 0.95),  # YYYY-MM-DD
            (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', 0.9),   # MM/DD/YYYY
            (r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b', 0.9),   # MM-DD-YYYY
            (r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', 0.85), # MM.DD.YYYY
        ]
        
        for pattern, confidence in date_patterns:
            match = re.search(pattern, deadline_input)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Try to parse the date
                        if pattern.startswith(r'\b(\d{4})'):  # YYYY-MM-DD
                            year, month, day = groups
                        else:  # MM/DD/YYYY or similar
                            month, day, year = groups
                        
                        # Basic validation
                        year, month, day = int(year), int(month), int(day)
                        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                            date_obj = datetime(year, month, day)
                            date_str = date_obj.strftime("%Y-%m-%d")
                            
                            return DeadlineParseResult(
                                parsed_date=date_str,
                                confidence=confidence,
                                parse_method="explicit",
                                original_input=deadline_input
                            )
                except (ValueError, TypeError) as e:
                    logger.debug(f"Date parsing failed: {e}")
                    continue
        
        # 3. Month and day parsing (medium confidence)
        month_patterns = [
            (r'\b(january|jan)\s+(\d{1,2})\b', 1),
            (r'\b(february|feb)\s+(\d{1,2})\b', 2),
            (r'\b(march|mar)\s+(\d{1,2})\b', 3),
            (r'\b(april|apr)\s+(\d{1,2})\b', 4),
            (r'\b(may)\s+(\d{1,2})\b', 5),
            (r'\b(june|jun)\s+(\d{1,2})\b', 6),
            (r'\b(july|jul)\s+(\d{1,2})\b', 7),
            (r'\b(august|aug)\s+(\d{1,2})\b', 8),
            (r'\b(september|sep)\s+(\d{1,2})\b', 9),
            (r'\b(october|oct)\s+(\d{1,2})\b', 10),
            (r'\b(november|nov)\s+(\d{1,2})\b', 11),
            (r'\b(december|dec)\s+(\d{1,2})\b', 12),
        ]
        
        for pattern, month_num in month_patterns:
            match = re.search(pattern, deadline_lower)
            if match:
                try:
                    day = int(match.group(2))
                    if 1 <= day <= 31:
                        current_year = datetime.now().year
                        current_month = datetime.now().month
                        
                        # If the month has passed this year, assume next year
                        year = current_year if month_num >= current_month else current_year + 1
                        
                        date_obj = datetime(year, month_num, day)
                        date_str = date_obj.strftime("%Y-%m-%d")
                        
                        return DeadlineParseResult(
                            parsed_date=date_str,
                            confidence=0.75,
                            parse_method="month_day",
                            original_input=deadline_input
                        )
                except (ValueError, TypeError):
                    continue
        
        # 4. Numeric day parsing (lower confidence)
        day_match = re.search(r'\b(\d{1,2})(st|nd|rd|th)?\b', deadline_lower)
        if day_match:
            try:
                day = int(day_match.group(1))
                if 1 <= day <= 31:
                    # Assume current month
                    current_date = datetime.now()
                    try:
                        if day > current_date.day:
                            # This month
                            date_obj = datetime(current_date.year, current_date.month, day)
                        else:
                            # Next month
                            next_month = current_date.month + 1
                            year = current_date.year
                            if next_month > 12:
                                next_month = 1
                                year += 1
                            date_obj = datetime(year, next_month, day)
                        
                        date_str = date_obj.strftime("%Y-%m-%d")
                        
                        return DeadlineParseResult(
                            parsed_date=date_str,
                            confidence=0.5,
                            parse_method="numeric_day",
                            original_input=deadline_input
                        )
                    except ValueError:
                        pass
            except (ValueError, TypeError):
                pass
        
        # No successful parsing
        return DeadlineParseResult(
            parsed_date=None,
            confidence=0.0,
            parse_method="failed",
            original_input=deadline_input
        )
    
    def calculateConfidence(self, task_data: Dict[str, Any], 
                          validation_result: Optional[ValidationResult] = None) -> float:
        """
        Multi-factor confidence calculation for task quality assessment.
        
        Args:
            task_data: Task data dictionary
            validation_result: Optional pre-computed validation result
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_factors = []
        
        # Base confidence from AI detection
        base_confidence = task_data.get("confidence", 0.5)
        confidence_factors.append(("base", base_confidence, 0.3))
        
        # Title quality factor
        title = task_data.get("title", "")
        title_quality = self._assess_task_quality(title.lower(), task_data.get("description", ""))
        confidence_factors.append(("title_quality", title_quality, 0.2))
        
        # Assignee factor
        assignee = task_data.get("assignee")
        if assignee:
            assignee_match = self.normalizeAssignee(assignee)
            assignee_factor = assignee_match.confidence
            confidence_factors.append(("assignee", assignee_factor, 0.15))
        else:
            confidence_factors.append(("assignee", 0.0, 0.15))
        
        # Deadline factor
        deadline = task_data.get("deadline")
        if deadline:
            deadline_result = self.parseDeadline(deadline)
            deadline_factor = deadline_result.confidence
            confidence_factors.append(("deadline", deadline_factor, 0.1))
        else:
            confidence_factors.append(("deadline", 0.0, 0.1))
        
        # Context factor
        source_text = task_data.get("source_text", "")
        context_factor = min(1.0, len(source_text) / 100.0)  # More context = higher confidence
        confidence_factors.append(("context", context_factor, 0.1))
        
        # Validation factor
        if validation_result:
            validation_factor = 1.0 if validation_result.is_valid else 0.5
            confidence_factors.append(("validation", validation_factor, 0.1))
        
        # Priority factor
        priority = task_data.get("priority", "medium")
        priority_factor = {"high": 0.8, "medium": 0.6, "low": 0.4}.get(priority, 0.5)
        confidence_factors.append(("priority", priority_factor, 0.05))
        
        # Calculate weighted average
        total_weight = sum(weight for _, _, weight in confidence_factors)
        weighted_sum = sum(score * weight for _, score, weight in confidence_factors)
        
        final_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Apply bonuses and penalties
        if task_data.get("urgency_indicators"):
            final_confidence += 0.05  # Bonus for urgency indicators
        
        if task_data.get("estimated_effort"):
            final_confidence += 0.02  # Bonus for effort estimation
        
        if len(task_data.get("tags", [])) > 0:
            final_confidence += 0.03  # Bonus for categorization
        
        # Ensure bounds
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        logger.debug(f"Confidence calculation: {final_confidence:.3f} from factors: {confidence_factors}")
        return final_confidence
    
    def deduplicateTasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Intelligent task deduplication with similarity detection.
        
        Args:
            tasks: List of task dictionaries to deduplicate
            
        Returns:
            List of unique tasks with duplicates removed
        """
        if not tasks:
            return []
        
        unique_tasks = []
        
        for task in tasks:
            is_duplicate = False
            best_existing_index = -1
            highest_similarity = 0.0
            
            for i, existing_task in enumerate(unique_tasks):
                similarity = self._calculateTaskSimilarity(task, existing_task)
                
                if similarity.is_duplicate:
                    is_duplicate = True
                    if similarity.similarity_score > highest_similarity:
                        highest_similarity = similarity.similarity_score
                        best_existing_index = i
            
            if is_duplicate and best_existing_index >= 0:
                # Keep the task with higher confidence
                existing_task = unique_tasks[best_existing_index]
                task_confidence = task.get("confidence", 0.0)
                existing_confidence = existing_task.get("confidence", 0.0)
                
                if task_confidence > existing_confidence:
                    # Replace existing with new task
                    unique_tasks[best_existing_index] = task
                    logger.debug(f"Replaced duplicate task with higher confidence: {task.get('title', '')}")
                else:
                    logger.debug(f"Skipped duplicate task: {task.get('title', '')}")
            else:
                unique_tasks.append(task)
        
        logger.info(f"Deduplication: {len(tasks)} -> {len(unique_tasks)} tasks")
        return unique_tasks
    
    def enrichTaskData(self, task_data: Dict[str, Any], 
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enrich task data with additional context and metadata.
        
        Args:
            task_data: Original task data dictionary
            context: Optional context information (meeting data, participants, etc.)
            
        Returns:
            Enriched task data dictionary
        """
        enriched_task = task_data.copy()
        
        # Add unique ID if not present
        if "id" not in enriched_task:
            enriched_task["id"] = str(uuid.uuid4())
        
        # Add timestamps
        if "created_at" not in enriched_task:
            enriched_task["created_at"] = datetime.now().isoformat()
        
        # Enrich title and description
        title = enriched_task.get("title", "")
        description = enriched_task.get("description", "")
        
        # Add task categories/tags
        if "tags" not in enriched_task or not enriched_task["tags"]:
            enriched_task["tags"] = self._categorizeTask(title, description)
        
        # Add effort estimation if not present
        if "estimated_effort" not in enriched_task or not enriched_task["estimated_effort"]:
            enriched_task["estimated_effort"] = self._estimateTaskEffort(title, description)
        
        # Add priority indicators
        if "urgency_indicators" not in enriched_task:
            enriched_task["urgency_indicators"] = self._extractUrgencyIndicators(
                title + " " + description + " " + enriched_task.get("source_text", "")
            )
        
        # Enhance assignee information
        assignee = enriched_task.get("assignee")
        if assignee:
            context_participants = context.get("participants", []) if context else []
            assignee_match = self.normalizeAssignee(assignee, context_participants)
            enriched_task["assignee"] = assignee_match.matched_name
            enriched_task["assignee_confidence"] = assignee_match.confidence
            enriched_task["assignee_match_type"] = assignee_match.match_type
        
        # Enhance deadline information
        deadline = enriched_task.get("deadline")
        if deadline:
            deadline_result = self.parseDeadline(deadline)
            if deadline_result.parsed_date:
                enriched_task["deadline"] = deadline_result.parsed_date
                enriched_task["deadline_confidence"] = deadline_result.confidence
                enriched_task["deadline_parse_method"] = deadline_result.parse_method
                if deadline_result.relative_days is not None:
                    enriched_task["deadline_relative_days"] = deadline_result.relative_days
        
        # Add context window
        source_text = enriched_task.get("source_text", "")
        if source_text and context and "full_transcript" in context:
            enriched_task["context_window"] = self._extractContextWindow(
                source_text, context["full_transcript"]
            )
        
        # Add task complexity score
        enriched_task["complexity_score"] = self._calculateTaskComplexity(title, description)
        
        # Add dependencies if context provides related tasks
        if context and "related_tasks" in context:
            enriched_task["potential_dependencies"] = self._identifyPotentialDependencies(
                enriched_task, context["related_tasks"]
            )
        
        # Add meeting context if available
        if context:
            if "meeting_id" in context:
                enriched_task["meeting_id"] = context["meeting_id"]
            if "meeting_title" in context:
                enriched_task["meeting_title"] = context["meeting_title"]
            if "meeting_duration" in context:
                enriched_task["meeting_duration"] = context["meeting_duration"]
        
        # Recalculate confidence with enriched data
        enriched_task["confidence"] = self.calculateConfidence(enriched_task)
        
        logger.debug(f"Enriched task: {enriched_task.get('title', '')} with {len(enriched_task)} fields")
        return enriched_task
    
    def _calculateTaskSimilarity(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> TaskSimilarity:
        """Calculate similarity between two tasks."""
        # Create cache key
        cache_key = self._generate_similarity_cache_key(task1, task2)
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        title1 = task1.get("title", "").lower()
        title2 = task2.get("title", "").lower()
        
        # Title similarity (most important factor)
        title_similarity = SequenceMatcher(None, title1, title2).ratio()
        
        # Assignee match
        assignee1 = task1.get("assignee", "")
        assignee2 = task2.get("assignee", "")
        assignee_match = (assignee1.lower() == assignee2.lower()) if assignee1 and assignee2 else False
        
        # Deadline match
        deadline1 = task1.get("deadline", "")
        deadline2 = task2.get("deadline", "")
        deadline_match = (deadline1 == deadline2) if deadline1 and deadline2 else False
        
        # Context similarity
        context1 = task1.get("source_text", "").lower()
        context2 = task2.get("source_text", "").lower()
        context_similarity = SequenceMatcher(None, context1, context2).ratio() if context1 and context2 else 0.0
        
        # Overall similarity calculation
        similarity_score = (
            title_similarity * 0.6 +
            (1.0 if assignee_match else 0.0) * 0.2 +
            (1.0 if deadline_match else 0.0) * 0.1 +
            context_similarity * 0.1
        )
        
        # Determine if duplicate
        is_duplicate = (
            title_similarity > 0.85 or
            (title_similarity > 0.7 and assignee_match and deadline_match) or
            (title_similarity > 0.75 and (assignee_match or deadline_match))
        )
        
        result = TaskSimilarity(
            similarity_score=similarity_score,
            title_similarity=title_similarity,
            assignee_match=assignee_match,
            deadline_match=deadline_match,
            context_similarity=context_similarity,
            is_duplicate=is_duplicate
        )
        
        # Cache result
        self.similarity_cache[cache_key] = result
        if len(self.similarity_cache) > 500:  # Limit cache size
            oldest_key = next(iter(self.similarity_cache))
            del self.similarity_cache[oldest_key]
        
        return result
    
    def _assess_task_quality(self, title_lower: str, description: str) -> float:
        """Assess the quality of a task based on its content."""
        quality_score = 0.5  # Base score
        
        # Check for high-quality indicators
        high_quality_count = sum(1 for word in self.quality_indicators["high_quality"] 
                               if word in title_lower)
        quality_score += high_quality_count * 0.1
        
        # Check for medium-quality indicators
        medium_quality_count = sum(1 for word in self.quality_indicators["medium_quality"] 
                                 if word in title_lower)
        quality_score += medium_quality_count * 0.05
        
        # Penalty for low-quality indicators
        low_quality_count = sum(1 for word in self.quality_indicators["low_quality"] 
                              if word in title_lower)
        quality_score -= low_quality_count * 0.1
        
        # Bonus for having description
        if description and len(description.strip()) > 10:
            quality_score += 0.1
        
        # Penalty for very short titles
        if len(title_lower.strip()) < 5:
            quality_score -= 0.2
        
        # Bonus for specific action words
        action_words = ["fix", "implement", "create", "update", "deploy", "test"]
        if any(word in title_lower for word in action_words):
            quality_score += 0.1
        
        return max(0.0, min(1.0, quality_score))
    
    def _categorizeTask(self, title: str, description: str) -> List[str]:
        """Categorize task based on content."""
        content = (title + " " + description).lower()
        categories = []
        
        for category, keywords in self.task_categories.items():
            if any(keyword in content for keyword in keywords):
                categories.append(category)
        
        # Add default category if none found
        if not categories:
            categories.append("general")
        
        return categories
    
    def _estimateTaskEffort(self, title: str, description: str) -> str:
        """Estimate task effort based on complexity indicators."""
        content = (title + " " + description).lower()
        
        # Simple heuristics for effort estimation
        if any(word in content for word in ["quick", "simple", "easy", "minor", "small"]):
            return "1-2 hours"
        elif any(word in content for word in ["complex", "major", "redesign", "refactor", "large"]):
            return "1-2 days"
        elif any(word in content for word in ["implement", "build", "create", "develop", "new"]):
            return "4-8 hours"
        elif any(word in content for word in ["fix", "bug", "issue", "problem"]):
            return "2-4 hours"
        elif any(word in content for word in ["test", "verify", "validate", "check"]):
            return "1-3 hours"
        elif any(word in content for word in ["document", "write", "update docs"]):
            return "2-4 hours"
        else:
            return "2-4 hours"  # Default estimate
    
    def _extractUrgencyIndicators(self, text: str) -> List[str]:
        """Extract urgency indicators from text."""
        text_lower = text.lower()
        indicators = []
        
        urgency_words = [
            "urgent", "asap", "immediately", "critical", "emergency", "now",
            "today", "tonight", "deadline", "due", "overdue", "blocking",
            "blocker", "high priority", "important", "must have"
        ]
        
        for word in urgency_words:
            if word in text_lower:
                indicators.append(word)
        
        return list(set(indicators))  # Remove duplicates
    
    def _extractContextWindow(self, source_text: str, full_transcript: str) -> str:
        """Extract surrounding context for better task understanding."""
        try:
            start_pos = full_transcript.lower().find(source_text.lower())
            if start_pos == -1:
                return source_text[:200]  # Fallback
            
            # Extract context window (100 chars before and after)
            context_start = max(0, start_pos - 100)
            context_end = min(len(full_transcript), start_pos + len(source_text) + 100)
            
            return full_transcript[context_start:context_end]
        except Exception:
            return source_text[:200]
    
    def _calculateTaskComplexity(self, title: str, description: str) -> float:
        """Calculate task complexity score."""
        content = (title + " " + description).lower()
        complexity_score = 0.5  # Base complexity
        
        # Complexity indicators
        complex_words = ["integrate", "refactor", "redesign", "architecture", "system", "multiple"]
        simple_words = ["fix", "update", "change", "add", "remove", "simple"]
        
        complex_count = sum(1 for word in complex_words if word in content)
        simple_count = sum(1 for word in simple_words if word in content)
        
        complexity_score += complex_count * 0.2
        complexity_score -= simple_count * 0.1
        
        # Length factor
        content_length = len(content)
        if content_length > 100:
            complexity_score += 0.1
        elif content_length < 20:
            complexity_score -= 0.1
        
        return max(0.0, min(1.0, complexity_score))
    
    def _identifyPotentialDependencies(self, task: Dict[str, Any], 
                                     related_tasks: List[Dict[str, Any]]) -> List[str]:
        """Identify potential task dependencies."""
        dependencies = []
        task_title = task.get("title", "").lower()
        
        for related_task in related_tasks:
            related_title = related_task.get("title", "").lower()
            
            # Simple dependency detection heuristics
            if "before" in task_title and any(word in related_title for word in task_title.split()):
                dependencies.append(related_task.get("id", ""))
            elif "after" in related_title and any(word in task_title for word in related_title.split()):
                dependencies.append(related_task.get("id", ""))
        
        return dependencies
    
    def _generate_validation_cache_key(self, task_data: Dict[str, Any]) -> str:
        """Generate cache key for validation results."""
        key_data = {
            "title": task_data.get("title", ""),
            "assignee": task_data.get("assignee", ""),
            "deadline": task_data.get("deadline", ""),
            "confidence": task_data.get("confidence", 0.0)
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def _generate_similarity_cache_key(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> str:
        """Generate cache key for similarity results."""
        # Create a consistent key regardless of task order
        title1 = task1.get("title", "")
        title2 = task2.get("title", "")
        
        if title1 < title2:
            key = f"{title1}|{title2}"
        else:
            key = f"{title2}|{title1}"
        
        return hashlib.md5(key.encode()).hexdigest()
    
    # Public utility methods
    
    def addParticipant(self, name: str, aliases: Optional[List[str]] = None):
        """Add a new participant to the known list."""
        if name and name.lower() not in self.known_participants:
            self.known_participants.append(name.lower())
            
            # Add aliases if provided
            if aliases:
                for alias in aliases:
                    if alias:
                        self.participant_aliases[alias.lower()] = name.lower()
            
            logger.info(f"Added participant: {name} with aliases: {aliases}")
    
    def addParticipantAlias(self, alias: str, real_name: str):
        """Add a participant alias for better name matching."""
        if alias and real_name:
            self.participant_aliases[alias.lower()] = real_name.lower()
            logger.info(f"Added alias: {alias} -> {real_name}")
    
    def getParticipants(self) -> List[str]:
        """Get list of known participants."""
        return [p.title() for p in self.known_participants]
    
    def clearCache(self):
        """Clear all caches."""
        self.validation_cache.clear()
        self.similarity_cache.clear()
        logger.info("Task validation caches cleared")
    
    def getValidationStatistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "validation_cache_size": len(self.validation_cache),
            "similarity_cache_size": len(self.similarity_cache),
            "known_participants": len(self.known_participants),
            "participant_aliases": len(self.participant_aliases),
            "deadline_patterns": len(self.deadline_patterns),
            "task_categories": len(self.task_categories)
        }
    
    def validateTaskBatch(self, tasks: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate a batch of tasks efficiently."""
        results = []
        
        for task in tasks:
            try:
                result = self.validateTaskStructure(task)
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating task: {e}")
                results.append(ValidationResult(
                    is_valid=False,
                    confidence_score=0.0,
                    issues=[f"Validation error: {str(e)}"],
                    warnings=[],
                    suggestions=[],
                    normalized_data=task
                ))
        
        return results
    
    def processTaskPipeline(self, task_data: Dict[str, Any], 
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete task processing pipeline: validate, normalize, and enrich.
        
        Args:
            task_data: Raw task data
            context: Optional context information
            
        Returns:
            Fully processed and enriched task data
        """
        # Step 1: Validate task structure
        validation_result = self.validateTaskStructure(task_data)
        
        if not validation_result.is_valid:
            logger.warning(f"Task validation failed: {validation_result.issues}")
            # Use normalized data even if validation failed
            processed_task = validation_result.normalized_data
        else:
            processed_task = validation_result.normalized_data
        
        # Step 2: Enrich task data
        enriched_task = self.enrichTaskData(processed_task, context)
        
        # Step 3: Add validation metadata
        enriched_task["validation_result"] = {
            "is_valid": validation_result.is_valid,
            "confidence_score": validation_result.confidence_score,
            "issues": validation_result.issues,
            "warnings": validation_result.warnings,
            "suggestions": validation_result.suggestions
        }
        
        logger.info(f"Processed task pipeline: {enriched_task.get('title', '')} "
                   f"(valid: {validation_result.is_valid}, confidence: {validation_result.confidence_score:.2f})")
        
        return enriched_task