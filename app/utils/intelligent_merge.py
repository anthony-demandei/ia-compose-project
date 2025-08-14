"""
Sistema de merge inteligente com deduplicação para requisitos.
Previne duplicação de dados e consolida informações similares automaticamente.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


@dataclass
class MergeConflict:
    """Representa um conflito durante o merge."""

    field_path: str
    existing_value: Any
    new_value: Any
    similarity_score: float
    resolution_strategy: str


class IntelligentMerger:
    """
    Sistema de merge inteligente que consolida dados sem duplicação.
    """

    # Configurações de similaridade
    SIMILARITY_THRESHOLD = 0.85
    FUZZY_MATCH_THRESHOLD = 0.75

    # Campos que devem ser tratados como listas únicas
    LIST_FIELDS = {
        "features_must",
        "features_should",
        "integracoes",
        "kpis",
        "riscos_principais",
        "personas",
        "jornadas_criticas",
        "stacks_permitidas",
        "stacks_vedadas",
        "compliance",
    }

    # Campos que podem ser sobrescritos
    OVERWRITEABLE_FIELDS = {
        "objetivo",
        "nome_projeto",
        "tipo_aplicativo",
        "descricao_basica",
        "disponibilidade",
        "custo_alvo",
        "budget",
    }

    # Palavras de parada para normalização
    STOP_WORDS = {
        "o",
        "a",
        "os",
        "as",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "para",
        "com",
        "por",
        "sem",
        "sob",
        "sobre",
        "um",
        "uma",
        "uns",
        "umas",
        "e",
        "ou",
        "mas",
        "que",
        "se",
        "quando",
        "onde",
    }

    def __init__(self):
        self.merge_stats = {
            "items_merged": 0,
            "duplicates_removed": 0,
            "conflicts_resolved": 0,
            "similarity_improvements": 0,
        }
        self.conflicts: List[MergeConflict] = []

    def normalize_text(self, text: str) -> str:
        """
        Normaliza texto para comparação melhor.
        """
        if not isinstance(text, str):
            return str(text).lower()

        # Converter para minúsculas e remover acentos
        normalized = text.lower().strip()

        # Remover pontuação e caracteres especiais
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remover múltiplos espaços
        normalized = re.sub(r"\s+", " ", normalized)

        # Remover palavras de parada
        words = [w for w in normalized.split() if w not in self.STOP_WORDS]

        return " ".join(words)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade entre dois textos.
        """
        if not text1 or not text2:
            return 0.0

        # Normalizar textos
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)

        if norm1 == norm2:
            return 1.0

        # Usar SequenceMatcher para similaridade fuzzy
        return SequenceMatcher(None, norm1, norm2).ratio()

    def find_similar_items(self, items: List[str], new_item: str) -> Tuple[Optional[str], float]:
        """
        Encontra item similar em uma lista.

        Returns:
            Tuple (item_similar, score) ou (None, 0.0) se não encontrar
        """
        best_match = None
        best_score = 0.0

        for item in items:
            score = self.calculate_similarity(new_item, item)
            if score > best_score and score >= self.FUZZY_MATCH_THRESHOLD:
                best_match = item
                best_score = score

        return best_match, best_score

    def merge_string_lists(self, existing: List[str], new: List[str]) -> List[str]:
        """
        Merge listas de strings com deduplicação inteligente.
        """
        merged = existing.copy()
        duplicates_found = 0

        for new_item in new:
            if not new_item or not new_item.strip():
                continue

            # Verificar duplicatas exatas
            if new_item in merged:
                duplicates_found += 1
                continue

            # Verificar duplicatas fuzzy
            similar_item, similarity = self.find_similar_items(merged, new_item)

            if similar_item and similarity >= self.SIMILARITY_THRESHOLD:
                # Item muito similar - considerar duplicata
                duplicates_found += 1
                logger.debug(
                    f"Item similar encontrado: '{new_item}' ~= '{similar_item}' (score: {similarity:.2f})"
                )

                # Se o novo item é mais detalhado, substituir
                if len(new_item) > len(similar_item) * 1.2:  # 20% mais detalhado
                    merged[merged.index(similar_item)] = new_item
                    self.merge_stats["similarity_improvements"] += 1
                    logger.debug(
                        f"Substituindo por versão mais detalhada: '{similar_item}' -> '{new_item}'"
                    )

            else:
                # Item único - adicionar
                merged.append(new_item)

        self.merge_stats["duplicates_removed"] += duplicates_found
        return merged

    def merge_dict_lists(
        self, existing: List[Dict], new: List[Dict], key_field: str = "name"
    ) -> List[Dict]:
        """
        Merge listas de dicionários usando campo chave.
        """
        merged = existing.copy()

        for new_dict in new:
            if not new_dict or key_field not in new_dict:
                continue

            new_key = new_dict[key_field]

            # Procurar por chave exata
            existing_item = None
            for item in merged:
                if item.get(key_field) == new_key:
                    existing_item = item
                    break

            if existing_item:
                # Merge campos do dicionário
                self.merge_stats["items_merged"] += 1
                for field, value in new_dict.items():
                    if field not in existing_item or not existing_item[field]:
                        existing_item[field] = value
                    elif existing_item[field] != value:
                        # Conflito - usar estratégia de resolução
                        resolved_value = self.resolve_field_conflict(
                            f"{key_field}.{field}", existing_item[field], value
                        )
                        existing_item[field] = resolved_value
            else:
                # Procurar por similaridade fuzzy
                similar_item = None
                best_score = 0.0

                for item in merged:
                    if key_field in item:
                        score = self.calculate_similarity(new_key, item[key_field])
                        if score > best_score and score >= self.SIMILARITY_THRESHOLD:
                            similar_item = item
                            best_score = score

                if similar_item:
                    # Item similar encontrado - merge
                    self.merge_stats["similarity_improvements"] += 1
                    logger.debug(
                        f"Fazendo merge com item similar: '{new_key}' ~= '{similar_item[key_field]}' (score: {best_score:.2f})"
                    )

                    for field, value in new_dict.items():
                        if field not in similar_item or not similar_item[field]:
                            similar_item[field] = value
                else:
                    # Item novo - adicionar
                    merged.append(new_dict)

        return merged

    def resolve_field_conflict(self, field_path: str, existing: Any, new: Any) -> Any:
        """
        Resolve conflito entre valores de campo.
        """
        # Estratégia 1: Se novo valor é mais detalhado, usar ele
        if isinstance(existing, str) and isinstance(new, str):
            if len(new) > len(existing) * 1.5:  # 50% mais detalhado
                self.conflicts.append(
                    MergeConflict(
                        field_path=field_path,
                        existing_value=existing,
                        new_value=new,
                        similarity_score=self.calculate_similarity(existing, new),
                        resolution_strategy="more_detailed",
                    )
                )
                return new

        # Estratégia 2: Se valores são similares, manter existente
        if isinstance(existing, str) and isinstance(new, str):
            similarity = self.calculate_similarity(existing, new)
            if similarity >= self.SIMILARITY_THRESHOLD:
                return existing

        # Estratégia 3: Se existente está vazio, usar novo
        if not existing and new:
            return new

        # Estratégia 4: Para números, usar o maior (assumindo que é mais atual)
        if isinstance(existing, (int, float)) and isinstance(new, (int, float)):
            resolved = max(existing, new)
            if resolved != existing:
                self.conflicts.append(
                    MergeConflict(
                        field_path=field_path,
                        existing_value=existing,
                        new_value=new,
                        similarity_score=1.0,
                        resolution_strategy="max_value",
                    )
                )
            return resolved

        # Default: manter existente
        self.conflicts.append(
            MergeConflict(
                field_path=field_path,
                existing_value=existing,
                new_value=new,
                similarity_score=0.0,
                resolution_strategy="keep_existing",
            )
        )
        self.merge_stats["conflicts_resolved"] += 1
        return existing

    def intelligent_merge(
        self, existing_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Faz merge inteligente de dois dicionários de dados.
        """
        logger.info("Iniciando merge inteligente de dados")

        # Reset stats
        self.merge_stats = {
            "items_merged": 0,
            "duplicates_removed": 0,
            "conflicts_resolved": 0,
            "similarity_improvements": 0,
        }
        self.conflicts.clear()

        merged = existing_data.copy()

        for field, new_value in new_data.items():
            if not new_value:  # Skip empty/None values
                continue

            if field not in merged or not merged[field]:
                # Campo não existe ou está vazio - adicionar
                merged[field] = new_value
                continue

            existing_value = merged[field]

            # Estratégias específicas por tipo de campo
            if field in self.LIST_FIELDS:
                if isinstance(existing_value, list) and isinstance(new_value, list):
                    if all(isinstance(item, str) for item in existing_value + new_value):
                        # Lista de strings - merge com deduplicação
                        merged[field] = self.merge_string_lists(existing_value, new_value)
                    elif all(isinstance(item, dict) for item in existing_value + new_value):
                        # Lista de dicts - merge por campo chave
                        key_field = self.infer_key_field(existing_value + new_value)
                        merged[field] = self.merge_dict_lists(existing_value, new_value, key_field)
                    else:
                        # Lista mista - concatenar sem duplicatas exatas
                        merged[field] = list(set(existing_value + new_value))

            elif field in self.OVERWRITEABLE_FIELDS:
                # Campos que podem ser sobrescritos
                resolved_value = self.resolve_field_conflict(field, existing_value, new_value)
                merged[field] = resolved_value

            elif isinstance(existing_value, dict) and isinstance(new_value, dict):
                # Dicionários - merge recursivo
                merged[field] = self.intelligent_merge(existing_value, new_value)

            elif isinstance(existing_value, list) and isinstance(new_value, list):
                # Listas genéricas - concatenar sem duplicatas
                merged[field] = existing_value + [
                    item for item in new_value if item not in existing_value
                ]

            else:
                # Outros tipos - usar estratégia de resolução
                resolved_value = self.resolve_field_conflict(field, existing_value, new_value)
                merged[field] = resolved_value

        logger.info(
            "Merge inteligente concluído",
            extra={"stats": self.merge_stats, "conflicts_count": len(self.conflicts)},
        )

        return merged

    def infer_key_field(self, dict_list: List[Dict]) -> str:
        """
        Infere qual campo usar como chave para merge de dicionários.
        """
        common_fields = set()

        if dict_list:
            common_fields = set(dict_list[0].keys())
            for item in dict_list[1:]:
                common_fields &= set(item.keys())

        # Prioridades de campos chave
        key_priorities = ["name", "nome", "id", "title", "titulo", "type", "tipo"]

        for key_field in key_priorities:
            if key_field in common_fields:
                return key_field

        # Fallback para primeiro campo comum
        return next(iter(common_fields)) if common_fields else "name"

    def get_merge_report(self) -> Dict[str, Any]:
        """
        Retorna relatório detalhado do merge.
        """
        return {
            "statistics": self.merge_stats,
            "conflicts": [
                {
                    "field": conflict.field_path,
                    "similarity": conflict.similarity_score,
                    "strategy": conflict.resolution_strategy,
                    "existing_preview": str(conflict.existing_value)[:100],
                    "new_preview": str(conflict.new_value)[:100],
                }
                for conflict in self.conflicts
            ],
            "total_conflicts": len(self.conflicts),
            "merge_efficiency": (
                self.merge_stats["duplicates_removed"] + self.merge_stats["similarity_improvements"]
            )
            / max(1, self.merge_stats["items_merged"] + self.merge_stats["duplicates_removed"]),
        }


# Funções de conveniência
def merge_requirements_data(
    existing: Dict[str, Any], new: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Função de conveniência para merge de dados de requisitos.

    Returns:
        Tuple (dados_merged, relatorio_merge)
    """
    merger = IntelligentMerger()
    merged_data = merger.intelligent_merge(existing, new)
    report = merger.get_merge_report()

    return merged_data, report


def deduplicate_list(items: List[str], similarity_threshold: float = 0.85) -> List[str]:
    """
    Remove duplicatas de uma lista usando similaridade fuzzy.
    """
    merger = IntelligentMerger()
    merger.SIMILARITY_THRESHOLD = similarity_threshold

    return merger.merge_string_lists([], items)


# Exemplo de uso
if __name__ == "__main__":
    # Teste básico
    existing = {
        "features_must": ["Sistema de login", "Dashboard principal", "Relatórios básicos"],
        "integracoes": [
            {"name": "Stripe", "type": "payment", "purpose": "Processamento de pagamentos"}
        ],
    }

    new = {
        "features_must": [
            "Sistema de autenticação",  # Similar a "Sistema de login"
            "Dashboard principal",  # Duplicata exata
            "Relatórios avançados",  # Novo
            "Notificações por email",  # Novo
        ],
        "integracoes": [
            {
                "name": "Stripe",
                "type": "payment",
                "purpose": "Pagamentos com cartão de crédito",
            },  # Merge
            {"name": "SendGrid", "type": "email", "purpose": "Envio de emails"},  # Novo
        ],
    }

    merged_data, report = merge_requirements_data(existing, new)

    print("Dados merged:")
    print(json.dumps(merged_data, indent=2, ensure_ascii=False))

    print("\nRelatório de merge:")
    print(json.dumps(report, indent=2, ensure_ascii=False))
