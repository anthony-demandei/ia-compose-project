"""
Utilidades para logging seguro que não expõe PII (Personally Identifiable Information).
Implementa mascaramento e redação de dados sensíveis em logs.
"""

import re
import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PIISafeLogger:
    """
    Logger que automaticamente mascara dados sensíveis antes de registrar.
    """

    # Padrões de PII comuns no Brasil
    PII_PATTERNS = {
        "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
        "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
        "phone": re.compile(r"\b(?:\+55\s?)?(?:\(\d{2}\)\s?)?(?:9\s?)?\d{4}-?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "rg": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dXx]\b"),
        "cep": re.compile(r"\b\d{5}-?\d{3}\b"),
        "credit_card": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b"),
        "bank_account": re.compile(
            r"\bagencia\s*:?\s*\d{4}-?\d?\s*conta\s*:?\s*\d{5,8}-?\d\b", re.IGNORECASE
        ),
    }

    # Campos que são considerados sensíveis
    SENSITIVE_FIELDS = {
        "password",
        "senha",
        "token",
        "api_key",
        "secret",
        "private_key",
        "cpf",
        "cnpj",
        "rg",
        "passport",
        "ssn",
        "phone",
        "telefone",
        "email",
        "endereco",
        "address",
        "credit_card",
        "cartao",
        "bank_account",
        "conta_bancaria",
        "pix",
        "nome_completo",
        "full_name",
        "data_nascimento",
        "birth_date",
    }

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)

    def _mask_pii_patterns(self, text: str) -> str:
        """
        Mascara padrões de PII conhecidos no texto.
        """
        if not isinstance(text, str):
            return text

        masked_text = text

        # Mascarar CPF: 123.456.789-01 -> 123.***.**9-01
        masked_text = self.PII_PATTERNS["cpf"].sub(
            lambda m: m.group()[:3] + ".***.**" + m.group()[-3:], masked_text
        )

        # Mascarar CNPJ: 12.345.678/0001-90 -> 12.***.***/**01-90
        masked_text = self.PII_PATTERNS["cnpj"].sub(
            lambda m: m.group()[:2] + ".***.***/**" + m.group()[-5:], masked_text
        )

        # Mascarar telefone: (11) 99999-9999 -> (11) 9****-9999
        masked_text = self.PII_PATTERNS["phone"].sub(
            lambda m: m.group()[:-8] + "*" * 4 + m.group()[-4:], masked_text
        )

        # Mascarar email: user@domain.com -> u***@domain.com
        masked_text = self.PII_PATTERNS["email"].sub(
            lambda m: m.group()[0] + "***@" + m.group().split("@")[1], masked_text
        )

        # Mascarar RG: 12.345.678-9 -> 12.***.***-9
        masked_text = self.PII_PATTERNS["rg"].sub(
            lambda m: m.group()[:2] + ".***.***" + m.group()[-2:], masked_text
        )

        # Mascarar CEP: 01234-567 -> 01***-567
        masked_text = self.PII_PATTERNS["cep"].sub(
            lambda m: m.group()[:2] + "***" + m.group()[-4:], masked_text
        )

        # Mascarar cartão: 1234 5678 9012 3456 -> 1234 **** **** 3456
        masked_text = self.PII_PATTERNS["credit_card"].sub(
            lambda m: m.group()[:4] + " **** ****" + m.group()[-5:], masked_text
        )

        return masked_text

    def _mask_sensitive_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mascara campos sensíveis em dicionários recursivamente.
        """
        if not isinstance(data, dict):
            return data

        masked_data = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Verificar se a chave é sensível
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                if isinstance(value, str) and len(value) > 3:
                    masked_data[key] = value[:1] + "*" * (len(value) - 2) + value[-1:]
                else:
                    masked_data[key] = "[REDACTED]"

            # Processar recursivamente
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_dict(value)
            elif isinstance(value, list):
                masked_data[key] = [
                    self._mask_sensitive_dict(item)
                    if isinstance(item, dict)
                    else self._mask_pii_patterns(str(item))
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                masked_data[key] = self._mask_pii_patterns(value)
            else:
                masked_data[key] = value

        return masked_data

    def _safe_format_message(self, message: str, *args, **kwargs) -> str:
        """
        Formata mensagem de forma segura, mascarando PII.
        """
        try:
            # Formatar argumentos posicionais
            safe_args = []
            for arg in args:
                if isinstance(arg, dict):
                    safe_args.append(self._mask_sensitive_dict(arg))
                elif isinstance(arg, str):
                    safe_args.append(self._mask_pii_patterns(arg))
                else:
                    safe_args.append(arg)

            # Formatar argumentos nomeados
            safe_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, dict):
                    safe_kwargs[key] = self._mask_sensitive_dict(value)
                elif isinstance(value, str):
                    safe_kwargs[key] = self._mask_pii_patterns(value)
                else:
                    safe_kwargs[key] = value

            # Formatar mensagem
            formatted_message = (
                message.format(*safe_args, **safe_kwargs) if (args or kwargs) else message
            )

            # Mascarar qualquer PII restante na mensagem final
            return self._mask_pii_patterns(formatted_message)

        except Exception:
            # Se der erro na formatação, retornar mensagem básica
            return f"[LOG FORMATTING ERROR] {self._mask_pii_patterns(str(message))}"

    def info(self, message: str, *args, **kwargs):
        """Log de informação com PII mascarado."""
        safe_message = self._safe_format_message(message, *args, **kwargs)
        self.logger.info(safe_message)

    def debug(self, message: str, *args, **kwargs):
        """Log de debug com PII mascarado."""
        safe_message = self._safe_format_message(message, *args, **kwargs)
        self.logger.debug(safe_message)

    def warning(self, message: str, *args, **kwargs):
        """Log de warning com PII mascarado."""
        safe_message = self._safe_format_message(message, *args, **kwargs)
        self.logger.warning(safe_message)

    def error(self, message: str, *args, **kwargs):
        """Log de erro com PII mascarado."""
        safe_message = self._safe_format_message(message, *args, **kwargs)
        self.logger.error(safe_message)

    def critical(self, message: str, *args, **kwargs):
        """Log crítico com PII mascarado."""
        safe_message = self._safe_format_message(message, *args, **kwargs)
        self.logger.critical(safe_message)


# Funções de conveniência para criar loggers seguros
def get_pii_safe_logger(name: str) -> PIISafeLogger:
    """
    Cria um logger seguro para PII.
    """
    return PIISafeLogger(name)


def mask_pii_in_text(text: str) -> str:
    """
    Função utilitária para mascarar PII em texto.
    """
    temp_logger = PIISafeLogger("temp")
    return temp_logger._mask_pii_patterns(text)


def mask_pii_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função utilitária para mascarar PII em dicionários.
    """
    temp_logger = PIISafeLogger("temp")
    return temp_logger._mask_sensitive_dict(data)


