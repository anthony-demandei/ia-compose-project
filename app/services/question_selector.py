"""
Seletor inteligente de perguntas usando embeddings e IA.
Escolhe até 10 perguntas mais relevantes baseado no texto de intake.
"""

import yaml
import json
import hashlib
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from openai import AsyncOpenAI
from app.models.intake import Question, QuestionSelectionResult, QuestionCondition
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class QuestionSelector:
    """
    Seleciona perguntas inteligentemente usando:
    1. Embeddings para similaridade semântica
    2. Classificação LLM para tags
    3. Scoring ponderado
    4. Diversidade de estágios
    """

    def __init__(self, api_key: str, catalog_path: Optional[str] = None):
        from app.utils.config import get_settings

        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key)
        self.embedding_model = settings.embedding_model
        self.classification_model = settings.classification_model

        # Carregar catálogo de perguntas V2 (sem perguntas de texto)
        if catalog_path is None:
            catalog_path = Path(__file__).parent.parent / "data" / "question_catalog_v2.yaml"
        self.catalog = self._load_catalog(catalog_path)

        # Cache de embeddings
        self.embedding_cache = {}

        # Configurações
        self.max_questions = 10
        self.max_per_stage = 3  # Máximo de perguntas por estágio
        self.conditional_slots = 2  # Slots reservados para condicionais

    def _load_catalog(self, path: Path) -> List[Question]:
        """Carrega catálogo de perguntas do YAML."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            questions = []
            for q_data in data.get("catalog", []):
                # Converter condições se existirem
                condition = None
                if q_data.get("condition"):
                    condition = QuestionCondition(**q_data["condition"])

                question = Question(
                    id=q_data["id"],
                    text=q_data["text"],
                    type=q_data["type"],
                    stage=q_data["stage"],
                    options=q_data.get("options", []),
                    tags=q_data.get("tags", []),
                    required=q_data.get("required", False),
                    weight=q_data.get("weight", 0),
                    condition=condition,
                    version=q_data.get("version", 1),
                )
                questions.append(question)

            logger.info(f"Carregadas {len(questions)} perguntas do catálogo")
            return questions

        except Exception as e:
            logger.error(f"Erro ao carregar catálogo: {str(e)}")
            return []

    async def select_questions(self, intake_text: str) -> QuestionSelectionResult:
        """
        Seleciona até 10 perguntas mais relevantes para o texto de intake.

        Args:
            intake_text: Descrição inicial do projeto pelo cliente

        Returns:
            QuestionSelectionResult com IDs selecionados e metadados
        """
        try:
            # 1. Separar perguntas obrigatórias (required=true)
            required_questions = [q for q in self.catalog if q.required]
            optional_questions = [q for q in self.catalog if not q.required]

            # 2. Classificar tags do texto
            tags = await self._classify_tags(intake_text)
            logger.info(f"Tags identificadas: {tags}")

            # 3. Gerar embedding do texto de intake
            intake_embedding = await self._get_embedding(intake_text)

            # 4. Calcular scores para perguntas opcionais
            scored_questions = []
            similarity_scores = {}

            for question in optional_questions:
                # Calcular similaridade semântica
                q_embedding = await self._get_question_embedding(question)
                similarity = self._cosine_similarity(intake_embedding, q_embedding)

                # Bonus por tags matching
                tag_bonus = sum(0.15 for tag in tags if tag in question.tags)

                # Peso da pergunta
                weight_bonus = question.weight * 0.001

                # Score final
                total_score = similarity + tag_bonus + weight_bonus

                scored_questions.append((total_score, question))
                similarity_scores[question.id] = round(similarity, 3)

            # 5. Ordenar por score
            scored_questions.sort(key=lambda x: x[0], reverse=True)

            # 6. Selecionar com diversidade de estágios
            selected_optional = self._select_with_diversity(
                scored_questions,
                max_questions=self.max_questions - len(required_questions) - self.conditional_slots,
            )

            # 7. Combinar required + selected
            selected_ids = [q.id for q in required_questions]
            selected_ids.extend([q.id for q in selected_optional])

            # 8. Adicionar algumas condicionais comuns
            conditional_ids = self._get_common_conditionals(selected_ids)
            selected_ids.extend(conditional_ids[: self.conditional_slots])

            # Metadados da seleção
            metadata = {
                "tags_identified": tags,
                "similarity_scores": similarity_scores,
                "total_candidates": len(self.catalog),
                "required_count": len(required_questions),
                "optional_selected": len(selected_optional),
                "conditional_reserved": len(conditional_ids[: self.conditional_slots]),
            }

            logger.info(f"Selecionadas {len(selected_ids)} perguntas: {selected_ids}")

            return QuestionSelectionResult(
                selected_ids=selected_ids[: self.max_questions], selection_metadata=metadata
            )

        except Exception as e:
            logger.error(f"Erro na seleção de perguntas: {str(e)}")
            # Fallback: retornar perguntas core
            fallback_ids = [q.id for q in self.catalog if q.required][: self.max_questions]
            return QuestionSelectionResult(
                selected_ids=fallback_ids, selection_metadata={"error": str(e), "fallback": True}
            )

    async def _classify_tags(self, intake_text: str) -> List[str]:
        """Classifica o texto em tags pré-definidas usando LLM."""
        try:
            allowed_tags = [
                "ecommerce",
                "marketplace",
                "b2b",
                "b2c",
                "educacao",
                "saude",
                "financas",
                "logistica",
                "conteudo",
                "social",
                "assinatura",
                "pagamento",
                "geo",
                "chat",
                "relatorio",
                "api",
                "admin",
                "mobile",
                "web",
                "desktop",
                "offline",
                "realtime",
                "ai",
            ]

            prompt = f"""
            Texto: "{intake_text[:500]}"
            
            Tags permitidas:
            {json.dumps(allowed_tags)}
            
            Responda APENAS com JSON:
            {{"tags": ["..."], "confidence": 0.0}}
            """

            response = await self.client.chat.completions.create(
                model=self.classification_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um classificador. Retorne apenas JSON puro.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("tags", [])

        except Exception as e:
            logger.error(f"Erro na classificação de tags: {str(e)}")
            return []

    async def _get_embedding(self, text: str) -> np.ndarray:
        """Gera embedding para um texto."""
        try:
            # Check cache
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash]

            # Generate embedding
            response = await self.client.embeddings.create(
                model=self.embedding_model, input=text[:8000]  # Limitar tamanho
            )

            embedding = np.array(response.data[0].embedding)

            # Cache it
            self.embedding_cache[text_hash] = embedding

            return embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {str(e)}")
            return np.zeros(1536)  # Fallback

    async def _get_question_embedding(self, question: Question) -> np.ndarray:
        """Gera ou recupera embedding de uma pergunta."""
        # Usar embedding pré-computado se disponível
        if question.embedding:
            return np.array(question.embedding)

        # Gerar embedding combinando texto + tags
        combined_text = f"{question.text} {' '.join(question.tags)}"
        return await self._get_embedding(combined_text)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcula similaridade de cosseno entre dois vetores."""
        if vec1.size == 0 or vec2.size == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _select_with_diversity(
        self, scored_questions: List[Tuple[float, Question]], max_questions: int
    ) -> List[Question]:
        """
        Seleciona perguntas garantindo diversidade de estágios.
        Evita muitas perguntas do mesmo estágio.
        """
        selected = []
        stage_counts = {}

        for score, question in scored_questions:
            if len(selected) >= max_questions:
                break

            # Verificar limite por estágio
            stage = question.stage
            if stage_counts.get(stage, 0) >= self.max_per_stage:
                continue

            selected.append(question)
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        return selected

    def _get_common_conditionals(self, selected_ids: List[str]) -> List[str]:
        """
        Retorna IDs de perguntas condicionais comuns que podem ser úteis.
        Baseado nas perguntas já selecionadas.
        """
        conditionals = []

        # Se tem Q_PUBLICO, adicionar Q_PROFISSIONAIS_DETALHE
        if "Q_PUBLICO" in selected_ids:
            conditionals.append("Q_PROFISSIONAIS_DETALHE")

        # Se tem Q_PERMISSOES, adicionar Q_PERMISSOES_DESC
        if "Q_PERMISSOES" in selected_ids:
            conditionals.append("Q_PERMISSOES_DESC")

        # Se tem Q_AUTH, adicionar Q_AUTH_OUTRO_DESC
        if "Q_AUTH" in selected_ids:
            conditionals.append("Q_AUTH_OUTRO_DESC")

        # Se tem finalidade ecommerce, garantir Q_PAGTO_GATEWAY
        if "Q_FINALIDADE" in selected_ids:
            conditionals.append("Q_PAGTO_GATEWAY")

        return conditionals

    def evaluate_condition(
        self, condition: Optional[QuestionCondition], answers: Dict[str, Any]
    ) -> bool:
        """
        Avalia se uma condição é satisfeita dado as respostas atuais.

        Args:
            condition: Condição a avaliar
            answers: Dicionário de respostas {question_id: value}

        Returns:
            True se a condição é satisfeita ou não existe
        """
        if not condition:
            return True

        def evaluate_single(expr: Dict[str, Any]) -> bool:
            """Avalia uma expressão única."""
            q_id = expr.get("q")
            op = expr.get("op")
            expected = expr.get("v")

            if q_id not in answers:
                return False

            actual = answers[q_id]

            if op == "in":
                if isinstance(actual, list):
                    return any(v in expected for v in actual)
                return actual in expected
            elif op == "eq":
                return actual == expected
            elif op == "neq":
                return actual != expected

            return False

        # Avaliar condições ALL
        if condition.all:
            return all(evaluate_single(expr) for expr in condition.all)

        # Avaliar condições ANY
        if condition.any:
            return any(evaluate_single(expr) for expr in condition.any)

        return True

    def get_next_questions(
        self, selected_ids: List[str], answers: Dict[str, Any], batch_size: int = 3
    ) -> List[str]:
        """
        Retorna próximas perguntas a serem exibidas,
        considerando condições e respostas já dadas.

        Args:
            selected_ids: IDs de todas as perguntas selecionadas
            answers: Respostas já fornecidas
            batch_size: Quantas perguntas retornar

        Returns:
            Lista com IDs das próximas perguntas
        """
        next_questions = []

        for q_id in selected_ids:
            # Pular se já foi respondida
            if q_id in answers:
                continue

            # Encontrar pergunta no catálogo
            question = next((q for q in self.catalog if q.id == q_id), None)
            if not question:
                continue

            # Verificar se condição é satisfeita
            if self.evaluate_condition(question.condition, answers):
                next_questions.append(q_id)

                if len(next_questions) >= batch_size:
                    break

        return next_questions
