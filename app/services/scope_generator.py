"""
Gerador de documento de escopo técnico único.
Compila todas as informações em um documento completo para o desenvolvedor.
"""

import json
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI

from app.models.scope import (
    TechnicalScope,
    Integration,
    SecurityRequirement,
    Deliverable,
)
from app.models.intake import Question
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class ScopeGenerator:
    """
    Gera documento de escopo técnico completo baseado em:
    - Texto inicial de intake
    - Respostas do wizard
    - Análise de IA para complementar informações
    """

    def __init__(self, api_key: str):
        from app.utils.config import get_settings

        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = settings.openai_model
        self.temperature = 0.4

    async def generate_scope(
        self,
        intake_text: str,
        answers: Dict[str, Any],
        question_catalog: List[Question],
        summary: Optional[str] = None,
        final_note: Optional[str] = None,
    ) -> TechnicalScope:
        """
        Gera documento de escopo técnico completo.

        Args:
            intake_text: Descrição inicial do projeto
            answers: Respostas do wizard {question_id: value}
            question_catalog: Catálogo de perguntas para contexto
            summary: Resumo gerado anteriormente
            final_note: Nota final do cliente

        Returns:
            TechnicalScope completo
        """
        try:
            # 1. Preparar contexto das respostas
            answers_context = self._prepare_answers_context(answers, question_catalog)

            # 2. Gerar escopo com IA
            scope_data = await self._generate_scope_with_ai(
                intake_text, answers_context, summary, final_note
            )

            # 3. Extrair e estruturar dados
            scope = self._structure_scope_data(scope_data, answers)

            # 4. Identificar assumptions
            scope.assumptions = await self._identify_assumptions(scope_data)

            logger.info(f"Escopo gerado com {len(scope.assumptions)} assumptions")

            return scope

        except Exception as e:
            logger.error(f"Erro ao gerar escopo: {str(e)}")
            # Retornar escopo básico em caso de erro
            return self._create_fallback_scope(intake_text, answers)

    async def _generate_scope_with_ai(
        self,
        intake_text: str,
        answers_context: str,
        summary: Optional[str],
        final_note: Optional[str],
    ) -> Dict[str, Any]:
        """Gera escopo usando IA."""

        prompt = f"""
        Gere um documento de escopo técnico COMPLETO e DETALHADO baseado nas informações fornecidas.
        
        CONTEXTO DO CLIENTE:
        {intake_text}
        
        RESPOSTAS DO FORMULÁRIO:
        {answers_context}
        
        {f'RESUMO ANTERIOR: {summary}' if summary else ''}
        
        {f'NOTA ADICIONAL DO CLIENTE: {final_note}' if final_note else ''}
        
        GERE UM JSON com a seguinte estrutura (seja MUITO específico e técnico):
        {{
            "project_name": "Nome do Projeto",
            "business_objective": "Objetivo de negócio claro e mensurável",
            "target_audience": ["Público 1", "Público 2"],
            "key_personas": [
                {{"name": "Persona 1", "description": "Descrição", "needs": "Necessidades"}}
            ],
            "success_metrics": ["KPI 1", "KPI 2"],
            
            "functional_requirements": {{
                "MUST": ["Requisito 1", "Requisito 2"],
                "SHOULD": ["Requisito 1"],
                "COULD": ["Requisito 1"]
            }},
            "out_of_scope": ["Item 1", "Item 2"],
            
            "critical_user_journeys": [
                {{
                    "name": "Jornada 1",
                    "steps": ["Passo 1", "Passo 2", "Passo 3"]
                }}
            ],
            
            "performance_requirements": {{
                "latency_p95": "< 500ms",
                "availability": "99.9%",
                "concurrent_users": 1000,
                "throughput": "100 req/s"
            }},
            
            "integrations": [
                {{
                    "name": "Stripe",
                    "type": "API",
                    "purpose": "Processamento de pagamentos",
                    "technical_details": "Webhook para confirmação"
                }}
            ],
            
            "security_requirements": [
                {{
                    "category": "auth",
                    "requirement": "Autenticação JWT",
                    "implementation": "Auth0 ou Supabase"
                }}
            ],
            "compliance": ["LGPD", "PCI DSS"],
            
            "technical_architecture": {{
                "frontend": "Next.js 14 + TypeScript + Tailwind CSS",
                "backend": "NestJS + GraphQL + TypeORM",
                "database": "PostgreSQL 15 + Redis",
                "infrastructure": "Google Cloud Run + Cloud SQL",
                "monitoring": "Datadog + Sentry",
                "ci_cd": "GitHub Actions + Docker"
            }},
            
            "deliverables": [
                {{
                    "name": "MVP Funcional",
                    "description": "Versão inicial com funcionalidades core",
                    "acceptance_criteria": ["Critério 1", "Critério 2"],
                    "estimated_effort": "4 semanas"
                }}
            ],
            
            "assumptions": [
                "Assumido que o cliente fornecerá APIs existentes",
                "Inferido prazo de 3 meses baseado na complexidade"
            ],
            
            "risks": [
                {{
                    "type": "Técnico",
                    "description": "Integração com sistema legado",
                    "mitigation": "Criar camada de abstração"
                }}
            ],
            
            "budget_estimate": "R$ 50.000 - R$ 80.000",
            "timeline_estimate": "3-4 meses",
            "team_requirements": ["1 Full-stack Senior", "1 DevOps", "1 Designer UI/UX"]
        }}
        
        IMPORTANTE:
        - Seja MUITO específico e técnico
        - Quando não tiver informação, marque como assumption
        - Use a arquitetura padrão: Next.js + NestJS + PostgreSQL + Google Cloud
        - Sempre inclua requisitos de segurança e conformidade
        - Gere pelo menos 5 deliverables com critérios de aceite claros
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um arquiteto de software sênior especializado em escopos técnicos detalhados. Retorne apenas JSON válido.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Erro na geração com IA: {str(e)}")
            return {}

    def _prepare_answers_context(self, answers: Dict[str, Any], catalog: List[Question]) -> str:
        """Prepara contexto formatado das respostas."""
        lines = []

        # Agrupar por estágio
        stages_map = {}
        for q_id, value in answers.items():
            question = next((q for q in catalog if q.id == q_id), None)
            if question:
                stage = question.stage
                if stage not in stages_map:
                    stages_map[stage] = []
                stages_map[stage].append((question, value))

        # Formatar por estágio
        for stage, items in stages_map.items():
            lines.append(f"\n=== {stage.upper()} ===")
            for question, value in items:
                # Formatar valor
                if isinstance(value, list):
                    # Para multi_choice, mapear IDs para labels
                    if question.options:
                        labels = []
                        for v in value:
                            option = next((o for o in question.options if o.get("id") == v), None)
                            labels.append(option.get("label", v) if option else v)
                        value_str = ", ".join(labels)
                    else:
                        value_str = ", ".join(str(v) for v in value)
                elif question.type == "single_choice" and question.options:
                    # Mapear ID para label
                    option = next((o for o in question.options if o.get("id") == value), None)
                    value_str = option.get("label", value) if option else str(value)
                else:
                    value_str = str(value)

                lines.append(f"• {question.text}")
                lines.append(f"  → {value_str}")

        return "\n".join(lines)

    def _structure_scope_data(
        self, scope_data: Dict[str, Any], answers: Dict[str, Any]
    ) -> TechnicalScope:
        """Estrutura dados do escopo no modelo TechnicalScope."""

        scope = TechnicalScope(
            project_name=scope_data.get("project_name", "Projeto Sem Nome"),
            business_objective=scope_data.get("business_objective", "Objetivo não especificado"),
            target_audience=scope_data.get("target_audience", []),
            key_personas=scope_data.get("key_personas", []),
            success_metrics=scope_data.get("success_metrics", []),
        )

        # Requisitos funcionais
        func_req = scope_data.get("functional_requirements", {})
        scope.functional_requirements = {
            "MUST": func_req.get("MUST", []),
            "SHOULD": func_req.get("SHOULD", []),
            "COULD": func_req.get("COULD", []),
        }
        scope.out_of_scope = scope_data.get("out_of_scope", [])

        # Jornadas críticas
        scope.critical_user_journeys = scope_data.get("critical_user_journeys", [])

        # Requisitos não-funcionais
        scope.performance_requirements = scope_data.get(
            "performance_requirements",
            {
                "latency_p95": "< 500ms",
                "availability": "99.9%",
                "concurrent_users": 1000,
                "throughput": "100 req/s",
            },
        )

        # Integrações
        integrations_data = scope_data.get("integrations", [])
        scope.integrations = [
            Integration(**int_data)
            if isinstance(int_data, dict)
            else Integration(name=str(int_data), type="API", purpose="A definir")
            for int_data in integrations_data
        ]

        # Segurança
        security_data = scope_data.get("security_requirements", [])
        scope.security_requirements = [
            SecurityRequirement(**sec_data)
            if isinstance(sec_data, dict)
            else SecurityRequirement(category="general", requirement=str(sec_data))
            for sec_data in security_data
        ]
        scope.compliance = scope_data.get("compliance", [])

        # Arquitetura técnica
        scope.technical_architecture = scope_data.get(
            "technical_architecture",
            {
                "frontend": "Next.js 14 + TypeScript + Tailwind CSS",
                "backend": "NestJS + GraphQL + TypeORM",
                "database": "PostgreSQL 15 + Redis",
                "infrastructure": "Google Cloud Run + Cloud SQL",
            },
        )

        # Entregáveis
        deliverables_data = scope_data.get("deliverables", [])
        scope.deliverables = [
            Deliverable(**del_data)
            if isinstance(del_data, dict)
            else Deliverable(
                name=f"Entregável {i+1}", description=str(del_data), acceptance_criteria=[]
            )
            for i, del_data in enumerate(deliverables_data)
        ]

        # Riscos
        scope.risks = scope_data.get("risks", [])

        # Estimativas
        scope.budget_estimate = scope_data.get("budget_estimate")
        scope.timeline_estimate = scope_data.get("timeline_estimate")
        scope.team_requirements = scope_data.get("team_requirements", [])

        return scope

    async def _identify_assumptions(self, scope_data: Dict[str, Any]) -> List[str]:
        """Identifica e lista assumptions do escopo."""

        assumptions = scope_data.get("assumptions", [])

        # Adicionar assumptions padrão se não houver
        if not assumptions:
            assumptions = [
                "Cliente fornecerá acesso às APIs e sistemas existentes necessários",
                "Ambiente de desenvolvimento e homologação serão provisionados pelo cliente",
                "Requisitos podem ser refinados durante a fase de descoberta detalhada",
                "Estimativas baseadas em complexidade média e equipe experiente",
                "Tecnologias sugeridas podem ser ajustadas conforme necessidade",
            ]

        return assumptions

    def _create_fallback_scope(self, intake_text: str, answers: Dict[str, Any]) -> TechnicalScope:
        """Cria escopo básico de fallback em caso de erro."""

        scope = TechnicalScope(
            project_name="Projeto de Software",
            business_objective=intake_text[:200]
            if intake_text
            else "Desenvolver solução de software",
            target_audience=["Usuários finais"],
            success_metrics=["Sistema funcional", "Usuários satisfeitos"],
        )

        # Extrair funcionalidades das respostas
        features = []
        for q_id, value in answers.items():
            if "FEATURES" in q_id and isinstance(value, list):
                features.extend(value)

        scope.functional_requirements = {
            "MUST": features[:5] if features else ["Interface de usuário", "Backend API"],
            "SHOULD": features[5:8] if len(features) > 5 else ["Relatórios"],
            "COULD": features[8:] if len(features) > 8 else ["Dark mode"],
        }

        # Arquitetura padrão
        scope.technical_architecture = {
            "frontend": "Next.js + TypeScript",
            "backend": "NestJS + PostgreSQL",
            "infrastructure": "Cloud",
        }

        # Assumptions padrão
        scope.assumptions = [
            "Escopo preliminar sujeito a refinamento",
            "Detalhes técnicos a serem definidos em reunião de kick-off",
        ]

        return scope
