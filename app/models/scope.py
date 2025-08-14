"""
Modelo para o documento de escopo técnico único.
Define a estrutura e seções do documento final gerado.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TechnicalRequirement(BaseModel):
    """Requisito técnico específico."""

    category: str  # frontend, backend, database, infra
    requirement: str
    priority: str  # MUST, SHOULD, COULD
    technical_notes: Optional[str] = None


class Integration(BaseModel):
    """Integração com sistema externo."""

    name: str
    type: str  # API, webhook, database, file
    purpose: str
    technical_details: Optional[str] = None


class SecurityRequirement(BaseModel):
    """Requisito de segurança."""

    category: str  # auth, data, network, compliance
    requirement: str
    implementation: Optional[str] = None


class Deliverable(BaseModel):
    """Entregável do projeto."""

    name: str
    description: str
    acceptance_criteria: List[str]
    estimated_effort: Optional[str] = None


class TechnicalScope(BaseModel):
    """
    Documento de escopo técnico completo.
    Estrutura unificada para desenvolvedor.
    """

    # Metadados
    project_name: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    # 1. Objetivo de Negócio
    business_objective: str
    target_audience: List[str]
    key_personas: List[Dict[str, str]]
    success_metrics: List[str]

    # 2. Escopo Funcional
    functional_requirements: Dict[str, List[str]] = Field(
        default_factory=lambda: {"MUST": [], "SHOULD": [], "COULD": []}
    )
    out_of_scope: List[str] = Field(default_factory=list)

    # 3. Jornadas Críticas
    critical_user_journeys: List[Dict[str, Any]]
    user_stories: List[str] = Field(default_factory=list)

    # 4. Requisitos Não-Funcionais
    performance_requirements: Dict[str, Any] = Field(
        default_factory=lambda: {
            "latency_p95": "< 500ms",
            "availability": "99.9%",
            "concurrent_users": 1000,
            "throughput": "100 req/s",
        }
    )
    scalability_requirements: Optional[str] = None

    # 5. Integrações e Webhooks
    integrations: List[Integration] = Field(default_factory=list)
    webhooks: List[Dict[str, str]] = Field(default_factory=list)
    external_apis: List[str] = Field(default_factory=list)

    # 6. Segurança & Conformidade
    security_requirements: List[SecurityRequirement] = Field(default_factory=list)
    compliance: List[str] = Field(default_factory=list)  # LGPD, GDPR, PCI, etc.
    data_privacy: Dict[str, Any] = Field(default_factory=dict)

    # 7. Arquitetura Proposta
    technical_architecture: Dict[str, Any] = Field(
        default_factory=lambda: {
            "frontend": "Next.js 14 + TypeScript + Tailwind CSS",
            "backend": "NestJS + GraphQL + TypeORM",
            "database": "PostgreSQL 15 + Redis",
            "infrastructure": "Google Cloud Run + Cloud SQL",
            "monitoring": "Datadog + Sentry",
            "ci_cd": "GitHub Actions + Docker",
        }
    )
    technology_stack: Dict[str, List[str]] = Field(default_factory=dict)
    infrastructure_requirements: List[str] = Field(default_factory=list)

    # 8. Entregáveis e Critérios de Aceite
    deliverables: List[Deliverable] = Field(default_factory=list)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)

    # 9. Assumptions (Premissas)
    assumptions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    risks: List[Dict[str, str]] = Field(default_factory=list)

    # 10. Informações Adicionais
    budget_estimate: Optional[str] = None
    timeline_estimate: Optional[str] = None
    team_requirements: List[str] = Field(default_factory=list)
    maintenance_plan: Optional[str] = None

    def to_markdown(self) -> str:
        """Converte o escopo para formato Markdown."""
        md_parts = []

        # Header
        md_parts.append(f"# Escopo Técnico: {self.project_name}")
        md_parts.append(f"\n*Gerado em: {self.generated_at.strftime('%d/%m/%Y %H:%M')}*")
        md_parts.append(f"*Versão: {self.version}*\n")

        # 1. Objetivo de Negócio
        md_parts.append("## 1. Objetivo de Negócio\n")
        md_parts.append(self.business_objective + "\n")

        if self.target_audience:
            md_parts.append("### Público-Alvo")
            for audience in self.target_audience:
                md_parts.append(f"- {audience}")
            md_parts.append("")

        if self.success_metrics:
            md_parts.append("### Métricas de Sucesso")
            for metric in self.success_metrics:
                md_parts.append(f"- {metric}")
            md_parts.append("")

        # 2. Escopo Funcional
        md_parts.append("## 2. Escopo Funcional\n")

        for priority, items in self.functional_requirements.items():
            if items:
                md_parts.append(f"### {priority}")
                for item in items:
                    md_parts.append(f"- {item}")
                md_parts.append("")

        if self.out_of_scope:
            md_parts.append("### Fora de Escopo")
            for item in self.out_of_scope:
                md_parts.append(f"- {item}")
            md_parts.append("")

        # 3. Jornadas Críticas
        if self.critical_user_journeys:
            md_parts.append("## 3. Jornadas Críticas do Usuário\n")
            for i, journey in enumerate(self.critical_user_journeys, 1):
                md_parts.append(f"### Jornada {i}: {journey.get('name', 'N/A')}")
                if "steps" in journey:
                    for step in journey["steps"]:
                        md_parts.append(f"- {step}")
                md_parts.append("")

        # 4. Requisitos Não-Funcionais
        md_parts.append("## 4. Requisitos Não-Funcionais\n")
        md_parts.append("### Performance")
        for key, value in self.performance_requirements.items():
            md_parts.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        md_parts.append("")

        # 5. Integrações
        if self.integrations:
            md_parts.append("## 5. Integrações e APIs Externas\n")
            for integration in self.integrations:
                md_parts.append(f"### {integration.name}")
                md_parts.append(f"- **Tipo:** {integration.type}")
                md_parts.append(f"- **Propósito:** {integration.purpose}")
                if integration.technical_details:
                    md_parts.append(f"- **Detalhes:** {integration.technical_details}")
                md_parts.append("")

        # 6. Segurança & Conformidade
        md_parts.append("## 6. Segurança & Conformidade\n")

        if self.security_requirements:
            md_parts.append("### Requisitos de Segurança")
            for req in self.security_requirements:
                md_parts.append(f"- **{req.category}:** {req.requirement}")
            md_parts.append("")

        if self.compliance:
            md_parts.append("### Conformidade")
            for comp in self.compliance:
                md_parts.append(f"- {comp}")
            md_parts.append("")

        # 7. Arquitetura Técnica
        md_parts.append("## 7. Arquitetura Técnica Proposta\n")
        for component, tech in self.technical_architecture.items():
            md_parts.append(f"- **{component.replace('_', ' ').title()}:** {tech}")
        md_parts.append("")

        # 8. Entregáveis
        if self.deliverables:
            md_parts.append("## 8. Entregáveis e Critérios de Aceite\n")
            for deliverable in self.deliverables:
                md_parts.append(f"### {deliverable.name}")
                md_parts.append(f"{deliverable.description}\n")
                md_parts.append("**Critérios de Aceite:**")
                for criteria in deliverable.acceptance_criteria:
                    md_parts.append(f"- {criteria}")
                md_parts.append("")

        # 9. Assumptions
        if self.assumptions:
            md_parts.append("## 9. Premissas (Assumptions)\n")
            md_parts.append(
                "*As seguintes premissas foram consideradas na elaboração deste escopo:*\n"
            )
            for assumption in self.assumptions:
                md_parts.append(f"- {assumption}")
            md_parts.append("")

        # 10. Riscos
        if self.risks:
            md_parts.append("## 10. Riscos Identificados\n")
            for risk in self.risks:
                md_parts.append(f"- **{risk.get('type', 'Risco')}:** {risk.get('description', '')}")
                if "mitigation" in risk:
                    md_parts.append(f"  - *Mitigação:* {risk['mitigation']}")
            md_parts.append("")

        # Informações Adicionais
        if self.budget_estimate or self.timeline_estimate:
            md_parts.append("## Informações Adicionais\n")
            if self.budget_estimate:
                md_parts.append(f"- **Estimativa de Orçamento:** {self.budget_estimate}")
            if self.timeline_estimate:
                md_parts.append(f"- **Estimativa de Prazo:** {self.timeline_estimate}")
            md_parts.append("")

        # Footer
        md_parts.append("---")
        md_parts.append(
            "*Este documento foi gerado automaticamente pelo sistema de Discovery Inteligente.*"
        )

        return "\n".join(md_parts)
