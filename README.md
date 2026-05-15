# SecureDocs — Suficiência em Segurança Computacional

SecureDocs é um MVP acadêmico de gerenciamento seguro de documentos sensíveis.

O objetivo é demonstrar, de forma pequena e controlada, mecanismos centrais de Segurança Computacional:

- autenticação;
- hash de senha com Argon2id;
- sessão por cookie assinado;
- RBAC com papéis `admin`, `usuario` e `auditor`;
- upload de documentos;
- armazenamento cifrado em repouso;
- download autorizado no backend;
- negação de acesso com HTTP 403;
- logs de auditoria;
- consulta de auditoria por `admin` e `auditor`.

O projeto é um protótipo local para demonstração e defesa acadêmica.

---

## Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Argon2id via `argon2-cffi`
- `cryptography/Fernet` para criptografia simétrica de documentos
- `itsdangerous` para token de sessão assinado
- Pytest
- Ruff

Observação: o CI usa Python 3.12. O ambiente local WSL registrado durante a implementação usa Python 3.10.12. O código é compatível com Python 3.10+.

---

## Estrutura principal

```text
app/
  main.py
  config.py
  database.py
  models.py
  deps.py
  routes/
    auth.py
    documents.py
    audit.py
  security/
    passwords.py
    sessions.py
    crypto.py
  services/
    auth_service.py
    audit_service.py
    document_service.py

scripts/
  init_db.py
  seed.py
  generate_document_crypto_key.py

tests/
private_storage/
```

---

## Configuração local

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Gere uma chave Fernet para `DOCUMENT_CRYPTO_KEY`:

```bash
python -m scripts.generate_document_crypto_key
```

Copie o valor gerado para o campo `DOCUMENT_CRYPTO_KEY` no `.env`.

Exemplo de `.env` local:

```env
APP_ENV=development
APP_SECRET_KEY=trocar-por-segredo-local
DOCUMENT_CRYPTO_KEY=colar-chave-fernet-gerada
DATABASE_URL=sqlite:///./securedocs.db
PRIVATE_STORAGE_DIR=private_storage
SESSION_COOKIE_NAME=securedocs_session
SESSION_COOKIE_SECURE=false
SESSION_MAX_AGE_SECONDS=3600
```

---

## Instalação

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

---

## Inicializar banco

```bash
python -m scripts.init_db
```

---

## Criar usuários de demonstração

```bash
python -m scripts.seed
```

Usuários criados pelo seed:

| Email                      | Papel     | Senha de demonstração |
| -------------------------- | --------- | --------------------- |
| `admin@securedocs.local`   | `admin`   | `Admin123!`           |
| `usuario@securedocs.local` | `usuario` | `Usuario123!`         |
| `auditor@securedocs.local` | `auditor` | `Auditor123!`         |

As senhas são apenas para demonstração local. O banco armazena hash Argon2id, não senha em texto claro.

---

## Rodar servidor local

```bash
uvicorn app.main:app --reload
```

A API ficará disponível localmente no endereço padrão do Uvicorn.

---

## Endpoints principais

### Saúde

```text
GET /health
```

### Autenticação

```text
POST /login
POST /logout
```

### Documentos

```text
POST /documents
GET /documents
GET /documents/{document_id}/download
```

### Auditoria

```text
GET /audit/logs
```

---

## Roteiro rápido de demonstração via curl

### 1. Login válido

```bash
curl -i -c cookies.txt \
  -X POST \
  -F "email=usuario@securedocs.local" \
  -F "password=Usuario123!" \
  http://127.0.0.1:8000/login
```

Resultado esperado:

* HTTP 200;
* cookie de sessão `HttpOnly`;
* log de auditoria de login com sucesso.

### 2. Upload de documento por usuário comum

```bash
printf "conteudo sensivel de teste" > /tmp/documento_teste.txt

curl -i -b cookies.txt \
  -X POST \
  -F "upload=@/tmp/documento_teste.txt;type=text/plain" \
  http://127.0.0.1:8000/documents
```

Resultado esperado:

* HTTP 200;
* metadados do documento retornados;
* arquivo salvo cifrado em `private_storage`.

### 3. Listar documentos visíveis

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/documents
```

Resultado esperado:

* usuário vê documentos que pode acessar.

### 4. Download autorizado

Substitua `1` pelo ID retornado no upload:

```bash
curl -i -b cookies.txt \
  http://127.0.0.1:8000/documents/1/download
```

Resultado esperado:

* HTTP 200;
* conteúdo original retornado;
* log de auditoria de download com sucesso.

### 5. Login como auditor

```bash
curl -i -c auditor_cookies.txt \
  -X POST \
  -F "email=auditor@securedocs.local" \
  -F "password=Auditor123!" \
  http://127.0.0.1:8000/login
```

### 6. Auditor consulta logs

```bash
curl -i -b auditor_cookies.txt http://127.0.0.1:8000/audit/logs
```

Resultado esperado:

* HTTP 200;
* logs visíveis ao auditor.

### 7. Auditor não consegue fazer upload

```bash
curl -i -b auditor_cookies.txt \
  -X POST \
  -F "upload=@/tmp/documento_teste.txt;type=text/plain" \
  http://127.0.0.1:8000/documents
```

Resultado esperado:

* HTTP 403.

---

## Testes automatizados

Rodar tudo:

```bash
pytest
```

Lint:

```bash
ruff check app scripts tests
```

Validação de sintaxe:

```bash
python -m compileall app scripts tests
```

---

## Relação

| Tópico                     | Onde aparece no MVP                                                 |
| -------------------------- | ------------------------------------------------------------------- |
| Autenticação               | `/login`, `/logout`, serviço de autenticação                        |
| Hash                       | senhas com Argon2id                                                 |
| Autorização                | dependências de autenticação e RBAC                                 |
| Controle de acesso         | papéis `admin`, `usuario`, `auditor`                                |
| Criptografia simétrica     | documentos cifrados com Fernet                                      |
| Auditoria                  | tabela `audit_logs` e rota `/audit/logs`                            |
| Monitoramento básico       | consulta e análise dos logs                                         |
| Ameaças e vulnerabilidades | acesso negado, anti-IDOR, upload controlado                         |
| Política de segurança      | documento próprio do projeto                                        |
| Segurança de rede          | tratada como requisito de produção: TLS, firewall, exposição mínima |
| IDS/IPS/SIEM               | tratados como arquitetura/evolução, não como implementação do MVP   |


---

## Limitações do protótipo

* Não implementa TLS localmente.
* Não implementa firewall real.
* Não implementa IDS/IPS real.
* Não implementa SIEM.
* Não implementa antivírus, sandbox ou DLP para upload.
* Não implementa assinatura digital jurídica.
* Não implementa PKI própria.
* Não implementa alta disponibilidade.
* Não implementa gestão de chaves com KMS ou cofre de segredos.
* Não deve ser usado com dados reais sensíveis.

Essas limitações são intencionais para manter o escopo pequeno e demonstrável. No relatório e na defesa, esses itens devem ser tratados como requisitos arquiteturais, riscos residuais ou evoluções de produção.

---

## Evidências esperadas

* hash Argon2id no banco;
* arquivo cifrado em `private_storage`;
* download autorizado;
* acesso negado com HTTP 403;
* log de login inválido;
* log de acesso negado;
* auditor consultando logs;
* auditor bloqueado ao tentar upload;
* `.env.example` sem segredos reais;
* audit reports numerados demonstrando o histórico de implementação.
