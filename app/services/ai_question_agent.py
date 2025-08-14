"""
AI Question Agent - Agente inteligente que gera perguntas dinamicamente
como um desenvolvedor sênior ou Product Owner experiente.

Totalmente dinâmico, sem templates ou domínios predefinidos.
Gera perguntas naturais e contextuais baseadas apenas na descrição do projeto.
"""

import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import ValidationError
from app.models.api_models import Question, QuestionChoice
from app.services.ai_factory import get_ai_provider
from app.services.question_cache import get_question_cache
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


# Note: Complex JSON extraction functions removed - no longer needed with Gemini structured output


def create_example_json_from_question_model() -> str:
    """
    Create example JSON string based on our Question/QuestionChoice Pydantic models.
    This follows the Medium article's approach of providing concrete examples.
    
    Returns:
        JSON string showing expected structure
    """
    example_questions = [
        {
            "code": "Q001",
            "text": "Pergunta específica sobre o projeto?",
            "why_it_matters": "Esta pergunta é essencial porque define a estratégia técnica do projeto.",
            "category": "business",
            "required": True,
            "allow_multiple": False,
            "choices": [
                {"id": "opt1", "text": "Primeira opção"},
                {"id": "opt2", "text": "Segunda opção"},
                {"id": "opt3", "text": "Terceira opção"}
            ]
        },
        {
            "code": "Q002", 
            "text": "Outra pergunta contextual?",
            "why_it_matters": "Pergunta crítica para determinar a complexidade da arquitetura.",
            "category": "technical",
            "required": True,
            "allow_multiple": False,
            "choices": [
                {"id": "choice1", "text": "Opção A"},
                {"id": "choice2", "text": "Opção B"}
            ]
        }
    ]
    
    return json.dumps({"questions": example_questions}, indent=2, ensure_ascii=False)


def validate_questions_json(json_data: Dict) -> Tuple[List[Question], List[str]]:
    """
    Validate extracted JSON against Question Pydantic models.
    
    Args:
        json_data: Extracted JSON dictionary
        
    Returns:
        Tuple of (validated_questions, validation_errors)
    """
    validated_questions = []
    validation_errors = []
    
    # Handle different response formats
    if "questions" in json_data:
        raw_questions = json_data["questions"]
    elif isinstance(json_data, list):
        raw_questions = json_data
    else:
        validation_errors.append("JSON does not contain 'questions' field or is not a list")
        return [], validation_errors
    
    for idx, q_data in enumerate(raw_questions):
        try:
            # Validate choices first
            choices = []
            for choice_data in q_data.get("choices", []):
                try:
                    choice = QuestionChoice(
                        id=choice_data.get("id", f"opt_{idx}_{len(choices)}"),
                        text=choice_data.get("text", "Opção"),
                        description=choice_data.get("description")
                    )
                    choices.append(choice)
                except ValidationError as e:
                    validation_errors.append(f"Choice {idx} validation error: {e}")
                    continue
            
            # Create and validate question
            question = Question(
                code=q_data.get("code", f"Q{idx+1:03d}"),
                text=q_data.get("text", "Pergunta não especificada"),
                why_it_matters=q_data.get("why_it_matters", "Esta pergunta ajuda a esclarecer requisitos importantes do projeto."),
                choices=choices,
                required=q_data.get("required", True),
                allow_multiple=q_data.get("allow_multiple", False),
                category=q_data.get("category", "general")
            )
            
            validated_questions.append(question)
            
        except ValidationError as e:
            validation_errors.append(f"Question {idx} validation error: {e}")
            continue
    
    return validated_questions, validation_errors


