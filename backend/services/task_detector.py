"""
services/task_detector.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Production-grade AI-powered task detection from transcribed speech.
Enhanced with sophisticated AI processing, buffered transcript handling,
advanced assignee extraction, deadline parsing, and confidence scoring.
"""

import asyncio
import re
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from collections import defaultdict
import hashlib

from groq import Groq
from core.config import settings

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DetectedTask:
    """Structured task detected from speech with enhanced metadata."""
    id: str
    title: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    description: str = ""
    priority: str = "medium"  # low, medium, high
    status: str = "pending"   # pending, in-progress, done
    confidence: float = 0.0
    source_text: str = ""
    created_at: str = ""
    # Enhanced fields for production
    dependencies: List[str] = None  # Task IDs this task depends on
    tags: List[str] = None  # Categorization tags
    estimated_effort: Optional[str] = None  # time estimate
    urgency_indicators: List[str] = None  # Words that indicated urgency
    assignee_confidence: float = 0.0  # Confidence in assignee extraction
    deadline_confidence: float = 0.0  # Confidence in deadline parsing
    context_window: str = ""  # Surrounding text for context
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.urgency_indicators is None:
            self.urgency_indicators = []


@dataclass
class TaskRelationship:
    """Represents relationships between tasks."""
    parent_task_id: str
    child_task_id: str
    relationship_type: str  # "depends_on", "blocks", "related_to"
    confidence: float = 0.0


@dataclass
class ProcessingMetrics:
    """Metrics for task detection performance."""
    processing_time: float = 0.0
    chunks_processed: int = 0
    tasks_detected: int = 0
    confidence_scores: List[float] = None
    api_calls_made: int = 0
    cache_hits: int = 0
    
    def __post_init__(self):
        if self.confidence_scores is None:
            self.confidence_scores = []


