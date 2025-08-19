# API Keys - IA Compose

## 🔐 Chaves de API Geradas

### Desenvolvimento/Testes
```
DEMANDEI_API_KEY=dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313
```

### Produção (Recomendado gerar nova)
Para produção, recomenda-se gerar uma nova chave exclusiva:

```bash
# Gerar nova chave de produção
python3 -c "import secrets; import string; chars = string.ascii_letters + string.digits; key = 'dmnd_prod_' + ''.join(secrets.choice(chars) for _ in range(32)); print(f'DEMANDEI_API_KEY={key}')"
```

## 📝 Formato das Chaves

As chaves seguem o padrão:
- **Prefixo:** `dmnd_prod_` (identifica como chave Demandei de produção)
- **Corpo:** 32 caracteres alfanuméricos aleatórios
- **Tamanho total:** 42 caracteres

## 🔄 Como Usar

### 1. No arquivo `.env`:
```env
DEMANDEI_API_KEY=dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313
```

### 2. Nas requisições à API:
```http
Authorization: Bearer dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313
```

### 3. Exemplo com cURL:
```bash
curl -X POST https://compose.demandei.com.br/v1/project/analyze \
  -H "Authorization: Bearer dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313" \
  -H "Content-Type: application/json" \
  -d '{"project_description": "Sistema de gestão"}'
```

### 4. Exemplo com Python:
```python
import requests

headers = {
    "Authorization": "Bearer dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://compose.demandei.com.br/v1/project/analyze",
    headers=headers,
    json={"project_description": "Sistema de gestão"}
)
```

## ⚠️ Segurança

1. **NUNCA** commite chaves reais no repositório
2. Use variáveis de ambiente ou gerenciadores de secrets
3. Rotacione as chaves regularmente
4. Use chaves diferentes para cada ambiente (dev, staging, prod)
5. Monitore o uso das chaves para detectar acessos não autorizados

## 🔄 Rotação de Chaves

Para rotacionar uma chave:

1. Gere uma nova chave
2. Atualize a configuração no Coolify/servidor
3. Teste com a nova chave
4. Desative a chave antiga após confirmar que tudo funciona

## 📊 Múltiplas Chaves (Opcional)

Se precisar suportar múltiplas chaves simultâneas, você pode modificar o arquivo `app/middleware/auth.py` para aceitar uma lista de chaves válidas:

```python
VALID_API_KEYS = [
    "dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313",
    "dmnd_prod_OUTRA_CHAVE_AQUI",
]
```

---

**Última atualização:** Novembro 2024  
**Chave atual para testes:** `dmnd_prod_BeaVLLyBsQ82ye4CbkeAql7itAtun313`