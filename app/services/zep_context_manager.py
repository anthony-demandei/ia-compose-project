"""
Zep Context Manager - Manages project memory and context using Zep.

Zep helps us:
- Remember similar projects
- Learn from past interactions
- Improve question relevance over time
- Provide contextual insights
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Check if Zep is available
try:
    from zep_python import ZepClient
    ZEP_AVAILABLE = True
except ImportError:
    logger.warning("Zep SDK not installed. Install with: pip install zep-python")
    ZEP_AVAILABLE = False


@dataclass
class ProjectMemory:
    """Memory of a project interaction."""
    
    session_id: str
    project_description: str
    questions_asked: List[Dict]
    answers_received: List[Dict]
    project_type: str
    complexity: str
    timestamp: str
    success_metrics: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class ZepContextManager:
    """
    Manages project context and memory using Zep.
    
    Features:
    - Store project interactions
    - Retrieve similar project contexts
    - Learn patterns from successful projects
    - Provide insights for better questions
    """
    
    def __init__(self, zep_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Zep context manager.
        
        Args:
            zep_url: Zep server URL (uses env var if not provided)
            api_key: Zep API key (uses env var if not provided)
        """
        self.enabled = False
        self.local_memory = []  # Always initialize fallback
        
        # Check if Zep is enabled
        enable_zep = os.getenv("ENABLE_ZEP_MEMORY", "false").lower() == "true"
        
        if not enable_zep:
            logger.info("📝 Zep memory disabled - using local fallback only")
            return
        
        if not ZEP_AVAILABLE:
            logger.warning("⚠️ Zep SDK not available - install with: pip install zep-python")
            logger.info("📝 Using local memory fallback")
            return
        
        # Get configuration from environment
        zep_url = zep_url or os.getenv("ZEP_URL")
        api_key = api_key or os.getenv("ZEP_API_KEY")
        self.project_id = os.getenv("ZEP_PROJECT_ID", "demandei_ia_compose")
        self.similarity_threshold = float(os.getenv("ZEP_SIMILARITY_THRESHOLD", "0.7"))
        self.max_memory_items = int(os.getenv("ZEP_MAX_MEMORY_ITEMS", "100"))
        
        if not zep_url or not api_key:
            logger.warning("⚠️ Zep URL or API key not configured")
            logger.info("📝 Using local memory fallback")
            return
        
        try:
            # Initialize Zep client
            self.client = ZepClient(base_url=zep_url, api_key=api_key)
            self.enabled = True
            logger.info(f"✅ Zep context manager initialized: {zep_url}")
            logger.info(f"🎯 Project: {self.project_id}, Threshold: {self.similarity_threshold}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Zep client: {e}")
            logger.info("📝 Using local memory fallback")
    
    async def store_project_interaction(
        self,
        session_id: str,
        project_description: str,
        questions: List[Dict],
        project_classification: Dict
    ) -> bool:
        """
        Store a project interaction in memory.
        
        Args:
            session_id: Unique session identifier
            project_description: Original project description
            questions: Questions generated for the project
            project_classification: AI classification of the project
            
        Returns:
            True if stored successfully
        """
        try:
            memory = ProjectMemory(
                session_id=session_id,
                project_description=project_description,
                questions_asked=questions,
                answers_received=[],  # Will be updated as answers come in
                project_type=project_classification.get("type", "unknown"),
                complexity=project_classification.get("complexity", "moderate"),
                timestamp=datetime.now().isoformat()
            )
            
            if self.enabled and ZEP_AVAILABLE:
                # Store in Zep
                await self._store_in_zep(memory)
            else:
                # Store locally
                self.local_memory.append(memory.to_dict())
            
            logger.info(f"Stored project interaction for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store project interaction: {e}")
            return False
    
    async def get_similar_projects(
        self,
        project_description: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Retrieve similar projects from memory.
        
        Args:
            project_description: Description to search for
            limit: Maximum number of similar projects
            
        Returns:
            List of similar project contexts
        """
        logger.info(f"🔍 Searching for similar projects", extra={
            "description_length": len(project_description),
            "limit": limit,
            "zep_enabled": self.enabled
        })
        
        try:
            if self.enabled and ZEP_AVAILABLE:
                # Search in Zep
                similar = await self._search_zep(project_description, limit)
                logger.info(f"📋 Found {len(similar)} similar projects in Zep")
                return similar
            else:
                # Search locally
                similar = self._search_local(project_description, limit)
                logger.info(f"📋 Found {len(similar)} similar projects locally")
                return similar
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve similar projects: {e}")
            return []
    
    async def update_with_answers(
        self,
        session_id: str,
        answers: List[Dict]
    ) -> bool:
        """
        Update a session with user answers.
        
        Args:
            session_id: Session to update
            answers: User's answers to questions
            
        Returns:
            True if updated successfully
        """
        try:
            if self.enabled and ZEP_AVAILABLE:
                # Update in Zep
                await self._update_zep_session(session_id, answers)
            else:
                # Update locally
                for memory in self.local_memory:
                    if memory.get("session_id") == session_id:
                        memory["answers_received"] = answers
                        break
            
            logger.info(f"Updated session {session_id} with answers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session with answers: {e}")
            return False
    
    async def get_insights_for_project(
        self,
        project_description: str
    ) -> Dict[str, Any]:
        """
        Get insights based on similar projects.
        
        Args:
            project_description: Project to analyze
            
        Returns:
            Dict with insights and recommendations
        """
        insights = {
            "similar_projects_found": 0,
            "common_questions": [],
            "typical_complexity": "moderate",
            "success_patterns": [],
            "recommendations": []
        }
        
        try:
            # Get similar projects
            similar = await self.get_similar_projects(project_description)
            insights["similar_projects_found"] = len(similar)
            
            if similar:
                # Analyze patterns
                complexities = [p.get("complexity", "moderate") for p in similar]
                insights["typical_complexity"] = max(set(complexities), key=complexities.count)
                
                # Find common questions
                all_questions = []
                for project in similar:
                    questions = project.get("questions_asked", [])
                    all_questions.extend([q.get("text", "") for q in questions])
                
                # Get most common question themes
                if all_questions:
                    # Simple frequency analysis
                    insights["common_questions"] = list(set(all_questions))[:5]
                
                # Add recommendations
                insights["recommendations"] = [
                    "Consider asking about integration requirements",
                    "Clarify performance expectations early",
                    "Understand maintenance and support needs"
                ]
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return insights
    
    # Private methods for Zep integration
    
    async def _store_in_zep(self, memory: ProjectMemory):
        """Store memory in Zep."""
        if not self.enabled:
            return
        
        try:
            # Create or get user
            user_id = f"project_{memory.project_type}"
            
            # Create session
            session = {
                "session_id": memory.session_id,
                "user_id": user_id,
                "metadata": {
                    "project_type": memory.project_type,
                    "complexity": memory.complexity,
                    "timestamp": memory.timestamp
                }
            }
            
            # Add messages
            messages = [
                {
                    "role": "user",
                    "content": memory.project_description,
                    "metadata": {"type": "project_description"}
                },
                {
                    "role": "assistant",
                    "content": json.dumps(memory.questions_asked),
                    "metadata": {"type": "generated_questions"}
                }
            ]
            
            # Store in Zep
            await self.client.memory.add_memory(
                session_id=memory.session_id,
                messages=messages,
                metadata=session["metadata"]
            )
            
        except Exception as e:
            logger.error(f"Failed to store in Zep: {e}")
    
    async def _search_zep(self, description: str, limit: int) -> List[Dict]:
        """Search for similar projects in Zep."""
        if not self.enabled:
            return []
        
        try:
            # Search for similar content
            results = await self.client.memory.search_memory(
                query=description,
                limit=limit
            )
            
            # Convert results to our format
            similar_projects = []
            for result in results:
                project = {
                    "session_id": result.session_id,
                    "project_description": result.messages[0].content if result.messages else "",
                    "questions_asked": json.loads(result.messages[1].content) if len(result.messages) > 1 else [],
                    "project_type": result.metadata.get("project_type", "unknown"),
                    "complexity": result.metadata.get("complexity", "moderate")
                }
                similar_projects.append(project)
            
            return similar_projects
            
        except Exception as e:
            logger.error(f"Failed to search Zep: {e}")
            return []
    
    async def _update_zep_session(self, session_id: str, answers: List[Dict]):
        """Update a Zep session with answers."""
        if not self.enabled:
            return
        
        try:
            # Add answer as a new message
            message = {
                "role": "user",
                "content": json.dumps(answers),
                "metadata": {"type": "user_answers"}
            }
            
            await self.client.memory.add_memory(
                session_id=session_id,
                messages=[message]
            )
            
        except Exception as e:
            logger.error(f"Failed to update Zep session: {e}")
    
    def _search_local(self, description: str, limit: int) -> List[Dict]:
        """Simple local search fallback."""
        if not hasattr(self, 'local_memory'):
            return []
        
        # Very simple keyword matching
        description_lower = description.lower()
        scored_projects = []
        
        for project in self.local_memory:
            project_desc = project.get("project_description", "").lower()
            
            # Count common words (very basic similarity)
            common_words = len(set(description_lower.split()) & set(project_desc.split()))
            
            if common_words > 0:
                scored_projects.append((common_words, project))
        
        # Sort by score and return top matches
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        return [project for _, project in scored_projects[:limit]]