class TaskDetector:
    """
    Production-grade task detection from transcribed speech using AI and rule-based approaches.
    
    Features:
    - Buffered transcript processing for complete context
    - Advanced AI prompting with sophisticated task detection patterns
    - Complex task relationship detection
    - Fuzzy matching for assignee extraction
    - Natural language deadline parsing
    - Priority detection based on urgency indicators
    - Multi-factor confidence scoring
    - Performance monitoring and caching
    """
    
    def __init__(self):
        self.groq_client = None
        self.processed_texts: List[str] = []  # For deduplication
        self.task_cache: Dict[str, List[DetectedTask]] = {}  # Cache for similar inputs
        self.processing_metrics = ProcessingMetrics()
        
        # Enhanced participant management with fuzzy matching
        self.known_participants = [
            "arnav", "kunal", "john", "sarah", "mike", "alex", "priya", "david", "emma", "ryan"
        ]
        self.participant_aliases = {
            "arnie": "arnav", "kun": "kunal", "johnny": "john", "sara": "sarah",
            "michael": "mike", "alexander": "alex", "dave": "david", "em": "emma"
        }
        
        # Enhanced transcript buffer with context management
        self.transcript_buffer = ""
        self.context_buffer = []  # Store recent context for better understanding
        self.buffer_word_threshold = 15  # Increased for better context
        self.max_context_length = 500  # Maximum context to maintain
        
        # Sophisticated AI prompting system
        self.ENHANCED_TASK_PROMPT = """You are an expert AI assistant specialized in extracting actionable tasks from meeting transcripts.

CONTEXT: This is from a live meeting transcript. Extract ALL actionable tasks, assignments, and commitments.

INSTRUCTIONS:
1. Identify tasks that require action from someone
2. Extract assignee names (even if mentioned indirectly)
3. Parse any mentioned deadlines or timeframes
4. Determine priority based on urgency language
5. Detect task relationships and dependencies
6. Return ONLY valid JSON array

TASK CRITERIA:
- Must be actionable (not just discussion points)
- Should have clear ownership or assignment
- Include follow-ups, commitments, and action items
- Consider implicit assignments ("I'll handle that")

TEXT TO ANALYZE: "{text}"

CONTEXT (previous discussion): "{context}"

OUTPUT FORMAT (JSON array only):
[
  {{
    "title": "Clear, actionable task title",
    "assignee": "Person's name or null",
    "deadline": "Parsed deadline or null", 
    "priority": "low|medium|high",
    "confidence": 0.0-1.0,
    "description": "Brief task description",
    "tags": ["category", "type"],
    "estimated_effort": "time estimate or null",
    "urgency_indicators": ["urgent", "asap"],
    "dependencies": ["related task titles"],
    "context_clues": "Why this was identified as a task"
  }}
]

If no tasks found, return: []
"""
        
        # Enhanced task detection patterns
        self.task_keywords = [
            # Action verbs
            "fix", "update", "deploy", "implement", "create", "build", "test", "review",
            "handle", "work on", "take care of", "responsible for", "assigned to",
            "complete", "finish", "deliver", "prepare", "setup", "configure",
            "investigate", "research", "analyze", "document", "write", "design",
            
            # Commitment phrases
            "need to", "should", "must", "will", "going to", "have to", "ought to",
            "let me", "i'll", "we'll", "you'll", "they'll", "someone needs to",
            
            # Assignment indicators
            "assign", "delegate", "give to", "hand over", "pass to", "owner",
            "responsible", "accountable", "in charge of", "lead on",
            
            # Task indicators
            "todo", "task", "action item", "follow up", "next step", "deliverable"
        ]
        
        # Enhanced deadline patterns with natural language processing
        self.deadline_patterns = {
            # Immediate timeframes
            r'\b(right\s+now|immediately|asap|urgent)\b': 0,
            r'\b(today|this\s+afternoon|tonight|this\s+evening|end\s+of\s+day|eod)\b': 0,
            r'\b(by\s+end\s+of\s+day|by\s+eod|before\s+5)\b': 0,
            
            # Tomorrow and next day
            r'\b(tomorrow|by\s+tomorrow|tomorrow\s+morning)\b': 1,
            r'\b(next\s+business\s+day|first\s+thing\s+tomorrow)\b': 1,
            
            # This week
            r'\b(this\s+week|by\s+friday|end\s+of\s+week|eow)\b': self._days_until_friday,
            r'\b(by\s+the\s+end\s+of\s+the\s+week|before\s+weekend)\b': self._days_until_friday,
            
            # Next week
            r'\b(next\s+week|early\s+next\s+week|beginning\s+of\s+next\s+week)\b': self._days_until_next_monday,
            r'\b(by\s+next\s+friday|end\s+of\s+next\s+week)\b': self._days_until_next_friday,
            
            # Specific weekdays
            r'\b(by\s+)?monday\b': lambda: self._days_until_weekday(0),
            r'\b(by\s+)?tuesday\b': lambda: self._days_until_weekday(1),
            r'\b(by\s+)?wednesday\b': lambda: self._days_until_weekday(2),
            r'\b(by\s+)?thursday\b': lambda: self._days_until_weekday(3),
            r'\b(by\s+)?friday\b': lambda: self._days_until_weekday(4),
            r'\b(by\s+)?saturday\b': lambda: self._days_until_weekday(5),
            r'\b(by\s+)?sunday\b': lambda: self._days_until_weekday(6),
            
            # Longer timeframes
            r'\b(in\s+a\s+few\s+days|few\s+days)\b': 3,
            r'\b(next\s+month|by\s+month\s+end)\b': 30,
            r'\b(quarter\s+end|end\s+of\s+quarter)\b': 90,
        }
        
        # Priority indicators
        self.priority_indicators = {
            "high": [
                "urgent", "asap", "critical", "emergency", "immediately", "right now",
                "top priority", "high priority", "must have", "blocker", "blocking",
                "deadline", "due today", "overdue", "escalate"
            ],
            "low": [
                "eventually", "sometime", "when possible", "nice to have", "optional",
                "if time permits", "low priority", "backlog", "future", "someday"
            ]
        }
        
        # Task categories for tagging
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
    
    def get_groq(self) -> Groq:
        """Get or create Groq client with error handling."""
        if self.groq_client is None:
            try:
                self.groq_client = Groq(api_key=settings.groq_api_key)
                logger.info("Groq client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                raise
        return self.groq_client
    
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
        return TaskDetector._days_until_weekday(4)
    
    @staticmethod
    def _days_until_next_monday() -> int:
        """Calculate days until next Monday."""
        today = datetime.now().weekday()
        days_ahead = 7 - today  # Days until next Monday
        return days_ahead
    
    @staticmethod
    def _days_until_next_friday() -> int:
        """Calculate days until next Friday."""
        return TaskDetector._days_until_friday() + 7
    
    async def process_transcript_chunk(self, chunk: str) -> List[DetectedTask]:
        """
        Enhanced buffered processing for transcript chunks with context management.
        
        This is the main entry point for real-time transcription processing.
        Uses intelligent buffering to ensure complete context for accurate task detection.
        
        Args:
            chunk: New transcript chunk to process
            
        Returns:
            List of detected tasks (empty if buffering)
        """
        start_time = datetime.now()
        
        if not chunk or len(chunk.strip()) < 3:
            return []
        
        # Clean and add to buffer
        cleaned_chunk = self._clean_transcript_text(chunk)
        self.transcript_buffer += " " + cleaned_chunk
        
        # Maintain context buffer for better understanding
        self.context_buffer.append(cleaned_chunk)
        if len(self.context_buffer) > 10:  # Keep last 10 chunks as context
            self.context_buffer.pop(0)
        
        logger.debug(f"Chunk added to buffer: '{cleaned_chunk}'")
        logger.debug(f"Current buffer length: {len(self.transcript_buffer.split())} words")
        
        # Check if we have enough content for processing
        words = self.transcript_buffer.split()
        if len(words) >= self.buffer_word_threshold:
            logger.info(f"Processing buffer with {len(words)} words")
            
            # Build context from recent chunks
            context = " ".join(self.context_buffer[:-1]) if len(self.context_buffer) > 1 else ""
            
            # Process the buffered text with context
            tasks = await self.detect_tasks(self.transcript_buffer, context=context)
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_metrics.processing_time += processing_time
            self.processing_metrics.chunks_processed += 1
            self.processing_metrics.tasks_detected += len(tasks)
            
            # Clear buffer after processing but keep some overlap for context
            overlap_words = words[-5:] if len(words) > 5 else []
            self.transcript_buffer = " ".join(overlap_words)
            
            logger.info(f"Detected {len(tasks)} tasks in {processing_time:.2f}s")
            return tasks
        
        logger.debug(f"Buffering... ({len(words)}/{self.buffer_word_threshold} words)")
        return []
    
    async def flush_buffer(self) -> List[DetectedTask]:
        """
        Force process any remaining buffered text.
        Used when transcription ends to ensure no tasks are missed.
        """
        if not self.transcript_buffer.strip():
            return []
        
        logger.info(f"Flushing buffer: '{self.transcript_buffer}'")
        context = " ".join(self.context_buffer[:-1]) if len(self.context_buffer) > 1 else ""
        tasks = await self.detect_tasks(self.transcript_buffer, context=context)
        
        # Clear buffers
        self.transcript_buffer = ""
        self.context_buffer.clear()
        
        return tasks
    
    async def detect_tasks(self, text: str, context: str = "") -> List[DetectedTask]:
        """
        Enhanced task detection with sophisticated AI processing and validation.
        
        Args:
            text: The complete transcribed text to analyze
            context: Previous discussion context for better understanding
            
        Returns:
            List of validated and enriched detected tasks
        """
        if not text or len(text.strip()) < 10:
            return []
        
        logger.debug(f"Analyzing text: '{text[:100]}...'")
        
        # Check cache first for performance
        cache_key = self._generate_cache_key(text, context)
        if cache_key in self.task_cache:
            logger.debug("Cache hit for task detection")
            self.processing_metrics.cache_hits += 1
            return self.task_cache[cache_key]
        
        # Check for duplicates
        if self._is_duplicate_text(text):
            logger.debug("Duplicate text detected, skipping")
            return []
        
        # Primary AI-based detection
        tasks = await self._detect_tasks_with_ai(text, context)
        
        # Fallback to rule-based detection if AI fails or returns low confidence
        if not tasks or all(task.confidence < 0.5 for task in tasks):
            logger.info("AI detection failed or low confidence, trying rule-based fallback")
            rule_tasks = self._detect_tasks_with_rules(text)
            tasks.extend(rule_tasks)
        
        # Post-process and enrich tasks
        tasks = self._enrich_tasks(tasks, text, context)
        tasks = self._detect_task_relationships(tasks)
        tasks = self._deduplicate_tasks(tasks)
        tasks = self._validate_and_filter_tasks(tasks)
        
        # Cache results
        self.task_cache[cache_key] = tasks
        if len(self.task_cache) > 100:  # Limit cache size
            oldest_key = next(iter(self.task_cache))
            del self.task_cache[oldest_key]
        
        # Store for deduplication
        self.processed_texts.append(text.lower().strip())
        if len(self.processed_texts) > 50:
            self.processed_texts = self.processed_texts[-50:]
        
        logger.info(f"Final task detection result: {len(tasks)} tasks")
        return tasks
    
    async def _detect_tasks_with_ai(self, text: str, context: str = "") -> List[DetectedTask]:
        """
        Enhanced AI-based task detection with sophisticated prompting and error handling.
        """
        try:
            # Build enhanced prompt with context
            prompt = self.ENHANCED_TASK_PROMPT.format(
                text=text,
                context=context[:self.max_context_length] if context else "No previous context"
            )
            
            logger.debug("Calling Groq API for task detection")
            response = self.get_groq().chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent JSON
                max_tokens=1200,  # Increased for more detailed responses
                top_p=0.9
            )
            
            self.processing_metrics.api_calls_made += 1
            ai_response = response.choices[0].message.content.strip()
            
            logger.debug(f"AI response received: {len(ai_response)} characters")
            
            # Parse and validate JSON response
            tasks_data = self._parse_ai_response(ai_response)
            if not tasks_data:
                return []
            
            # Convert to DetectedTask objects
            tasks = []
            for task_data in tasks_data:
                if not self._is_valid_task_data(task_data):
                    continue
                
                task = self._create_task_from_ai_data(task_data, text)
                if task:
                    tasks.append(task)
            
            logger.info(f"AI detected {len(tasks)} tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"AI task detection failed: {e}")
            return []
    
    def _parse_ai_response(self, ai_response: str) -> List[Dict]:
        """Parse AI response and extract JSON array."""
        try:
            # Clean response - remove markdown if present
            cleaned_response = ai_response
            if "```json" in cleaned_response:
                json_start = cleaned_response.find("```json") + 7
                json_end = cleaned_response.find("```", json_start)
                cleaned_response = cleaned_response[json_start:json_end].strip()
            elif "```" in cleaned_response:
                json_start = cleaned_response.find("```") + 3
                json_end = cleaned_response.find("```", json_start)
                cleaned_response = cleaned_response[json_start:json_end].strip()
            
            # Handle case where LLM returns just the array
            if not cleaned_response.startswith('['):
                # Try to find JSON array in the response
                json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(0)
                else:
                    logger.warning("No JSON array found in AI response")
                    return []
            
            tasks_data = json.loads(cleaned_response)
            
            if not isinstance(tasks_data, list):
                logger.warning("AI response is not a list")
                return []
            
            return tasks_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            logger.debug(f"Raw response: '{ai_response}'")
            return []
    
    def _is_valid_task_data(self, task_data: Dict) -> bool:
        """Validate task data structure from AI response."""
        if not isinstance(task_data, dict):
            return False
        
        # Must have title
        if not task_data.get("title") or not isinstance(task_data["title"], str):
            return False
        
        # Validate confidence if present
        confidence = task_data.get("confidence", 0.8)
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            return False
        
        return True
    
    def _create_task_from_ai_data(self, task_data: Dict, source_text: str) -> Optional[DetectedTask]:
        """Create DetectedTask object from AI response data."""
        try:
            # Extract and validate deadline
            deadline_str = task_data.get("deadline", "")
            deadline_date, deadline_confidence = self._parse_deadline_enhanced(deadline_str)
            
            # Extract and normalize assignee
            assignee_str = task_data.get("assignee", "")
            assignee, assignee_confidence = self._normalize_assignee_enhanced(assignee_str)
            
            # Determine priority with confidence
            priority = self._determine_priority_enhanced(
                task_data.get("priority", "medium"),
                task_data.get("urgency_indicators", []),
                source_text
            )
            
            # Extract tags and categorize
            tags = task_data.get("tags", [])
            if not tags:
                tags = self._categorize_task(task_data["title"])
            
            # Calculate overall confidence
            base_confidence = float(task_data.get("confidence", 0.8))
            overall_confidence = self._calculate_enhanced_confidence(
                base_confidence, assignee_confidence, deadline_confidence, task_data
            )
            
            task = DetectedTask(
                id=str(uuid.uuid4()),
                title=task_data["title"][:100],  # Limit length
                assignee=assignee,
                deadline=deadline_date,
                description=task_data.get("description", task_data["title"]),
                priority=priority,
                confidence=overall_confidence,
                source_text=source_text,
                created_at=datetime.now().isoformat(),
                # Enhanced fields
                dependencies=task_data.get("dependencies", []),
                tags=tags,
                estimated_effort=task_data.get("estimated_effort"),
                urgency_indicators=task_data.get("urgency_indicators", []),
                assignee_confidence=assignee_confidence,
                deadline_confidence=deadline_confidence,
                context_window=task_data.get("context_clues", "")
            )
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task from AI data: {e}")
            return None
    
    def _detect_tasks_with_rules(self, text: str) -> List[DetectedTask]:
        """
        Enhanced rule-based task detection as fallback with improved pattern matching.
        """
        tasks = []
        text_lower = text.lower()
        
        # Split into sentences for analysis
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
            
            sentence_lower = sentence.lower()
            
            # Check if sentence contains task keywords
            has_task_keyword = any(keyword in sentence_lower for keyword in self.task_keywords)
            if not has_task_keyword:
                continue
            
            # Extract components
            assignee, assignee_confidence = self._extract_assignee_rules(sentence)
            deadline, deadline_confidence = self._extract_deadline_rules(sentence)
            priority = self._determine_priority_rules(sentence_lower)
            title = self._generate_title_rules(sentence)
            tags = self._categorize_task(sentence)
            
            # Calculate confidence
            confidence = self._calculate_rule_confidence(
                sentence_lower, assignee, deadline, has_task_keyword
            )
            
            if confidence >= 0.6:  # Threshold for rule-based detection
                task = DetectedTask(
                    id=str(uuid.uuid4()),
                    title=title,
                    assignee=assignee,
                    deadline=deadline,
                    description=sentence,
                    priority=priority,
                    confidence=confidence,
                    source_text=text,
                    created_at=datetime.now().isoformat(),
                    tags=tags,
                    assignee_confidence=assignee_confidence,
                    deadline_confidence=deadline_confidence
                )
                tasks.append(task)
        
        logger.info(f"Rule-based detection found {len(tasks)} tasks")
        return tasks
    
    def _extract_assignee_rules(self, sentence: str) -> Tuple[Optional[str], float]:
        """Enhanced assignee extraction with confidence scoring."""
        sentence_lower = sentence.lower()
        confidence = 0.0
        
        # Pattern: "Name will/should/needs to..."
        for participant in self.known_participants:
            patterns = [
                (rf'\b{participant}\s+(?:will|should|needs?\s+to|has\s+to|must)\b', 0.6),
                (rf'\b{participant}\s+(?:is\s+)?(?:responsible\s+for|assigned\s+to|handling)\b', 0.8),
                (rf'\b{participant}[,:]?\s+(?:fix|update|deploy|implement|create|build)\b', 0.7),
                (rf'\bassign\s+(?:this\s+)?to\s+{participant}\b', 0.9),
                (rf'\b{participant}\s+(?:can|will)\s+(?:handle|take\s+care\s+of)\b', 0.7)
            ]
            
            for pattern, conf in patterns:
                if re.search(pattern, sentence_lower):
                    return participant.title(), conf
        
        # Check aliases
        for alias, real_name in self.participant_aliases.items():
            if alias in sentence_lower and real_name in self.known_participants:
                confidence = 0.7  # Lower confidence for aliases
                return real_name.title(), confidence
        
        # Look for "I will" patterns (first person)
        if re.search(r'\bi\s+(?:will|\'ll|can|should)\b', sentence_lower):
            return "Speaker", 0.6  # Generic speaker reference
        
        return None, 0.0
    
    def _extract_deadline_rules(self, sentence: str) -> Tuple[Optional[str], float]:
        """Enhanced deadline extraction with confidence scoring."""
        sentence_lower = sentence.lower()
        
        for pattern, days_offset in self.deadline_patterns.items():
            match = re.search(pattern, sentence_lower)
            if match:
                try:
                    if callable(days_offset):
                        days_offset = days_offset()
                    
                    target_date = datetime.now() + timedelta(days=days_offset)
                    date_str = target_date.strftime("%Y-%m-%d")
                    
                    # Calculate confidence based on specificity
                    confidence = 0.9 if "by" in match.group(0) else 0.7
                    if "specific date" in pattern:  # More specific patterns
                        confidence = 0.95
                    
                    return date_str, confidence
                except Exception as e:
                    logger.warning(f"Error parsing deadline: {e}")
                    continue
        
        return None, 0.0
    
    def _normalize_assignee_enhanced(self, assignee: Optional[str]) -> Tuple[Optional[str], float]:
        """Enhanced assignee normalization with fuzzy matching and confidence."""
        if not assignee:
            return None, 0.0
        
        assignee_lower = assignee.lower().strip()
        confidence = 0.5  # Base confidence
        
        # Exact match with known participants
        for participant in self.known_participants:
            if participant == assignee_lower:
                return participant.title(), 0.95
        
        # Check aliases first (more specific)
        for alias, real_name in self.participant_aliases.items():
            if assignee_lower == alias:  # Exact alias match
                return real_name.title(), 0.8
        
        # Fuzzy matching with known participants
        best_match = None
        best_ratio = 0.0
        
        for participant in self.known_participants:
            ratio = SequenceMatcher(None, assignee_lower, participant).ratio()
            if ratio > best_ratio and ratio > 0.7:  # 70% similarity threshold
                best_ratio = ratio
                best_match = participant
        
        if best_match:
            confidence = 0.7 + (best_ratio - 0.7) * 0.2  # Scale to 0.7-0.9
            return best_match.title(), confidence
        
        # Check partial alias matches
        for alias, real_name in self.participant_aliases.items():
            if alias in assignee_lower or assignee_lower in alias:
                return real_name.title(), 0.6  # Lower confidence for partial matches
        
        # Return cleaned version if not in known list
        cleaned = assignee.strip().title()
        return cleaned, 0.5
    
    def _parse_deadline_enhanced(self, deadline_str: str) -> Tuple[Optional[str], float]:
        """Enhanced deadline parsing with natural language processing."""
        if not deadline_str:
            return None, 0.0
        
        deadline_lower = deadline_str.lower().strip()
        
        # Try pattern matching first
        for pattern, days_offset in self.deadline_patterns.items():
            if re.search(pattern.replace(r'\b', ''), deadline_lower):
                try:
                    if callable(days_offset):
                        days_offset = days_offset()
                    
                    target_date = datetime.now() + timedelta(days=days_offset)
                    date_str = target_date.strftime("%Y-%m-%d")
                    
                    # Higher confidence for more specific patterns
                    confidence = 0.9 if "by" in deadline_lower else 0.7
                    return date_str, confidence
                except Exception:
                    continue
        
        # Try to parse specific dates (e.g., "December 15", "12/15", "2024-12-15")
        date_patterns = [
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # MM/DD/YYYY
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\w+)\s+(\d{1,2}),?\s+(\d{4})?\b',  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, deadline_str)
            if match:
                try:
                    # This is a simplified parser - in production, use dateutil.parser
                    return deadline_str, 0.8  # Return original for now
                except Exception:
                    continue
        
        return None, 0.0
    
    def _determine_priority_enhanced(self, ai_priority: str, urgency_indicators: List[str], text: str) -> str:
        """Enhanced priority determination using multiple factors."""
        text_lower = text.lower()
        
        # Start with AI suggestion
        priority = ai_priority.lower() if ai_priority in ["low", "medium", "high"] else "medium"
        
        # Check urgency indicators from AI
        if urgency_indicators:
            high_urgency = any(indicator.lower() in self.priority_indicators["high"] 
                             for indicator in urgency_indicators)
            if high_urgency:
                priority = "high"
        
        # Check text for priority indicators
        if any(word in text_lower for word in self.priority_indicators["high"]):
            priority = "high"
        elif any(word in text_lower for word in self.priority_indicators["low"]):
            priority = "low"
        
        return priority
    
    def _determine_priority_rules(self, sentence_lower: str) -> str:
        """Determine task priority from sentence using rules."""
        if any(word in sentence_lower for word in self.priority_indicators["high"]):
            return "high"
        elif any(word in sentence_lower for word in self.priority_indicators["low"]):
            return "low"
        else:
            return "medium"
    
    def _generate_title_rules(self, sentence: str) -> str:
        """Generate a clean title from sentence using rules."""
        # Remove common prefixes
        sentence = re.sub(r'^(we need to|we should|let\'s|i think we should)\s+', '', sentence, flags=re.IGNORECASE)
        sentence = re.sub(r'^(someone needs to|somebody should)\s+', '', sentence, flags=re.IGNORECASE)
        
        # Remove assignee mentions at the beginning
        for participant in self.known_participants:
            sentence = re.sub(rf'^{participant}\s+(will|should|needs?\s+to|has\s+to|must)\s+', '', sentence, flags=re.IGNORECASE)
        
        # Capitalize first letter and limit length
        sentence = sentence.strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
        
        return sentence[:80]
    
    def _categorize_task(self, title: str) -> List[str]:
        """Categorize task based on title content."""
        title_lower = title.lower()
        tags = []
        
        for category, keywords in self.task_categories.items():
            if any(keyword in title_lower for keyword in keywords):
                tags.append(category)
        
        # Add default tag if no category found
        if not tags:
            tags.append("general")
        
        return tags
    
    def _calculate_enhanced_confidence(self, base_confidence: float, assignee_confidence: float, 
                                     deadline_confidence: float, task_data: Dict) -> float:
        """Calculate overall confidence using multiple validation factors."""
        # Start with base AI confidence
        confidence = base_confidence
        
        # Boost for assignee presence and confidence
        if assignee_confidence > 0:
            confidence += 0.05 * assignee_confidence  # Reduced boost
        
        # Boost for deadline presence and confidence
        if deadline_confidence > 0:
            confidence += 0.03 * deadline_confidence  # Reduced boost
        
        # Boost for additional context
        if task_data.get("context_clues"):
            confidence += 0.02  # Reduced boost
        
        # Boost for urgency indicators
        if task_data.get("urgency_indicators"):
            confidence += 0.02  # Reduced boost
        
        # Boost for estimated effort (shows thoughtfulness)
        if task_data.get("estimated_effort"):
            confidence += 0.01  # Reduced boost
        
        return min(confidence, 1.0)
    
    def _calculate_rule_confidence(self, sentence_lower: str, assignee: Optional[str], 
                                 deadline: Optional[str], has_task_keyword: bool) -> float:
        """Calculate confidence score for rule-based detection."""
        confidence = 0.6  # Base confidence
        
        # Boost for clear task keywords
        strong_keywords = ["fix", "implement", "deploy", "create", "build", "update"]
        if any(keyword in sentence_lower for keyword in strong_keywords):
            confidence += 0.1
        
        # Boost for assignee
        if assignee:
            confidence += 0.15
        
        # Boost for deadline
        if deadline:
            confidence += 0.1
        
        # Boost for imperative language
        if any(word in sentence_lower for word in ["must", "need to", "should", "will"]):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _enrich_tasks(self, tasks: List[DetectedTask], text: str, context: str) -> List[DetectedTask]:
        """Enrich tasks with additional context and metadata."""
        for task in tasks:
            # Add context window (surrounding text)
            task.context_window = self._extract_context_window(task.source_text, text)
            
            # Estimate effort based on task complexity
            if not task.estimated_effort:
                task.estimated_effort = self._estimate_task_effort(task.title, task.description)
            
            # Add more specific tags based on content analysis
            additional_tags = self._analyze_task_content(task.title + " " + task.description)
            task.tags.extend(tag for tag in additional_tags if tag not in task.tags)
        
        return tasks
    
    def _extract_context_window(self, source_text: str, full_text: str) -> str:
        """Extract surrounding context for better task understanding."""
        # Find the position of source text in full text
        try:
            start_pos = full_text.lower().find(source_text.lower())
            if start_pos == -1:
                return source_text[:100]  # Fallback
            
            # Extract context window (50 chars before and after)
            context_start = max(0, start_pos - 50)
            context_end = min(len(full_text), start_pos + len(source_text) + 50)
            
            return full_text[context_start:context_end]
        except Exception:
            return source_text[:100]
    
    def _estimate_task_effort(self, title: str, description: str) -> str:
        """Estimate task effort based on complexity indicators."""
        text = (title + " " + description).lower()
        
        # Simple heuristics for effort estimation
        if any(word in text for word in ["quick", "simple", "easy", "minor"]):
            return "1-2 hours"
        elif any(word in text for word in ["complex", "major", "redesign", "refactor"]):
            return "1-2 days"
        elif any(word in text for word in ["implement", "build", "create", "develop"]):
            return "4-8 hours"
        else:
            return "2-4 hours"  # Default estimate
    
    def _analyze_task_content(self, content: str) -> List[str]:
        """Analyze task content for additional categorization."""
        content_lower = content.lower()
        additional_tags = []
        
        # Technical tags
        if any(word in content_lower for word in ["bug", "fix", "error", "issue"]):
            additional_tags.append("bugfix")
        
        if any(word in content_lower for word in ["feature", "new", "add"]):
            additional_tags.append("feature")
        
        if any(word in content_lower for word in ["security", "auth", "permission"]):
            additional_tags.append("security")
        
        if any(word in content_lower for word in ["performance", "optimize", "speed"]):
            additional_tags.append("performance")
        
        return additional_tags
    
    def _detect_task_relationships(self, tasks: List[DetectedTask]) -> List[DetectedTask]:
        """Detect relationships and dependencies between tasks."""
        relationships = []
        
        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                
                # Check for dependency keywords
                relationship = self._analyze_task_relationship(task1, task2)
                if relationship:
                    relationships.append(relationship)
                    
                    # Add dependency to task
                    if relationship.relationship_type == "depends_on":
                        if relationship.parent_task_id == task1.id:
                            task1.dependencies.append(task2.id)
                        else:
                            task2.dependencies.append(task1.id)
        
        return tasks
    
    def _analyze_task_relationship(self, task1: DetectedTask, task2: DetectedTask) -> Optional[TaskRelationship]:
        """Analyze relationship between two tasks."""
        # Simple heuristics for relationship detection
        title1_lower = task1.title.lower()
        title2_lower = task2.title.lower()
        
        # Check for sequential dependencies
        if "before" in title1_lower and any(word in title2_lower for word in title1_lower.split()):
            return TaskRelationship(
                parent_task_id=task2.id,
                child_task_id=task1.id,
                relationship_type="depends_on",
                confidence=0.7
            )
        
        # Check for blocking relationships
        if "after" in title1_lower and any(word in title2_lower for word in title1_lower.split()):
            return TaskRelationship(
                parent_task_id=task1.id,
                child_task_id=task2.id,
                relationship_type="blocks",
                confidence=0.7
            )
        
        return None
    
    def _deduplicate_tasks(self, tasks: List[DetectedTask]) -> List[DetectedTask]:
        """Enhanced task deduplication with similarity detection."""
        if not tasks:
            return []
        
        unique_tasks = []
        
        for task in tasks:
            is_duplicate = False
            
            for existing_task in unique_tasks:
                # Check title similarity
                title_similarity = SequenceMatcher(None, task.title.lower(), existing_task.title.lower()).ratio()
                
                # Check assignee and deadline similarity
                assignee_match = task.assignee == existing_task.assignee
                deadline_match = task.deadline == existing_task.deadline
                
                # Consider duplicate if high title similarity and same assignee/deadline
                if title_similarity > 0.8 or (title_similarity > 0.6 and assignee_match and deadline_match):
                    # Keep the one with higher confidence
                    if task.confidence > existing_task.confidence:
                        unique_tasks.remove(existing_task)
                        unique_tasks.append(task)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_tasks.append(task)
        
        logger.info(f"Deduplication: {len(tasks)} -> {len(unique_tasks)} tasks")
        return unique_tasks
    
    def _validate_and_filter_tasks(self, tasks: List[DetectedTask]) -> List[DetectedTask]:
        """Validate and filter tasks based on quality criteria."""
        valid_tasks = []
        
        for task in tasks:
            # Basic validation
            if not task.title or len(task.title.strip()) < 3:
                logger.debug(f"Rejected task: title too short '{task.title}'")
                continue
            
            # Confidence threshold
            if task.confidence < 0.5:
                logger.debug(f"Rejected task: confidence too low {task.confidence}")
                continue
            
            # Check for meaningful content
            if self._is_meaningful_task(task):
                valid_tasks.append(task)
            else:
                logger.debug(f"Rejected task: not meaningful '{task.title}'")
        
        logger.info(f"Validation: {len(tasks)} -> {len(valid_tasks)} tasks")
        return valid_tasks
    
    def _is_meaningful_task(self, task: DetectedTask) -> bool:
        """Check if task represents a meaningful actionable item."""
        title_lower = task.title.lower()
        
        # Reject vague or non-actionable titles
        vague_patterns = [
            r'^(ok|okay|yes|no|sure|right|good)$',
            r'^(um|uh|well|so)$',
            r'^(thanks|thank you)$',
            r'^(i think|maybe|perhaps)$'
        ]
        
        for pattern in vague_patterns:
            if re.match(pattern, title_lower):
                return False
        
        # Must contain at least one action word
        action_words = ["fix", "update", "create", "build", "implement", "deploy", "test", "review", "handle", "complete"]
        if not any(word in title_lower for word in action_words):
            # Check if it's a commitment phrase
            commitment_phrases = ["will", "going to", "need to", "should", "must"]
            if not any(phrase in title_lower for phrase in commitment_phrases):
                return False
        
        return True
    
    def _clean_transcript_text(self, text: str) -> str:
        """Clean transcript text for better processing."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common transcription artifacts
        text = re.sub(r'\b(um|uh|er|ah)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[.*?\]', '', text)  # Remove bracketed content
        text = re.sub(r'\(.*?\)', '', text)  # Remove parenthetical content
        
        # Clean up punctuation
        text = re.sub(r'[,]{2,}', ',', text)
        text = re.sub(r'[.]{2,}', '.', text)
        
        return text.strip()
    
    def _generate_cache_key(self, text: str, context: str) -> str:
        """Generate cache key for text and context."""
        combined = f"{text}|{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _is_duplicate_text(self, text: str) -> bool:
        """Enhanced duplicate detection with similarity checking."""
        text_lower = text.lower().strip()
        
        for processed_text in self.processed_texts[-10:]:  # Check last 10 texts
            similarity = SequenceMatcher(None, text_lower, processed_text).ratio()
            if similarity > 0.85:  # 85% similarity threshold
                return True
        
        return False
    
    # Public utility methods for external use
    
    def clear_history(self):
        """Clear processed texts history and cache."""
        self.processed_texts.clear()
        self.task_cache.clear()
        self.context_buffer.clear()
        self.transcript_buffer = ""
        logger.info("Task detector history cleared")
    
    def add_participant(self, name: str):
        """Add a new participant to the known list."""
        if name and name.lower() not in self.known_participants:
            self.known_participants.append(name.lower())
            logger.info(f"Added participant: {name}")
    
    def add_participant_alias(self, alias: str, real_name: str):
        """Add a participant alias for better name matching."""
        if alias and real_name:
            self.participant_aliases[alias.lower()] = real_name.lower()
            logger.info(f"Added alias: {alias} -> {real_name}")
    
    def get_participants(self) -> List[str]:
        """Get list of known participants."""
        return [p.title() for p in self.known_participants]
    
    def get_processing_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics."""
        return self.processing_metrics
    
    def reset_metrics(self):
        """Reset processing metrics."""
        self.processing_metrics = ProcessingMetrics()
        logger.info("Processing metrics reset")
    
    def update_configuration(self, config: Dict):
        """Update detector configuration dynamically."""
        if "buffer_word_threshold" in config:
            self.buffer_word_threshold = max(5, min(50, config["buffer_word_threshold"]))
        
        if "max_context_length" in config:
            self.max_context_length = max(100, min(1000, config["max_context_length"]))
        
        if "confidence_threshold" in config:
            # This would be used in validation if we stored it as instance variable
            pass
        
        logger.info(f"Configuration updated: {config}")
    
    def get_task_statistics(self) -> Dict:
        """Get statistics about detected tasks."""
        metrics = self.processing_metrics
        
        avg_confidence = (
            sum(metrics.confidence_scores) / len(metrics.confidence_scores)
            if metrics.confidence_scores else 0.0
        )
        
        return {
            "total_chunks_processed": metrics.chunks_processed,
            "total_tasks_detected": metrics.tasks_detected,
            "average_confidence": round(avg_confidence, 2),
            "total_processing_time": round(metrics.processing_time, 2),
            "api_calls_made": metrics.api_calls_made,
            "cache_hits": metrics.cache_hits,
            "cache_hit_rate": (
                round(metrics.cache_hits / max(1, metrics.api_calls_made + metrics.cache_hits), 2)
            )
        }
    
    async def validate_task_quality(self, tasks: List[DetectedTask]) -> Dict:
        """Validate the quality of detected tasks and provide feedback."""
        if not tasks:
            return {"quality_score": 0.0, "issues": ["No tasks detected"]}
        
        issues = []
        quality_factors = []
        
        for task in tasks:
            # Check confidence
            if task.confidence < 0.7:
                issues.append(f"Low confidence task: '{task.title}' ({task.confidence:.2f})")
            quality_factors.append(task.confidence)
            
            # Check assignee
            if not task.assignee:
                issues.append(f"No assignee for task: '{task.title}'")
            else:
                quality_factors.append(0.8)  # Bonus for having assignee
            
            # Check deadline
            if not task.deadline:
                issues.append(f"No deadline for task: '{task.title}'")
            else:
                quality_factors.append(0.8)  # Bonus for having deadline
        
        avg_quality = sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
        
        return {
            "quality_score": round(avg_quality, 2),
            "total_tasks": len(tasks),
            "issues": issues[:5],  # Limit to top 5 issues
            "recommendations": self._generate_quality_recommendations(tasks, issues)
        }
    
    def _generate_quality_recommendations(self, tasks: List[DetectedTask], issues: List[str]) -> List[str]:
        """Generate recommendations for improving task detection quality."""
        recommendations = []
        
        if len([t for t in tasks if not t.assignee]) > len(tasks) * 0.5:
            recommendations.append("Consider mentioning specific names when assigning tasks")
        
        if len([t for t in tasks if not t.deadline]) > len(tasks) * 0.5:
            recommendations.append("Include timeframes or deadlines when discussing tasks")
        
        if len([t for t in tasks if t.confidence < 0.7]) > len(tasks) * 0.3:
            recommendations.append("Use more explicit task language (e.g., 'John will fix the bug by Friday')")
        
        if not recommendations:
            recommendations.append("Task detection quality looks good!")
        
        return recommendations