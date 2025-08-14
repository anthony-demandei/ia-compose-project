"""
Question Generation Engine for the new 4-API workflow.
Uses AI to generate dynamic questions with 70% multiple choice guaranteed coverage.
Combines mandatory standardized questions with AI-generated contextual questions.
"""

import logging
from typing import List, Dict, Any, Optional

from app.models.api_models import Question, QuestionChoice
from app.services.ai_question_agent import AIQuestionAgent
from app.services.question_templates import QuestionTemplates
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class QuestionEngine:
    """
    Hybrid Engine for question generation.
    STRATEGY: 70% Multiple Choice (Mandatory + Templates) + 30% AI Open Questions
    
    Ensures comprehensive coverage while maintaining contextual relevance.
    """
    
    def __init__(self):
        """Initialize the question engine with AI agent and templates."""
        self.ai_agent = AIQuestionAgent()
        self.templates = QuestionTemplates()
        logger.info("Question Engine initialized with AI agent + standardized templates")
        
    async def generate_questions_for_project(
        self, 
        project_description: str, 
        max_questions: int = 8
    ) -> List[Question]:
        """
        ESTRATÉGIA HÍBRIDA: Generate questions with guaranteed 70% multiple choice coverage.
        
        COMPOSITION:
        - 4 Mandatory Coverage Questions (50%): Devices, Peripherals, Fiscal, Integrations
        - 2 Domain-Specific Questions (25%): Based on detected industry
        - 2 AI-Generated Open Questions (25%): Contextual insights
        
        Args:
            project_description: Description of the project
            max_questions: Target number of questions (minimum 6 for 70% ratio)
            
        Returns:
            List of hybrid questions (standardized + AI-generated)
        """
        logger.info(f"🎯 HYBRID STRATEGY: Generating {max_questions} questions (70% multiple choice guaranteed)")
        
        # Validate input
        if not project_description or len(project_description.strip()) < 20:
            logger.error("Project description too short for analysis")
            return []
        
        # Ensure minimum for 70% ratio
        total_questions = max(max_questions, 6)
        
        try:
            # STEP 1: Get standardized questions with quota enforcement
            standardized_questions = self.templates.get_contextual_questions(
                project_description=project_description,
                total_questions=total_questions  # Use full target to allow quota enforcement
            )
            
            logger.info(f"📋 Generated {len(standardized_questions)} standardized questions (multiple choice)")
            
            # STEP 2: Convert template format to Question objects
            questions = []
            for i, template_q in enumerate(standardized_questions):
                choices = [
                    QuestionChoice(
                        id=choice["id"],
                        text=choice["text"],
                        description=choice.get("description", "")
                    )
                    for choice in template_q["choices"]
                ]
                
                question = Question(
                    code=template_q["code"],
                    text=template_q["text"],
                    why_it_matters=template_q["why_it_matters"],
                    choices=choices,
                    required=template_q["required"],
                    allow_multiple=template_q["allow_multiple"],
                    category=template_q["category"]
                )
                questions.append(question)
            
            # STEP 3: Add AI-generated open questions if needed
            remaining_questions = total_questions - len(questions)
            if remaining_questions > 0:
                logger.info(f"🤖 Generating {remaining_questions} AI open questions for context")
                
                ai_questions = await self.ai_agent.generate_questions(
                    project_description=project_description,
                    num_questions=remaining_questions,
                    exclude_covered_topics=self._get_covered_topics(standardized_questions)
                )
                
                # Add AI questions with proper codes
                for i, ai_q in enumerate(ai_questions):
                    ai_q.code = f"Q{len(questions) + i + 1:03d}"
                
                questions.extend(ai_questions)
            
            # STEP 4: Calculate and log the multiple choice ratio
            mc_questions = len([q for q in questions if q.choices and len(q.choices) > 1])
            mc_ratio = (mc_questions / len(questions)) * 100 if questions else 0
            
            logger.info(f"✅ FINAL COMPOSITION: {len(questions)} questions, {mc_questions} multiple choice ({mc_ratio:.1f}%)")
            
            if mc_ratio < 70:
                logger.warning(f"⚠️ Multiple choice ratio below target: {mc_ratio:.1f}% < 70%")
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate hybrid questions: {e}")
            # Fallback: try pure AI generation
            logger.info("🔄 Falling back to pure AI generation")
            try:
                return await self.ai_agent.generate_questions(
                    project_description=project_description,
                    num_questions=total_questions
                )
            except Exception as fallback_e:
                logger.error(f"Fallback also failed: {fallback_e}")
                return []
    
    def _get_covered_topics(self, standardized_questions: List[Dict]) -> List[str]:
        """Extract topics already covered by standardized questions to avoid duplication."""
        covered_topics = []
        for q in standardized_questions:
            question_text = q["text"].lower()
            if "dispositivo" in question_text or "plataforma" in question_text:
                covered_topics.append("platforms_devices")
            elif "periférico" in question_text or "integração" in question_text:
                covered_topics.append("integrations_peripherals")
            elif "fiscal" in question_text or "regulament" in question_text:
                covered_topics.append("compliance_regulations")
        
        return covered_topics
    
    async def generate_follow_up_questions(
        self, 
        previous_answers: List[Dict], 
        session_context: Dict
    ) -> List[Question]:
        """
        Generate follow-up questions based on previous answers.
        
        Args:
            previous_answers: List of previous question answers
            session_context: Current session context with project info
            
        Returns:
            List of follow-up questions
        """
        logger.info("Generating follow-up questions based on context")
        
        # Extract project description from context
        project_description = session_context.get("project_description", "")
        
        if not project_description:
            logger.error("No project description in session context")
            return []
        
        try:
            # Generate contextual follow-up questions
            questions = await self.ai_agent.generate_followup_questions(
                project_description=project_description,
                previous_answers=previous_answers,
                num_questions=3  # Fewer questions for follow-ups
            )
            
            logger.info(f"Generated {len(questions)} follow-up questions")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate follow-up questions: {e}")
            return []