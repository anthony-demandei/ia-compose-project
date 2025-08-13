"""
Question Generation Engine for the new 4-API workflow.
Generates dynamic multiple choice questions based on project analysis.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.api_models import Question, QuestionChoice
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class QuestionEngine:
    """Engine for dynamic question generation with multiple choice format."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the question engine.
        
        Args:
            openai_api_key: OpenAI API key for AI-powered question generation
        """
        self.openai_api_key = openai_api_key
        self.question_templates = self._load_question_templates()
        
    def _load_question_templates(self) -> Dict[str, List[Dict]]:
        """
        Load predefined question templates organized by category.
        
        Returns:
            Dict containing question templates by category
        """
        return {
            "business": [
                {
                    "template": "Qual o tipo principal do seu projeto?",
                    "choices": [
                        {"id": "web_app", "text": "Aplicação Web"},
                        {"id": "mobile_app", "text": "Aplicativo Mobile"},
                        {"id": "desktop_app", "text": "Software Desktop"},
                        {"id": "api_service", "text": "API/Microserviço"},
                        {"id": "ecommerce", "text": "E-commerce"},
                        {"id": "cms", "text": "Sistema de Gestão de Conteúdo"},
                        {"id": "erp", "text": "Sistema ERP"},
                        {"id": "crm", "text": "Sistema CRM"},
                        {"id": "other", "text": "Outro tipo"}
                    ],
                    "category": "business",
                    "keywords": ["tipo", "projeto", "sistema", "aplicação"]
                },
                {
                    "template": "Qual o tamanho da sua empresa/organização?",
                    "choices": [
                        {"id": "startup", "text": "Startup (1-10 pessoas)"},
                        {"id": "small", "text": "Pequena empresa (11-50 pessoas)"},
                        {"id": "medium", "text": "Média empresa (51-250 pessoas)"},
                        {"id": "large", "text": "Grande empresa (250+ pessoas)"},
                        {"id": "enterprise", "text": "Corporação/Enterprise"},
                        {"id": "personal", "text": "Projeto pessoal"}
                    ],
                    "category": "business",
                    "keywords": ["empresa", "organização", "tamanho", "equipe"]
                },
                {
                    "template": "Qual o orçamento estimado para o projeto?",
                    "choices": [
                        {"id": "micro", "text": "Até R$ 10.000"},
                        {"id": "small", "text": "R$ 10.000 - R$ 50.000"},
                        {"id": "medium", "text": "R$ 50.000 - R$ 200.000"},
                        {"id": "large", "text": "R$ 200.000 - R$ 500.000"},
                        {"id": "enterprise", "text": "Acima de R$ 500.000"},
                        {"id": "not_defined", "text": "Ainda não definido"}
                    ],
                    "category": "business",
                    "keywords": ["orçamento", "investimento", "custo", "valor"]
                }
            ],
            "technical": [
                {
                    "template": "Qual o tamanho estimado da equipe de desenvolvimento?",
                    "choices": [
                        {"id": "solo", "text": "1 desenvolvedor"},
                        {"id": "small", "text": "2-5 desenvolvedores"},
                        {"id": "medium", "text": "6-15 desenvolvedores"},
                        {"id": "large", "text": "16+ desenvolvedores"},
                        {"id": "outsourced", "text": "Equipe terceirizada"}
                    ],
                    "category": "technical",
                    "keywords": ["equipe", "desenvolvedores", "time", "recursos"]
                },
                {
                    "template": "Quais tecnologias você tem preferência ou restrições?",
                    "choices": [
                        {"id": "react", "text": "React/Next.js"},
                        {"id": "vue", "text": "Vue.js/Nuxt.js"},
                        {"id": "angular", "text": "Angular"},
                        {"id": "python", "text": "Python (Django/FastAPI)"},
                        {"id": "nodejs", "text": "Node.js"},
                        {"id": "dotnet", "text": ".NET"},
                        {"id": "java", "text": "Java/Spring"},
                        {"id": "php", "text": "PHP (Laravel/Symfony)"},
                        {"id": "no_preference", "text": "Sem preferência"}
                    ],
                    "category": "technical",
                    "keywords": ["tecnologia", "linguagem", "framework", "stack"],
                    "allow_multiple": True
                },
                {
                    "template": "Qual a complexidade estimada do sistema?",
                    "choices": [
                        {"id": "simple", "text": "Simples (CRUD básico)"},
                        {"id": "moderate", "text": "Moderada (com integrações)"},
                        {"id": "complex", "text": "Complexa (múltiplos módulos)"},
                        {"id": "enterprise", "text": "Enterprise (alta complexidade)"}
                    ],
                    "category": "technical",
                    "keywords": ["complexidade", "escala", "módulos", "funcionalidades"]
                }
            ],
            "timeline": [
                {
                    "template": "Qual o prazo desejado para conclusão?",
                    "choices": [
                        {"id": "urgent", "text": "Menos de 2 meses"},
                        {"id": "short", "text": "2-4 meses"},
                        {"id": "normal", "text": "4-8 meses"},
                        {"id": "extended", "text": "8-12 meses"},
                        {"id": "long", "text": "Mais de 12 meses"},
                        {"id": "flexible", "text": "Flexível"}
                    ],
                    "category": "timeline",
                    "keywords": ["prazo", "cronograma", "entrega", "tempo"]
                },
                {
                    "template": "Como você prefere receber as entregas?",
                    "choices": [
                        {"id": "waterfall", "text": "Entrega final completa"},
                        {"id": "agile", "text": "Entregas incrementais (sprints)"},
                        {"id": "milestones", "text": "Por marcos importantes"},
                        {"id": "continuous", "text": "Implantação contínua"}
                    ],
                    "category": "timeline",
                    "keywords": ["entrega", "metodologia", "deploy", "lançamento"]
                }
            ],
            "integration": [
                {
                    "template": "Precisa integrar com sistemas existentes?",
                    "choices": [
                        {"id": "none", "text": "Não, sistema independente"},
                        {"id": "few", "text": "Poucas integrações simples"},
                        {"id": "moderate", "text": "Algumas integrações importantes"},
                        {"id": "many", "text": "Muitas integrações complexas"},
                        {"id": "legacy", "text": "Sistemas legados críticos"}
                    ],
                    "category": "integration",
                    "keywords": ["integração", "api", "sistemas", "existente", "legacy"]
                },
                {
                    "template": "Quais tipos de integrações são necessárias?",
                    "choices": [
                        {"id": "payment", "text": "Gateway de pagamento"},
                        {"id": "email", "text": "Serviço de e-mail"},
                        {"id": "sms", "text": "SMS/WhatsApp"},
                        {"id": "erp", "text": "Sistema ERP"},
                        {"id": "crm", "text": "Sistema CRM"},
                        {"id": "social", "text": "Redes sociais"},
                        {"id": "analytics", "text": "Analytics/BI"},
                        {"id": "other", "text": "Outras integrações"}
                    ],
                    "category": "integration",
                    "keywords": ["pagamento", "email", "sms", "whatsapp", "erp", "crm"],
                    "allow_multiple": True
                }
            ]
        }
    
    def generate_questions_for_project(self, project_description: str, max_questions: int = 5) -> List[Question]:
        """
        Generate questions based on project description analysis.
        
        Args:
            project_description: Description of the project
            max_questions: Maximum number of questions to generate
            
        Returns:
            List of generated questions
        """
        logger.info(f"Generating questions for project analysis")
        
        # Analyze project description to determine relevant categories
        relevant_categories = self._analyze_project_categories(project_description)
        
        # Select questions from relevant categories
        selected_questions = []
        question_counter = 1
        
        for category in relevant_categories:
            if len(selected_questions) >= max_questions:
                break
                
            category_questions = self.question_templates.get(category, [])
            
            # Select the most relevant question from this category
            best_question = self._select_best_question_for_category(
                project_description, category_questions
            )
            
            if best_question:
                question = self._create_question_from_template(
                    best_question, f"Q{question_counter:03d}"
                )
                selected_questions.append(question)
                question_counter += 1
        
        # If we need more questions, add some general ones
        if len(selected_questions) < max_questions:
            general_questions = self._get_general_questions(
                max_questions - len(selected_questions), question_counter
            )
            selected_questions.extend(general_questions)
        
        logger.info(f"Generated {len(selected_questions)} questions")
        return selected_questions
    
    def _analyze_project_categories(self, project_description: str) -> List[str]:
        """
        Analyze project description to determine relevant question categories.
        
        Args:
            project_description: Project description text
            
        Returns:
            List of relevant category names
        """
        description_lower = project_description.lower()
        relevant_categories = []
        
        # Simple keyword-based analysis (TODO: replace with AI analysis)
        category_keywords = {
            "business": ["negócio", "empresa", "orçamento", "investimento", "objetivo", "meta"],
            "technical": ["tecnologia", "sistema", "desenvolvimento", "programação", "api", "banco"],
            "timeline": ["prazo", "cronograma", "entrega", "tempo", "urgent", "rápido"],
            "integration": ["integração", "api", "sistema existente", "erp", "crm", "pagamento"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                relevant_categories.append(category)
        
        # Always include business questions
        if "business" not in relevant_categories:
            relevant_categories.insert(0, "business")
        
        # Always include technical questions for software projects
        if "technical" not in relevant_categories:
            relevant_categories.append("technical")
        
        return relevant_categories[:4]  # Limit to 4 categories
    
    def _select_best_question_for_category(self, project_description: str, category_questions: List[Dict]) -> Optional[Dict]:
        """
        Select the best question from a category based on project description.
        
        Args:
            project_description: Project description
            category_questions: List of questions in the category
            
        Returns:
            Best matching question template or None
        """
        if not category_questions:
            return None
        
        description_lower = project_description.lower()
        
        # Score questions based on keyword matches
        scored_questions = []
        
        for question in category_questions:
            score = 0
            keywords = question.get("keywords", [])
            
            for keyword in keywords:
                if keyword in description_lower:
                    score += 1
            
            scored_questions.append((score, question))
        
        # Sort by score and return the best one
        scored_questions.sort(key=lambda x: x[0], reverse=True)
        
        if scored_questions and scored_questions[0][0] > 0:
            return scored_questions[0][1]
        
        # If no good match, return the first question
        return category_questions[0] if category_questions else None
    
    def _create_question_from_template(self, template: Dict, code: str) -> Question:
        """
        Create a Question object from a template.
        
        Args:
            template: Question template dictionary
            code: Question code (e.g., Q001)
            
        Returns:
            Question object
        """
        choices = []
        for choice_data in template["choices"]:
            choice = QuestionChoice(
                id=choice_data["id"],
                text=choice_data["text"],
                description=choice_data.get("description")
            )
            choices.append(choice)
        
        return Question(
            code=code,
            text=template["template"],
            choices=choices,
            required=template.get("required", True),
            allow_multiple=template.get("allow_multiple", False),
            category=template["category"]
        )
    
    def _get_general_questions(self, count: int, start_counter: int) -> List[Question]:
        """
        Get general questions to fill up the quota.
        
        Args:
            count: Number of questions needed
            start_counter: Starting counter for question codes
            
        Returns:
            List of general questions
        """
        general_templates = [
            {
                "template": "Qual a prioridade máxima do projeto?",
                "choices": [
                    {"id": "speed", "text": "Velocidade de entrega"},
                    {"id": "quality", "text": "Qualidade do código"},
                    {"id": "cost", "text": "Controle de custos"},
                    {"id": "features", "text": "Máximo de funcionalidades"},
                    {"id": "maintenance", "text": "Facilidade de manutenção"}
                ],
                "category": "general"
            },
            {
                "template": "Como você avalia sua experiência técnica?",
                "choices": [
                    {"id": "beginner", "text": "Iniciante - preciso de orientação"},
                    {"id": "intermediate", "text": "Intermediário - entendo o básico"},
                    {"id": "advanced", "text": "Avançado - tenho experiência"},
                    {"id": "expert", "text": "Especialista - domino a área"},
                    {"id": "team_has", "text": "Minha equipe tem a expertise"}
                ],
                "category": "general"
            }
        ]
        
        questions = []
        for i in range(min(count, len(general_templates))):
            question = self._create_question_from_template(
                general_templates[i], f"Q{start_counter + i:03d}"
            )
            questions.append(question)
        
        return questions
    
    def generate_follow_up_questions(self, previous_answers: List[Dict], session_context: Dict) -> List[Question]:
        """
        Generate follow-up questions based on previous answers.
        
        Args:
            previous_answers: List of previous question answers
            session_context: Current session context
            
        Returns:
            List of follow-up questions
        """
        logger.info("Generating follow-up questions based on previous answers")
        
        # Analyze previous answers to determine what to ask next
        answer_analysis = self._analyze_previous_answers(previous_answers)
        
        # Generate contextual follow-up questions
        follow_up_questions = []
        question_counter = len(previous_answers) + 1
        
        # If user selected specific technologies, ask about experience
        if "tech_preferences" in answer_analysis:
            tech_question = self._create_tech_experience_question(
                answer_analysis["tech_preferences"], f"Q{question_counter:03d}"
            )
            follow_up_questions.append(tech_question)
            question_counter += 1
        
        # If it's a large project, ask about team structure
        if answer_analysis.get("project_size") == "large":
            team_question = self._create_team_structure_question(f"Q{question_counter:03d}")
            follow_up_questions.append(team_question)
            question_counter += 1
        
        # Always end with the final open question if we've asked enough
        if len(previous_answers) >= 3:
            final_question = self._create_final_question(f"Q{question_counter:03d}")
            follow_up_questions.append(final_question)
        
        return follow_up_questions
    
    def _analyze_previous_answers(self, previous_answers: List[Dict]) -> Dict[str, Any]:
        """Analyze previous answers to extract insights."""
        analysis = {}
        
        for answer_data in previous_answers:
            question_code = answer_data.get("question_code", "")
            selected_choices = answer_data.get("selected_choices", [])
            
            # Analyze specific patterns
            if "tech" in str(selected_choices).lower():
                analysis["tech_preferences"] = selected_choices
            
            if any("large" in choice or "enterprise" in choice for choice in selected_choices):
                analysis["project_size"] = "large"
            
            if any("complex" in choice for choice in selected_choices):
                analysis["complexity"] = "high"
        
        return analysis
    
    def _create_tech_experience_question(self, tech_preferences: List[str], code: str) -> Question:
        """Create a question about technology experience."""
        return Question(
            code=code,
            text="Qual o nível de experiência da sua equipe com as tecnologias selecionadas?",
            choices=[
                QuestionChoice(id="expert", text="Especialista - domínio completo"),
                QuestionChoice(id="experienced", text="Experiente - uso profissional"),
                QuestionChoice(id="intermediate", text="Intermediário - conhecimento básico"),
                QuestionChoice(id="beginner", text="Iniciante - precisará de treinamento"),
                QuestionChoice(id="learning", text="Disposto a aprender durante o projeto")
            ],
            required=True,
            allow_multiple=False,
            category="technical"
        )
    
    def _create_team_structure_question(self, code: str) -> Question:
        """Create a question about team structure."""
        return Question(
            code=code,
            text="Como está estruturada a equipe de desenvolvimento?",
            choices=[
                QuestionChoice(id="internal", text="Equipe interna da empresa"),
                QuestionChoice(id="mixed", text="Equipe mista (interna + terceiros)"),
                QuestionChoice(id="outsourced", text="Equipe terceirizada"),
                QuestionChoice(id="freelancers", text="Freelancers independentes"),
                QuestionChoice(id="agency", text="Agência de desenvolvimento")
            ],
            required=True,
            allow_multiple=False,
            category="business"
        )
    
    def _create_final_question(self, code: str) -> Question:
        """Create the final question allowing additional details."""
        return Question(
            code=code,
            text="Há alguma informação adicional importante que não foi coberta pelas perguntas anteriores?",
            choices=[
                QuestionChoice(id="none", text="Não, as informações estão completas"),
                QuestionChoice(id="has_more", text="Sim, tenho informações adicionais",
                             description="Será solicitado texto livre na próxima etapa")
            ],
            required=True,
            allow_multiple=False,
            category="final"
        )