def create_safe_audit_log(
    event_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> Dict[str, Any]:
    """
    Cria um log de auditoria seguro para compliance.
    """
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "success": success,
        "user_id": user_id[:8] + "***" if user_id and len(user_id) > 8 else user_id,
        "session_id": session_id[:8] + "***" if session_id and len(session_id) > 8 else session_id,
    }

    if data:
        # Mascarar dados sensíveis
        temp_logger = PIISafeLogger("audit")
        audit_entry["data"] = temp_logger._mask_sensitive_dict(data)

    return audit_entry


# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging básico
    logging.basicConfig(level=logging.DEBUG)

    # Criar logger seguro
    safe_logger = get_pii_safe_logger(__name__)

    # Exemplos de dados sensíveis
    sensitive_data = {
        "cpf": "123.456.789-01",
        "email": "usuario@exemplo.com",
        "phone": "(11) 99999-9999",
        "nome_completo": "João da Silva",
        "password": "senha_secreta",
    }

    # Testar logging seguro
    safe_logger.info("Dados do usuário processados: {}", sensitive_data)

    # Testar mascaramento direto
    text_with_pii = "O CPF 123.456.789-01 e email user@domain.com foram processados"
    masked_text = mask_pii_in_text(text_with_pii)
    print(f"Original: {text_with_pii}")
    print(f"Masked: {masked_text}")
