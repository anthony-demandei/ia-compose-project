from typing import Dict, List, Optional, Any
import json
import re
from openai import AsyncOpenAI
from app.models.base import DiscoveryStage, ValidationResult
from app.models.session import DiscoverySession, Message
from app.core.validation_engine import ValidationEngine
from app.templates.system_prompts import DemandeiDiscoveryPO
from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.token_optimizer import TokenOptimizer, optimize_messages_for_api

logger = get_pii_safe_logger(__name__)


class AIResponse:
    def __init__(self, content: str, stage: DiscoveryStage, metadata: Optional[Dict] = None):
        self.content = content
        self.stage = stage
        self.metadata = metadata or {}


class AIProcessingEngine:
    """
    Engine de processamento de IA que gera respostas contextuais,
    faz perguntas de esclarecimento e extrai requisitos das conversas.
    """

    def __init__(self, api_key: str, model: str = None):
        from app.utils.config import get_settings

        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or settings.openai_model
        self.validation_engine = ValidationEngine()
        self.token_optimizer = TokenOptimizer(model)

        # Configurações de temperatura por tipo de operação
        self.temperatures = {
            "validation": 0.3,
            "ideation": 0.6,
            "extraction": 0.4,
            "questions": 0.7,
        }

        self._initialize_stage_prompts()

    def _initialize_stage_prompts(self):
        """Inicializa os prompts específicos para cada estágio usando o sistema avançado."""
        # Obter prompt principal do sistema
        self.main_system_prompt = DemandeiDiscoveryPO.get_main_system_prompt()

        # Obter prompts específicos por estágio
        self.stage_prompts = {}
        stage_configs = DemandeiDiscoveryPO.get_stage_prompts()

        for stage, config in stage_configs.items():
            self.stage_prompts[stage] = {
                "system": f"{self.main_system_prompt}\n\n{config['system']}",
                "questions": config["questions"],
                "validation_prompt": config.get("validation_prompt", ""),
            }

    async def generate_response(
        self,
        session: DiscoverySession,
        user_message: str,
        uploaded_files: Optional[List[Dict[str, Any]]] = None,
    ) -> AIResponse:
        """
        Gera resposta contextual baseada no estágio atual e histórico da conversa.
        """
        try:
            current_stage = session.current_stage
            stage_config = self.stage_prompts.get(current_stage)

            if not stage_config:
                logger.error("Configuração não encontrada para estágio: {}", current_stage)
                return AIResponse(
                    content="Desculpe, houve um erro interno. Por favor, tente novamente.",
                    stage=current_stage,
                )

            # Construir contexto da conversa
            conversation_context = self._build_conversation_context(session)

            # Construir contexto de arquivos se fornecido
            files_context = ""
            if uploaded_files:
                files_context = await self._build_files_context(uploaded_files)

            # Validar estágio atual
            validation_result = self.validation_engine.validate_stage(
                current_stage, session.requirements
            )

            # Adicionar instruções de formatação e anti-repetição
            formatting_instructions = f"""
REGRAS CRÍTICAS PARA PERGUNTAS:

1. **NUNCA REPITA** perguntas sobre dados já coletados (veja DADOS JÁ COLETADOS acima)
2. **AVANCE AUTOMATICAMENTE** se já tem 80%+ das informações necessárias  
3. **ACEITE RESPOSTAS CURTAS** como "web", "não sei", "azul"
4. **NÃO INSISTA** em detalhes se o usuário deu respostas diretas
5. **MÁXIMO 3 PERGUNTAS** por turno - seja seletivo e estratégico

FORMATAÇÃO DAS PERGUNTAS:
**1. Primeira pergunta?**
Explicação breve se necessário.

**2. Segunda pergunta?** 
Explicação breve se necessário.

**3. Terceira pergunta?**
Explicação breve se necessário.

Nunca coloque múltiplas perguntas numeradas na mesma linha.

VALIDAÇÃO DO ESTÁGIO ATUAL: 
Score: {validation_result.completeness_score:.1%} | Faltando: {', '.join(validation_result.missing_items[:3])}
"""

            # Gerar prompt baseado no contexto
            messages = [
                {"role": "system", "content": stage_config["system"]},
                {"role": "system", "content": formatting_instructions},
                {"role": "system", "content": f"CONTEXTO DA CONVERSA:\n{conversation_context}"},
                {
                    "role": "system",
                    "content": f"VALIDAÇÃO ATUAL:\n{self._format_validation_result(validation_result)}",
                },
            ]

            # Adicionar contexto de arquivos se disponível
            if files_context:
                messages.append(
                    {"role": "system", "content": f"ARQUIVOS ENVIADOS:\n{files_context}"}
                )

            # Adicionar mensagem do usuário
            messages.append({"role": "user", "content": user_message})

            # Preparar mensagens com suporte multimodal
            if uploaded_files:
                messages = await self._prepare_multimodal_messages(messages, uploaded_files)

            # Otimizar mensagens para economizar tokens
            optimized_messages, token_usage = optimize_messages_for_api(messages, self.model)

            # Log de otimização se houve economia significativa
            if token_usage.optimization_savings > 100:
                logger.info(
                    "Otimização de tokens aplicada: {} tokens economizados",
                    token_usage.optimization_savings,
                )

            # Chamar OpenAI com structured output quando necessário
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=optimized_messages,
                temperature=self.temperatures["ideation"],
                max_tokens=1000,
            )

            ai_content = response.choices[0].message.content

            # Formatar perguntas numeradas se houver
            ai_content = self._format_numbered_questions(ai_content)

            # Extrair dados da resposta do usuário
            await self._extract_and_update_requirements(session, user_message, current_stage)

            # Verificar se deve avançar automaticamente após a atualização
            should_advance = await self.should_advance_stage(session)

            # Se pode avançar e não está no último estágio, adicionar mensagem de avanço
            if should_advance and current_stage != DiscoveryStage.FINALIZE_DOCS:
                next_stage = self._get_next_stage(current_stage)
                if next_stage:
                    ai_content += f"\n\n✅ **Ótimo! Temos informações suficientes sobre {current_stage.value}.**\n\n🚀 **Vamos para o próximo tópico: {next_stage.value}**"

            return AIResponse(
                content=ai_content,
                stage=current_stage,
                metadata={
                    "validation_score": validation_result.completeness_score,
                    "missing_items": validation_result.missing_items,
                    "can_advance": should_advance,
                    "should_advance": should_advance,
                },
            )

        except Exception as e:
            logger.error("Erro ao gerar resposta IA: {}", str(e))
            return AIResponse(
                content="Desculpe, houve um erro ao processar sua mensagem. Por favor, tente novamente.",
                stage=session.current_stage,
            )

    async def generate_clarifying_questions(self, stage: DiscoveryStage) -> List[str]:
        """Gera perguntas de esclarecimento para um estágio específico."""
        stage_config = self.stage_prompts.get(stage)
        if stage_config and "questions" in stage_config:
            return stage_config["questions"]
        return ["Pode me dar mais detalhes sobre este aspecto?"]

    async def extract_requirements(self, conversation: List[Message]) -> Dict[str, Any]:
        """
        Extrai requisitos estruturados de uma conversa.
        """
        try:
            # Construir contexto da conversa
            conversation_text = "\n".join([f"{msg.sender}: {msg.content}" for msg in conversation])

            extraction_prompt = f"""
            Analise a seguinte conversa e extraia informações estruturadas:
            
            {conversation_text}
            
            Retorne um JSON com as informações extraídas, seguindo esta estrutura:
            {{
                "business_context": {{
                    "objetivo": "texto extraído",
                    "personas": ["persona1", "persona2"],
                    "kpis": ["kpi1", "kpi2"],
                    "riscos_principais": ["risco1", "risco2"]
                }},
                "confidence_score": 0.8
            }}
            
            Retorne apenas o JSON, sem explicações adicionais.
            """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em extração de requisitos. Retorne apenas JSON válido.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=self.temperatures["extraction"],
                max_tokens=2000,
            )

            extracted_data = json.loads(response.choices[0].message.content)
            return extracted_data

        except Exception as e:
            logger.error("Erro na extração de requisitos: {}", str(e))
            return {"error": str(e)}

    def _build_conversation_context(self, session: DiscoverySession) -> str:
        """Constrói contexto da conversa para a IA."""
        recent_messages = session.get_conversation_history(limit=10)

        context_parts = [
            f"ESTÁGIO ATUAL: {session.current_stage.value}",
            f"TOTAL DE MENSAGENS: {len(session.messages)}",
            f"SESSÃO CRIADA EM: {session.created_at}",
            "",
        ]

        # Adicionar dados já coletados para evitar repetições
        stage_data = session.requirements.get_stage_data(session.current_stage)
        if stage_data:
            context_parts.append("DADOS JÁ COLETADOS NESTE ESTÁGIO:")
            stage_dict = stage_data.dict()

            collected_data = []
            for field, value in stage_dict.items():
                if value and value != [] and value != {}:
                    if isinstance(value, str) and len(value) > 0:
                        collected_data.append(f"✅ {field.replace('_', ' ')}: {value}")
                    elif isinstance(value, list) and len(value) > 0:
                        collected_data.append(f"✅ {field.replace('_', ' ')}: {', '.join(value)}")
                    elif isinstance(value, dict) and len(value) > 0:
                        collected_data.append(f"✅ {field.replace('_', ' ')}: {str(value)}")

            # Adicionar tópicos coletados dos outros estágios também
            all_stages_data = []
            for stage in DiscoveryStage:
                if stage != session.current_stage and stage != DiscoveryStage.FINALIZE_DOCS:
                    other_data = session.requirements.get_stage_data(stage)
                    if other_data:
                        other_dict = other_data.dict()
                        for field, value in other_dict.items():
                            if value and value != [] and value != {}:
                                if isinstance(value, str) and len(value) > 0:
                                    all_stages_data.append(
                                        f"• {stage.value}: {field.replace('_', ' ')} = {value}"
                                    )

            context_parts.extend(collected_data)

            if all_stages_data:
                context_parts.append("")
                context_parts.append("DADOS COLETADOS EM OUTROS ESTÁGIOS:")
                context_parts.extend(all_stages_data[:10])  # Limite para não poluir muito

            context_parts.append("")
            context_parts.append(
                "🚨 ANTI-REPETIÇÃO: NUNCA pergunte novamente sobre dados já coletados acima!"
            )
            context_parts.append("")

        context_parts.append("HISTÓRICO RECENTE:")
        for msg in recent_messages:
            context_parts.append(f"{msg.sender}: {msg.content[:200]}...")

        return "\n".join(context_parts)

    def _format_validation_result(self, validation: ValidationResult) -> str:
        """Formata resultado da validação para contexto da IA."""
        return f"""
        COMPLETUDE: {validation.completeness_score:.1%}
        STATUS: {'COMPLETO' if validation.is_complete else 'INCOMPLETO'}
        ITENS FALTANTES: {', '.join(validation.missing_items)}
        SUGESTÕES: {', '.join(validation.suggestions)}
        """

    def _format_numbered_questions(self, content: str) -> str:
        """
        Formata perguntas numeradas para ficarem organizadas uma abaixo da outra.
        """
        # Substitui perguntas numeradas que estão inline (na mesma linha)
        # Procura por padrões como: **1. pergunta** texto **2. pergunta**

        # Primeiro, procura por perguntas numeradas em negrito
        pattern_bold = r"\*\*(\d+)\.\s*([^*]+?)\*\*"
        matches = list(re.finditer(pattern_bold, content))

        if matches:
            # Se encontrou perguntas numeradas em negrito
            new_content = content

            # Processa de trás para frente para não bagunçar os índices
            for match in reversed(matches):
                num = match.group(1)
                question = match.group(2)

                # Verifica se já está em uma nova linha
                start_pos = match.start()

                # Verifica o que vem antes
                before_text = new_content[:start_pos]
                after_text = new_content[match.end() :]

                # Se não está no início de uma linha, adiciona quebra
                if before_text and not before_text.endswith("\n"):
                    # Adiciona duas quebras antes
                    formatted = f"\n\n**{num}. {question}**"
                else:
                    formatted = f"**{num}. {question}**"

                # Se tem texto logo depois (não é quebra de linha), adiciona quebra
                if after_text and not after_text.startswith("\n"):
                    formatted = formatted + "\n"

                new_content = before_text + formatted + after_text

            content = new_content

        # Também procura por perguntas sem negrito mas numeradas
        pattern_simple = r"(?<!\*\*)(\d+)\.\s+([A-Z][^.?!]*[.?!])"

        def replace_numbered(match):
            num = match.group(1)
            question = match.group(2)
            return f"\n\n**{num}. {question}**\n"

        # Aplica a substituição para perguntas simples numeradas
        content = re.sub(pattern_simple, replace_numbered, content)

        # Remove múltiplas quebras de linha consecutivas (mais de 2)
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove espaços em branco extras no início e fim
        content = content.strip()

        return content

    async def _extract_and_update_requirements(
        self, session: DiscoverySession, user_message: str, stage: DiscoveryStage
    ):
        """
        Extrai informações da mensagem do usuário e atualiza os requisitos.
        """
        try:
            # Tratamento especial para respostas numeradas
            numbered_pattern = r"(\d+)\.\s*([^0-9]+?)(?=\d+\.|$)"

            # Prompt específico para o estágio BUSINESS_CONTEXT com os novos campos
            if stage == DiscoveryStage.BUSINESS_CONTEXT:
                extraction_prompt = f"""
                Analise esta mensagem do usuário e extraia informações técnicas do projeto:
                
                "{user_message}"
                
                Se a mensagem contiver respostas numeradas (1. resposta 2. resposta), mapeie para:
                1 = tipo_aplicativo (web, mobile, desktop)
                2 = nome_projeto
                3 = identidade_visual (cores, design)
                4 = stack_tecnologico
                5 = tipo_notificacoes
                
                Também extraia:
                - descricao_basica: qualquer descrição do que o app deve fazer
                - preferencias_design: cores, estilos mencionados
                
                Retorne APENAS um JSON válido com os campos encontrados.
                Exemplo: {{"tipo_aplicativo": "web", "nome_projeto": "Max Finanças", "identidade_visual": "verde e azul"}}
                """
            else:
                extraction_prompt = f"""
                Extraia informações específicas para o estágio "{stage.value}" desta mensagem:
                
                "{user_message}"
                
                Retorne um JSON com os campos relevantes para este estágio.
                Se não houver informações suficientes, retorne campos vazios.
                Seja preciso e extraia apenas o que está explicitamente mencionado.
                """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um extrator de dados preciso. Retorne apenas JSON válido.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=self.temperatures["extraction"],
                response_format={"type": "json_object"},
                max_tokens=500,
            )

            extracted_data = json.loads(response.choices[0].message.content)

            # Atualizar requisitos da sessão
            if extracted_data:
                session.requirements.update_stage_data(stage, extracted_data)
                logger.info("Requisitos atualizados para estágio {}: {}", stage, extracted_data)

        except Exception as e:
            logger.error("Erro ao extrair dados da mensagem: {}", str(e))

    async def should_advance_stage(self, session: DiscoverySession) -> bool:
        """Verifica se deve avançar para o próximo estágio."""
        validation = self.validation_engine.validate_stage(
            session.current_stage, session.requirements
        )
        return validation.completeness_score >= 0.8

    def _get_next_stage(self, current_stage: DiscoveryStage) -> Optional[DiscoveryStage]:
        """Retorna o próximo estágio na sequência."""
        stage_order = [
            DiscoveryStage.BUSINESS_CONTEXT,
            DiscoveryStage.USERS_AND_JOURNEYS,
            DiscoveryStage.FUNCTIONAL_SCOPE,
            DiscoveryStage.CONSTRAINTS_POLICIES,
            DiscoveryStage.NON_FUNCTIONAL,
            DiscoveryStage.TECH_PREFERENCES,
            DiscoveryStage.DELIVERY_BUDGET,
            DiscoveryStage.REVIEW_GAPS,
            DiscoveryStage.FINALIZE_DOCS,
        ]

        try:
            current_index = stage_order.index(current_stage)
            if current_index < len(stage_order) - 1:
                return stage_order[current_index + 1]
        except ValueError:
            pass

        return None

    async def generate_finalization_summary(self, session: DiscoverySession) -> str:
        """Gera resumo executivo para confirmação final."""
        try:
            req = session.requirements

            # Extrair informações principais de cada estágio
            objetivo_principal = req.business_context.objetivo or "Não especificado"

            escopo_tecnico = []
            if req.functional_scope.features_must:
                escopo_tecnico.extend(req.functional_scope.features_must[:3])

            restricoes_principais = []
            if req.constraints_policies.lgpd_pii:
                restricoes_principais.append(f"LGPD: {str(req.constraints_policies.lgpd_pii)}")
            if req.non_functional.slos and req.non_functional.slos.get("latency"):
                restricoes_principais.append(
                    f"Latência: <{req.non_functional.slos.get('latency')}ms"
                )

            cronograma_orcamento = []
            if req.delivery_budget.prazo_semanas:
                cronograma_orcamento.append(f"Prazo: {req.delivery_budget.prazo_semanas} semanas")
            if req.delivery_budget.budget:
                cronograma_orcamento.append(f"Orçamento: R$ {req.delivery_budget.budget:,.2f}")

            # Gerar prompt de finalização personalizado
            finalization_prompt = DemandeiDiscoveryPO.get_finalization_prompt()
            finalization_prompt = finalization_prompt.replace(
                "[objetivo_principal]", objetivo_principal
            )
            finalization_prompt = finalization_prompt.replace(
                "[escopo_tecnico]", " • ".join(escopo_tecnico[:3])
            )
            finalization_prompt = finalization_prompt.replace(
                "[restricoes_principais]", " • ".join(restricoes_principais[:3])
            )
            finalization_prompt = finalization_prompt.replace(
                "[cronograma_orcamento]", " • ".join(cronograma_orcamento)
            )
            finalization_prompt = finalization_prompt.replace(
                "[riscos_principais]",
                " • ".join(
                    req.business_context.riscos_principais[:2]
                    if req.business_context.riscos_principais
                    else ["Não identificados"]
                ),
            )

            return finalization_prompt

        except Exception as e:
            logger.error("Erro ao gerar resumo de finalização: {}", str(e))
            return DemandeiDiscoveryPO.get_finalization_prompt()

    async def generate_completion_message(self) -> str:
        """Gera mensagem de conclusão após geração dos arquivos."""
        return DemandeiDiscoveryPO.get_completion_message()

    async def validate_stage_completion(
        self, stage: DiscoveryStage, session: DiscoverySession
    ) -> ValidationResult:
        """Valida se um estágio está completo usando prompt específico."""
        try:
            stage_config = self.stage_prompts.get(stage)
            if not stage_config or not stage_config.get("validation_prompt"):
                # Fallback para validação padrão
                return self.validation_engine.validate_stage(stage, session.requirements)

            # Construir contexto das informações coletadas
            collected_info = self._build_stage_context(session, stage)

            # Usar prompt de validação específico do estágio
            validation_prompt = stage_config["validation_prompt"].format(
                collected_info=collected_info
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um validador rigoroso de requisitos. Retorne apenas JSON válido.",
                    },
                    {"role": "user", "content": validation_prompt},
                ],
                temperature=self.temperatures["validation"],
                response_format={"type": "json_object"},
                max_tokens=500,
            )

            validation_data = json.loads(response.choices[0].message.content)

            return ValidationResult(
                is_complete=validation_data.get("is_complete", False),
                completeness_score=validation_data.get("completeness_score", 0.0),
                missing_items=validation_data.get("missing_items", []),
                suggestions=[],
            )

        except Exception as e:
            logger.error("Erro na validação avançada do estágio {}: {}", stage, str(e))
            # Fallback para validação padrão
            return self.validation_engine.validate_stage(stage, session.requirements)

    def _build_stage_context(self, session: DiscoverySession, stage: DiscoveryStage) -> str:
        """Constrói contexto específico de um estágio para validação."""
        req = session.requirements

        stage_contexts = {
            DiscoveryStage.BUSINESS_CONTEXT: f"""
            Objetivo: {req.business_context.objetivo}
            Personas: {req.business_context.personas}
            KPIs: {req.business_context.kpis}
            Riscos: {req.business_context.riscos_principais}
            """,
            DiscoveryStage.USERS_AND_JOURNEYS: f"""
            Perfis: {req.users_and_journeys.perfis}
            Jornadas: {req.users_and_journeys.jornadas_criticas}
            Idiomas: {req.users_and_journeys.idiomas}
            Acessibilidade: {req.users_and_journeys.acessibilidade}
            """,
            DiscoveryStage.FUNCTIONAL_SCOPE: f"""
            Features Must: {req.functional_scope.features_must}
            Features Should: {req.functional_scope.features_should}
            Integrações: {req.functional_scope.integracoes}
            Webhooks: {req.functional_scope.webhooks}
            """,
            DiscoveryStage.CONSTRAINTS_POLICIES: f"""
            LGPD PII: {req.constraints_policies.lgpd_pii}
            Segurança: {req.constraints_policies.seguranca}
            Auditoria: {req.constraints_policies.auditoria}
            Compliance: {req.constraints_policies.compliance}
            """,
            DiscoveryStage.NON_FUNCTIONAL: f"""
            SLOs: {req.non_functional.slos}
            Disponibilidade: {req.non_functional.disponibilidade}
            Custo Alvo: R$ {req.non_functional.custo_alvo}
            Escalabilidade: {req.non_functional.escalabilidade}
            """,
            DiscoveryStage.TECH_PREFERENCES: f"""
            Stacks Permitidas: {req.tech_preferences.stacks_permitidas}
            Stacks Vedadas: {req.tech_preferences.stacks_vedadas}
            Legado: {req.tech_preferences.legado}
            Infraestrutura: {req.tech_preferences.infraestrutura_preferida}
            """,
            DiscoveryStage.DELIVERY_BUDGET: f"""
            Marcos: {req.delivery_budget.marcos}
            Prazos: {req.delivery_budget.prazos}
            Budget: R$ {req.delivery_budget.budget}
            Governança: {req.delivery_budget.governanca}
            """,
            DiscoveryStage.REVIEW_GAPS: f"""
            Lacunas: {req.review_gaps.lacunas_identificadas}
            Trade-offs: {req.review_gaps.trade_offs}
            Decisões Pendentes: {req.review_gaps.decisoes_pendentes}
            Riscos Aceitos: {req.review_gaps.riscos_aceitos}
            """,
        }

        return stage_contexts.get(stage, "Contexto não disponível")

    async def _build_files_context(self, uploaded_files: List[Dict[str, Any]]) -> str:
        """Constrói contexto dos arquivos enviados para a IA."""
        context_parts = [
            "=== ARQUIVOS ENVIADOS PELO USUÁRIO ===",
            f"Total de arquivos: {len(uploaded_files)}",
            "",
        ]

        for i, file_info in enumerate(uploaded_files, 1):
            file_type = file_info.get("file_type", "unknown")
            filename = file_info.get("original_filename", "unknown")

            context_parts.append(f"ARQUIVO {i}: {filename}")
            context_parts.append(f"Tipo: {file_type}")

            # Adicionar conteúdo processado se disponível
            processed_content = file_info.get("processed_content", {})

            if file_type == "image":
                # Contexto de imagens
                analysis = processed_content.get("ai_analysis", {})
                context_parts.extend(
                    [
                        f"- Elementos UI: {', '.join(analysis.get('ui_elements', [])[:5])}",
                        f"- Padrões: {', '.join(analysis.get('design_patterns', [])[:3])}",
                        f"- Estilo: {analysis.get('design_style', 'não identificado')}",
                        f"- Texto extraído: {analysis.get('extracted_text', '')[:100]}...",
                    ]
                )

                # Sugestões técnicas
                suggestions = analysis.get("implementation_suggestions", [])
                if suggestions:
                    context_parts.append(f"- Sugestões técnicas: {'; '.join(suggestions[:3])}")

            elif file_type == "pdf":
                # Contexto de PDFs
                analysis = processed_content.get("ai_analysis", {})
                structured_data = processed_content.get("structured_data", {})

                context_parts.extend(
                    [
                        f"- Tipo de documento: {analysis.get('document_type', 'não identificado')}",
                        f"- Páginas: {structured_data.get('total_pages', 0)}",
                        f"- Contém tabelas: {'Sim' if structured_data.get('has_tables') else 'Não'}",
                    ]
                )

                # Requisitos identificados
                req_types = analysis.get("content_types", [])
                if req_types:
                    context_parts.append(f"- Tipos de conteúdo: {', '.join(req_types[:5])}")

                # Regras de negócio
                business_rules = analysis.get("business_rules", [])
                if business_rules:
                    context_parts.append(f"- Regras de negócio: {'; '.join(business_rules[:3])}")

                # Requisitos técnicos
                tech_req = analysis.get("technical_requirements", [])
                if tech_req:
                    context_parts.append(f"- Req. técnicos: {'; '.join(tech_req[:3])}")

            elif file_type == "markdown":
                # Contexto de Markdown
                analysis = processed_content.get("ai_analysis", {})
                structured_data = processed_content.get("structured_data", {})

                context_parts.extend(
                    [
                        f"- Tipo de doc: {analysis.get('doc_type', 'não identificado')}",
                        f"- Headers: {len(structured_data.get('headers', []))}",
                        f"- Blocos de código: {len(structured_data.get('code_blocks', []))}",
                    ]
                )

                # Requisitos existentes
                existing_req = analysis.get("existing_requirements", [])
                if existing_req:
                    context_parts.append(
                        f"- Requisitos identificados: {'; '.join(existing_req[:3])}"
                    )

                # Tecnologias mencionadas
                dependencies = analysis.get("dependencies", [])
                if dependencies:
                    context_parts.append(f"- Tecnologias: {', '.join(dependencies[:5])}")

            # Insights gerais
            insights = processed_content.get("insights", [])
            if insights:
                context_parts.append(f"- Insights: {'; '.join(insights[:2])}")

            context_parts.append("")  # Linha em branco entre arquivos

        context_parts.append("=== FIM DOS ARQUIVOS ===")
        context_parts.append("")
        context_parts.append(
            "INSTRUÇÕES: Use essas informações dos arquivos para enriquecer suas perguntas e sugestões. Referencie elementos específicos dos arquivos quando relevante para o estágio atual da descoberta."
        )

        return "\n".join(context_parts)

    async def _prepare_multimodal_messages(
        self, messages: List[Dict], uploaded_files: List[Dict[str, Any]]
    ) -> List[Dict]:
        """
        Prepara mensagens com conteúdo multimodal para OpenAI GPT-4 Vision.
        Processa imagens, PDFs e documentos para incluir nas mensagens.
        """
        try:
            # Encontrar a última mensagem do usuário para adicionar conteúdo multimodal
            user_message_idx = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    user_message_idx = i
                    break

            if user_message_idx is None:
                return messages

            user_message = messages[user_message_idx]
            multimodal_content = []

            # Adicionar texto original
            multimodal_content.append({"type": "text", "text": user_message["content"]})

            # Processar cada arquivo enviado
            for file_info in uploaded_files:
                file_type = file_info.get("file_type", "unknown")
                processed_content = file_info.get("processed_content", {})

                if file_type == "image":
                    # Para imagens, usar GPT-4 Vision
                    image_url = file_info.get("processed_content", {}).get("base64_data")
                    if image_url:
                        multimodal_content.append(
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_url}",
                                    "detail": "high",
                                },
                            }
                        )

                elif file_type == "pdf":
                    # Para PDFs, adicionar texto extraído e análise
                    pdf_analysis = processed_content.get("ai_analysis", {})
                    extracted_text = processed_content.get("extracted_text", "")

                    pdf_context = f"""
📄 **CONTEÚDO DO PDF ENVIADO:**

**Tipo:** {pdf_analysis.get('document_type', 'Documento técnico')}
**Páginas:** {processed_content.get('structured_data', {}).get('total_pages', 'N/A')}

**Regras de Negócio Identificadas:**
{chr(10).join(f'• {rule}' for rule in pdf_analysis.get('business_rules', [])[:5])}

**Requisitos Técnicos:**
{chr(10).join(f'• {req}' for req in pdf_analysis.get('technical_requirements', [])[:5])}

**Texto Relevante:**
{extracted_text[:1000]}...
"""

                    multimodal_content.append({"type": "text", "text": pdf_context})

                elif file_type == "markdown":
                    # Para Markdown, adicionar conteúdo estruturado
                    md_analysis = processed_content.get("ai_analysis", {})

                    md_context = f"""
📝 **DOCUMENTAÇÃO MARKDOWN ENVIADA:**

**Tipo:** {md_analysis.get('doc_type', 'Documentação técnica')}

**Requisitos Existentes:**
{chr(10).join(f'• {req}' for req in md_analysis.get('existing_requirements', [])[:5])}

**Tecnologias Mencionadas:**
{chr(10).join(f'• {tech}' for tech in md_analysis.get('dependencies', [])[:8])}

**Insights:**
{chr(10).join(f'• {insight}' for insight in processed_content.get('insights', [])[:3])}
"""

                    multimodal_content.append({"type": "text", "text": md_context})

            # Atualizar mensagem do usuário com conteúdo multimodal
            messages[user_message_idx] = {"role": "user", "content": multimodal_content}

            return messages

        except Exception as e:
            logger.error("Erro ao preparar mensagens multimodais: {}", str(e))
            return messages  # Fallback para mensagens originais