class AIQuestionAgent:
    """
    Agente IA que age como desenvolvedor sênior/Product Owner fazendo perguntas inteligentes.
    
    Características:
    - Gera perguntas como um humano faria em uma reunião
    - Adapta-se a qualquer tipo de projeto
    - Sem templates ou categorias predefinidas
    - Aprende com o contexto da sessão
    """
    
    def __init__(self):
        """Initialize the AI Question Agent."""
        self.ai_provider = get_ai_provider()
        self.system_prompt = self._create_system_prompt()
        self.cache = get_question_cache()
        
        logger.info("🤖 AI Question Agent initialized", extra={
            "cache_enabled": True
        })
        
    def _create_system_prompt(self) -> str:
        """System prompt otimizado para JSON nativo com contexto de negócio explícito."""
        return """CONTEXTO: Este é um sistema de análise de projetos corporativos legítimos para fins de consultoria em desenvolvimento de software. Todo conteúdo é de natureza comercial/empresarial para análise técnica profissional.

Você é um assistente especialista em análise de projetos de software comerciais e corporativos.
Seu papel é atuar como um Product Owner (PO) ou Desenvolvedor Sênior experiente analisando projetos empresariais legítimos.
Sua tarefa é analisar a descrição de um projeto empresarial/comercial e gerar perguntas técnicas e de negócio pertinentes para esclarecer os requisitos.

IMPORTANTE: Todo o conteúdo analisado é para fins de consultoria técnica empresarial legítima, não contém material inadequado.

Responda SEMPRE E SOMENTE com um objeto JSON que siga o schema fornecido. Não inclua texto explicativo, markdown ou qualquer outra coisa fora do JSON."""
    
    async def generate_questions(
        self, 
        project_description: str,
        num_questions: int = 5,
        session_context: Optional[Dict] = None,
        exclude_covered_topics: Optional[List[str]] = None
    ) -> List[Question]:
        """
        Generate intelligent questions based on project description.
        
        Args:
            project_description: The project description text
            num_questions: Number of questions to generate (3-10)
            session_context: Optional context from previous interactions
            
        Returns:
            List of Question objects with dynamic content
        """
        start_time = time.time()
        
        logger.info(f"🚀 Starting question generation", extra={
            "num_questions": num_questions,
            "description_length": len(project_description),
            "has_context": session_context is not None
        })
        
        # Step 1: Check cache first
        cached_questions = self.cache.get(project_description)
        if cached_questions and len(cached_questions) >= num_questions:
            logger.info("⚡ Using cached questions", extra={
                "cache_hit": True,
                "questions_count": len(cached_questions),
                "execution_time_ms": (time.time() - start_time) * 1000
            })
            return cached_questions[:num_questions]
        
        # Step 2: Get similar projects from Zep for context
        similar_projects = await self.zep_manager.get_similar_projects(
            project_description, 
            limit=3
        )
        
        # Build enhanced context
        enhanced_context = session_context or {}
        if similar_projects:
            enhanced_context["similar_projects"] = similar_projects
        
        # Step 3: Build the prompt with context and exclusions
        prompt = self._build_generation_prompt(
            project_description, 
            num_questions,
            enhanced_context,
            exclude_covered_topics
        )
        
        # NOVO: Lógica simplificada com JSON nativo confiável
        try:
            logger.info("🎯 Calling Gemini with native JSON mode...", extra={
                "project_length": len(project_description),
                "num_questions": num_questions
            })
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # A chamada é agora muito mais confiável com JSON nativo
            response_json = await self.ai_provider.generate_json_response(
                messages=messages,
                temperature=0.5,  # Temperatura mais baixa para consistência
                max_tokens=2048
            )

            # Verificação de erro simplificada
            if "error" in response_json:
                logger.error(f"❌ AI provider returned an error: {response_json.get('details', response_json['error'])}")
                return self._get_fallback_questions()

            # A validação com Pydantic continua sendo uma boa prática
            validated_questions, validation_errors = validate_questions_json(response_json)
            
            if validation_errors:
                logger.warning(f"⚠️ Validation errors found in AI response: {validation_errors}")
                # Mesmo com erros, podemos ter perguntas válidas
                if validated_questions:
                    logger.info(f"✅ Using {len(validated_questions)} partially valid questions.")
                    # Continuar com as perguntas válidas

            if not validated_questions:
                logger.error("❌ No valid questions could be parsed from AI response.")
                return self._get_fallback_questions()

            execution_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Successfully generated {len(validated_questions)} questions", extra={
                "questions_count": len(validated_questions),
                "execution_time_ms": execution_time,
                "cache_hit": False
            })

            # Cache e Zep
            self.cache.put(project_description, validated_questions)
            await self.zep_manager.store_project_interaction(
                session_id=enhanced_context.get("session_id", "unknown"),
                project_description=project_description,
                questions=[q.dict() for q in validated_questions],
                project_classification=enhanced_context.get("classification", {})
            )

            return validated_questions

        except Exception as e:
            logger.error(f"❌ Unhandled exception during question generation: {e}", exc_info=True)
            return self._get_fallback_questions()
    
    def _build_generation_prompt(
        self, 
        description: str, 
        num_questions: int,
        context: Optional[Dict],
        exclude_topics: Optional[List[str]] = None
    ) -> str:
        """Prompt otimizado para JSON nativo."""
        
        # Contexto adicional se disponível
        context_str = ""
        if context and context.get("similar_projects"):
            context_str = f"\n\nPara referência, aqui estão trechos de projetos similares:\n" + "\n".join(context["similar_projects"])
        
        # Tópicos a evitar se especificados
        exclusion_str = ""
        if exclude_topics:
            exclusion_str = f"\n\nIMPORTANTE: EVITE perguntas sobre estes tópicos já cobertos: {', '.join(exclude_topics)}"

        return f"""ANÁLISE DE PROJETO COMERCIAL LEGÍTIMO:

Este é um projeto empresarial real para consultoria técnica em desenvolvimento de software. O conteúdo é puramente comercial/corporativo e adequado para análise profissional.

Projeto a analisar:
---
{description}
---

TAREFA: Como consultor técnico experiente, gere exatamente {num_questions} perguntas inteligentes e contextuais sobre este projeto comercial. 

OBRIGATÓRIO - CADA PERGUNTA DEVE INCLUIR:
- text: A pergunta em si
- why_it_matters: Explicação de 1-2 frases sobre POR QUE esta pergunta é crítica para o sucesso do projeto
- choices: Opções de múltipla escolha quando aplicável
- category: 'business', 'technical', ou 'operational'

As perguntas devem:
- Ajudar a definir o escopo técnico e de negócio
- Identificar riscos e requisitos não-funcionais  
- Esclarecer funcionalidades e arquitetura
- Ser apropriadas para consultoria empresarial
- Incluir justificativas claras (why_it_matters) do valor de cada pergunta{context_str}{exclusion_str}

CONFIRMAÇÃO: Este conteúdo é para análise técnica comercial legítima."""
    
    # REMOVIDO: _parse_ai_response não é mais necessário
    # A validação é feita diretamente em generate_questions() com JSON nativo
    
    def _get_fallback_questions(self) -> List[Question]:
        """
        Minimal fallback questions if AI fails.
        These are generic but better than nothing.
        """
        return [
            Question(
                code="Q001",
                text="Qual é o principal objetivo deste projeto?",
                why_it_matters="Define a estratégia de desenvolvimento e prioridades técnicas do projeto.",
                choices=[
                    QuestionChoice(id="automate", text="Automatizar processos manuais"),
                    QuestionChoice(id="improve", text="Melhorar sistema existente"),
                    QuestionChoice(id="new", text="Criar nova solução do zero"),
                    QuestionChoice(id="integrate", text="Integrar sistemas diferentes"),
                    QuestionChoice(id="other", text="Outro objetivo")
                ],
                required=True,
                allow_multiple=False,
                category="business"
            ),
            Question(
                code="Q002",
                text="Qual é o prazo esperado para a primeira entrega?",
                why_it_matters="Determina a metodologia de desenvolvimento e recursos necessários para atender o cronograma.",
                choices=[
                    QuestionChoice(id="urgent", text="Menos de 1 mês (urgente)"),
                    QuestionChoice(id="short", text="1-3 meses"),
                    QuestionChoice(id="medium", text="3-6 meses"),
                    QuestionChoice(id="long", text="6-12 meses"),
                    QuestionChoice(id="flexible", text="Prazo flexível")
                ],
                required=True,
                allow_multiple=False,
                category="operational"
            ),
            Question(
                code="Q003",
                text="Quantos usuários você espera que usem o sistema?",
                why_it_matters="Define a arquitetura de escalabilidade e infraestrutura necessária para suportar a carga esperada.",
                choices=[
                    QuestionChoice(id="small", text="Menos de 100 usuários"),
                    QuestionChoice(id="medium", text="100 a 1.000 usuários"),
                    QuestionChoice(id="large", text="1.000 a 10.000 usuários"),
                    QuestionChoice(id="enterprise", text="Mais de 10.000 usuários"),
                    QuestionChoice(id="unknown", text="Ainda não sei")
                ],
                required=True,
                allow_multiple=False,
                category="technical"
            )
        ]
    
    async def generate_followup_questions(
        self,
        project_description: str,
        previous_answers: List[Dict],
        num_questions: int = 3
    ) -> List[Question]:
        """
        Generate follow-up questions based on previous answers.
        
        Args:
            project_description: Original project description
            previous_answers: List of previous Q&A pairs
            num_questions: Number of follow-up questions
            
        Returns:
            List of follow-up Question objects
        """
        context = {
            "previous_answers": previous_answers,
            "question_round": len(previous_answers) // 3 + 2  # Track which round we're in
        }
        
        # Add instruction for follow-up in the prompt
        enhanced_description = f"""
{project_description}

IMPORTANTE: Esta é a rodada {context['question_round']} de perguntas.
Baseie-se nas respostas anteriores para fazer perguntas mais específicas e detalhadas.
Evite repetir tópicos já cobertos.
"""
        
        return await self.generate_questions(
            enhanced_description,
            num_questions,
            context
        )