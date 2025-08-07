"""
Sistema de otimização de tokens para chamadas OpenAI.
Reduz custos e melhora performance através de estratégias inteligentes.
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import deque
import tiktoken

from app.utils.pii_safe_logging import get_pii_safe_logger
from app.models.base import DiscoveryStage

logger = get_pii_safe_logger(__name__)


@dataclass
class TokenUsage:
    """Estatísticas de uso de tokens."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    optimization_savings: int = 0


class TokenOptimizer:
    """
    Otimizador de tokens para reduzir custos e melhorar performance.
    """

    # Preços por 1K tokens (GPT-4 - atualizar conforme pricing atual)
    TOKEN_PRICES = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    }

    # Limites de contexto por modelo
    CONTEXT_LIMITS = {"gpt-4": 8192, "gpt-4-turbo": 128000, "gpt-3.5-turbo": 4096}

    # Prioridades para preservação de contexto
    CONTEXT_PRIORITIES = {
        "system_prompt": 10,
        "current_stage_data": 9,
        "validation_rules": 8,
        "recent_messages": 7,
        "file_context": 6,
        "previous_stages": 5,
        "conversation_history": 4,
        "examples": 3,
        "metadata": 2,
        "debug_info": 1,
    }

    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)
        self.context_window = deque(maxlen=50)  # Janela deslizante de contexto
        self.optimization_stats = {
            "total_savings": 0,
            "compressions_applied": 0,
            "contexts_trimmed": 0,
            "smart_summaries": 0,
        }

    def count_tokens(self, text: str) -> int:
        """
        Conta tokens em um texto.
        """
        if not text:
            return 0
        return len(self.encoding.encode(str(text)))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estima custo de uma chamada da API.
        """
        prices = self.TOKEN_PRICES.get(self.model, self.TOKEN_PRICES["gpt-4"])

        input_cost = (input_tokens / 1000) * prices["input"]
        output_cost = (output_tokens / 1000) * prices["output"]

        return input_cost + output_cost

    def compress_repeated_content(self, text: str) -> Tuple[str, int]:
        """
        Comprime conteúdo repetitivo no texto.
        """
        original_tokens = self.count_tokens(text)

        # Remover múltiplas quebras de linha
        compressed = re.sub(r"\n{3,}", "\n\n", text)

        # Remover espaços extras
        compressed = re.sub(r" {3,}", " ", compressed)

        # Remover repetições de frases
        lines = compressed.split("\n")
        seen_lines = set()
        unique_lines = []

        for line in lines:
            line_normalized = line.strip().lower()
            if line_normalized and line_normalized not in seen_lines:
                seen_lines.add(line_normalized)
                unique_lines.append(line)
            elif not line_normalized:  # Preservar linhas vazias
                unique_lines.append(line)

        compressed = "\n".join(unique_lines)

        # Comprimir listas longas
        compressed = self._compress_long_lists(compressed)

        new_tokens = self.count_tokens(compressed)
        savings = original_tokens - new_tokens

        if savings > 0:
            self.optimization_stats["compressions_applied"] += 1
            self.optimization_stats["total_savings"] += savings

        return compressed, savings

    def _compress_long_lists(self, text: str) -> str:
        """
        Comprime listas muito longas mantendo representatividade.
        """
        # Encontrar listas com bullets
        list_pattern = r"((?:^[•\-\*]\s.+\n?){6,})"

        def compress_list(match):
            list_text = match.group(1)
            items = [line.strip() for line in list_text.strip().split("\n") if line.strip()]

            if len(items) > 8:
                # Manter primeiros 4, últimos 2, e adicionar summary
                compressed_items = (
                    items[:4] + [f"• [...mais {len(items) - 6} itens similares...]"] + items[-2:]
                )
                return "\n".join(compressed_items) + "\n"

            return list_text

        return re.sub(list_pattern, compress_list, text, flags=re.MULTILINE)

    def create_smart_summary(self, stage_data: Dict[str, Any], max_tokens: int = 200) -> str:
        """
        Cria resumo inteligente de dados de estágio.
        """
        if not stage_data:
            return ""

        # Identificar campos mais importantes
        important_fields = []

        for field, value in stage_data.items():
            if not value:
                continue

            field_importance = self._calculate_field_importance(field, value)
            important_fields.append((field, value, field_importance))

        # Ordenar por importância
        important_fields.sort(key=lambda x: x[2], reverse=True)

        # Construir resumo
        summary_parts = []
        current_tokens = 0

        for field, value, importance in important_fields:
            field_summary = self._summarize_field(field, value)
            field_tokens = self.count_tokens(field_summary)

            if current_tokens + field_tokens > max_tokens:
                break

            summary_parts.append(field_summary)
            current_tokens += field_tokens

        summary = "RESUMO: " + " | ".join(summary_parts)

        self.optimization_stats["smart_summaries"] += 1

        return summary

    def _calculate_field_importance(self, field: str, value: Any) -> int:
        """
        Calcula importância de um campo para priorização.
        """
        # Campos críticos
        if field in ["nome_projeto", "tipo_aplicativo", "objetivo", "features_must"]:
            return 10

        # Campos importantes
        if field in ["stack_tecnologico", "integracoes", "slos", "budget"]:
            return 8

        # Campos úteis
        if field in ["identidade_visual", "tipo_notificacoes", "perfis"]:
            return 6

        # Listas com muitos itens são importantes
        if isinstance(value, list) and len(value) > 2:
            return 7

        # Textos longos podem ser importantes
        if isinstance(value, str) and len(value) > 50:
            return 5

        return 3

    def _summarize_field(self, field: str, value: Any) -> str:
        """
        Cria resumo conciso de um campo.
        """
        if isinstance(value, str):
            if len(value) > 50:
                return f"{field}: {value[:47]}..."
            return f"{field}: {value}"

        elif isinstance(value, list):
            if len(value) > 3:
                return f"{field}: {', '.join(map(str, value[:3]))}... (+{len(value)-3})"
            return f"{field}: {', '.join(map(str, value))}"

        elif isinstance(value, dict):
            keys = list(value.keys())[:3]
            return f"{field}: {{{', '.join(keys)}...}}"

        return f"{field}: {str(value)[:30]}"

    def optimize_context_window(self, messages: List[Dict], max_tokens: int = None) -> List[Dict]:
        """
        Otimiza janela de contexto para caber no limite.
        """
        if max_tokens is None:
            max_tokens = int(self.CONTEXT_LIMITS[self.model] * 0.8)  # 80% do limite

        total_tokens = sum(self.count_tokens(str(msg.get("content", ""))) for msg in messages)

        if total_tokens <= max_tokens:
            return messages

        logger.info(f"Otimizando contexto: {total_tokens} -> {max_tokens} tokens")

        # Separar mensagens por tipo/importância
        categorized_messages = self._categorize_messages(messages)

        # Construir contexto otimizado priorizando por importância
        optimized_messages = []
        current_tokens = 0

        # Sempre incluir system prompts
        for msg in categorized_messages.get("system_prompt", []):
            msg_tokens = self.count_tokens(str(msg.get("content", "")))
            optimized_messages.append(msg)
            current_tokens += msg_tokens

        # Incluir mensagens por prioridade
        for priority in sorted(
            self.CONTEXT_PRIORITIES.keys(), key=lambda x: self.CONTEXT_PRIORITIES[x], reverse=True
        ):
            if priority == "system_prompt":
                continue  # Já incluído

            for msg in categorized_messages.get(priority, []):
                msg_tokens = self.count_tokens(str(msg.get("content", "")))

                if current_tokens + msg_tokens > max_tokens:
                    # Se não cabe, tentar comprimir
                    if msg.get("role") == "system":
                        compressed_content, savings = self.compress_repeated_content(
                            str(msg.get("content", ""))
                        )
                        compressed_tokens = self.count_tokens(compressed_content)

                        if current_tokens + compressed_tokens <= max_tokens:
                            msg_copy = msg.copy()
                            msg_copy["content"] = compressed_content
                            optimized_messages.append(msg_copy)
                            current_tokens += compressed_tokens
                            continue

                    # Se ainda não cabe, truncar ou pular
                    if priority in ["recent_messages", "conversation_history"]:
                        # Truncar mensagem
                        available_tokens = max_tokens - current_tokens - 50  # Buffer
                        if available_tokens > 100:
                            truncated_content = self._truncate_to_tokens(
                                str(msg.get("content", "")), available_tokens
                            )
                            msg_copy = msg.copy()
                            msg_copy["content"] = truncated_content + "\n[...truncado...]"
                            optimized_messages.append(msg_copy)
                            current_tokens += self.count_tokens(msg_copy["content"])

                    break  # Não há mais espaço

                optimized_messages.append(msg)
                current_tokens += msg_tokens

        tokens_saved = total_tokens - current_tokens
        if tokens_saved > 0:
            self.optimization_stats["contexts_trimmed"] += 1
            self.optimization_stats["total_savings"] += tokens_saved

        logger.info(f"Contexto otimizado: {tokens_saved} tokens economizados")

        return optimized_messages

    def _categorize_messages(self, messages: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categoriza mensagens por tipo/importância.
        """
        categorized = {priority: [] for priority in self.CONTEXT_PRIORITIES.keys()}

        for msg in messages:
            content = str(msg.get("content", "")).lower()
            role = msg.get("role", "")

            if role == "system":
                if "demandei discovery" in content or "missão" in content:
                    categorized["system_prompt"].append(msg)
                elif "validação" in content or "score" in content:
                    categorized["validation_rules"].append(msg)
                elif "arquivos" in content or "pdf" in content:
                    categorized["file_context"].append(msg)
                elif "dados já coletados" in content:
                    categorized["current_stage_data"].append(msg)
                else:
                    categorized["metadata"].append(msg)
            elif role == "user":
                categorized["recent_messages"].append(msg)
            elif role == "assistant":
                categorized["conversation_history"].append(msg)
            else:
                categorized["metadata"].append(msg)

        return categorized

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Trunca texto para caber em número específico de tokens.
        """
        if self.count_tokens(text) <= max_tokens:
            return text

        # Truncar por parágrafos primeiro
        paragraphs = text.split("\n\n")
        truncated = ""

        for paragraph in paragraphs:
            test_text = truncated + "\n\n" + paragraph if truncated else paragraph
            if self.count_tokens(test_text) > max_tokens:
                break
            truncated = test_text

        # Se ainda muito grande, truncar por sentenças
        if self.count_tokens(truncated) > max_tokens:
            sentences = truncated.split(". ")
            truncated = ""

            for sentence in sentences:
                test_text = truncated + ". " + sentence if truncated else sentence
                if self.count_tokens(test_text) > max_tokens:
                    break
                truncated = test_text

        return truncated

    def optimize_for_stage(
        self, stage: DiscoveryStage, context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Otimiza contexto específico para um estágio.
        """
        stage_specific_optimizations = {
            DiscoveryStage.BUSINESS_CONTEXT: {
                "focus_fields": ["nome_projeto", "tipo_aplicativo", "objetivo"],
                "max_history": 5,
            },
            DiscoveryStage.FUNCTIONAL_SCOPE: {
                "focus_fields": ["features_must", "features_should", "integracoes"],
                "max_history": 8,
            },
            DiscoveryStage.FINALIZE_DOCS: {
                "focus_fields": ["all"],
                "max_history": 15,
                "include_summaries": True,
            },
        }

        optimization_config = stage_specific_optimizations.get(
            stage, {"focus_fields": ["all"], "max_history": 10}
        )

        optimized_context = context_data.copy()

        # Aplicar otimizações específicas do estágio
        if "include_summaries" in optimization_config:
            # Adicionar resumos de estágios anteriores
            optimized_context["stage_summaries"] = self._create_stage_summaries(context_data)

        return optimized_context

    def _create_stage_summaries(self, context_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Cria resumos de estágios para contexto reduzido.
        """
        summaries = {}

        for key, value in context_data.items():
            if isinstance(value, dict) and value:
                summary = self.create_smart_summary(value, max_tokens=100)
                if summary:
                    summaries[key] = summary

        return summaries

    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de otimização.
        """
        total_savings_cost = 0
        if self.optimization_stats["total_savings"] > 0:
            # Assumir que economias são 50% input, 50% output
            input_savings = self.optimization_stats["total_savings"] * 0.5
            output_savings = self.optimization_stats["total_savings"] * 0.5
            total_savings_cost = self.estimate_cost(input_savings, output_savings)

        return {
            "total_tokens_saved": self.optimization_stats["total_savings"],
            "estimated_cost_savings": total_savings_cost,
            "compressions_applied": self.optimization_stats["compressions_applied"],
            "contexts_trimmed": self.optimization_stats["contexts_trimmed"],
            "smart_summaries": self.optimization_stats["smart_summaries"],
            "optimization_efficiency": (
                self.optimization_stats["total_savings"]
                / max(
                    1,
                    self.optimization_stats["compressions_applied"]
                    + self.optimization_stats["contexts_trimmed"],
                )
            ),
        }


# Funções de conveniência
def optimize_messages_for_api(
    messages: List[Dict], model: str = "gpt-4"
) -> Tuple[List[Dict], TokenUsage]:
    """
    Otimiza mensagens para chamada da API.
    """
    optimizer = TokenOptimizer(model)

    original_tokens = sum(optimizer.count_tokens(str(msg.get("content", ""))) for msg in messages)
    optimized_messages = optimizer.optimize_context_window(messages)
    final_tokens = sum(
        optimizer.count_tokens(str(msg.get("content", ""))) for msg in optimized_messages
    )

    usage = TokenUsage(
        input_tokens=final_tokens,
        output_tokens=0,  # Será preenchido após a resposta
        total_tokens=final_tokens,
        estimated_cost=optimizer.estimate_cost(final_tokens, 200),  # Estimativa conservadora
        optimization_savings=original_tokens - final_tokens,
    )

    return optimized_messages, usage


def create_token_efficient_summary(data: Dict[str, Any], max_tokens: int = 300) -> str:
    """
    Cria resumo eficiente em tokens de dados estruturados.
    """
    optimizer = TokenOptimizer()
    return optimizer.create_smart_summary(data, max_tokens)


# Exemplo de uso
if __name__ == "__main__":
    # Teste básico
    optimizer = TokenOptimizer()

    test_messages = [
        {
            "role": "system",
            "content": "# DEMANDEI DISCOVERY PO (v2.1)\n\nVocê é um especialista técnico..." * 20,
        },
        {"role": "user", "content": "Quero criar um app de finanças"},
        {"role": "assistant", "content": "Vou ajudar você a especificar seu app de finanças..."},
    ]

    print(
        "Tokens originais:",
        sum(optimizer.count_tokens(str(msg.get("content", ""))) for msg in test_messages),
    )

    optimized, usage = optimize_messages_for_api(test_messages)

    print("Tokens otimizados:", usage.input_tokens)
    print("Economia:", usage.optimization_savings)
    print("Stats:", optimizer.get_optimization_stats())
