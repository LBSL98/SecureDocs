#!/usr/bin/env bash
set -euo pipefail

DEMO_PORT="${DEMO_PORT:-8001}"
DEMO_CODE_TOUR="${DEMO_CODE_TOUR:-true}"
BASE_URL="http://127.0.0.1:${DEMO_PORT}"
DEMO_ROOT="$(mktemp -d)"
SERVER_LOG="${DEMO_ROOT}/uvicorn.log"
USER_COOKIES="${DEMO_ROOT}/user_cookies.txt"
AUDITOR_COOKIES="${DEMO_ROOT}/auditor_cookies.txt"
DOCUMENT_FILE="${DEMO_ROOT}/documento_demo.txt"
DOWNLOAD_FILE="${DEMO_ROOT}/documento_baixado.txt"
NO_COOKIE_BODY="${DEMO_ROOT}/no_cookie_body.json"
BAD_LOGIN_BODY="${DEMO_ROOT}/bad_login_body.json"
USER_LOGIN_BODY="${DEMO_ROOT}/user_login_body.json"
USER_LOGIN_HEADERS="${DEMO_ROOT}/user_login_headers.txt"
UPLOAD_BODY="${DEMO_ROOT}/upload_body.json"
USER_LIST_BODY="${DEMO_ROOT}/user_list_body.json"
AUDITOR_LOGIN_BODY="${DEMO_ROOT}/auditor_login_body.json"
AUDITOR_LIST_BODY="${DEMO_ROOT}/auditor_list_body.json"
AUDITOR_DOWNLOAD_BODY="${DEMO_ROOT}/auditor_download_body.json"
AUDITOR_UPLOAD_BODY="${DEMO_ROOT}/auditor_upload_body.json"
AUDIT_LOGS_BODY="${DEMO_ROOT}/audit_logs_body.json"

if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="python"
  fi
fi

cleanup() {
  if [ -n "${SERVER_PID:-}" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi

  rm -rf "$DEMO_ROOT"
}

trap cleanup EXIT

export APP_ENV="demo"
export APP_SECRET_KEY="${APP_SECRET_KEY:-demo-local-secret-not-for-production}"
export DOCUMENT_CRYPTO_KEY="${DOCUMENT_CRYPTO_KEY:-$("$PYTHON_BIN" -m scripts.generate_document_crypto_key)}"
export DATABASE_URL="sqlite:///${DEMO_ROOT}/securedocs_demo.db"
export PRIVATE_STORAGE_DIR="${DEMO_ROOT}/private_storage"
export SESSION_COOKIE_NAME="securedocs_session"
export SESSION_COOKIE_SECURE="false"
export SESSION_MAX_AGE_SECONDS="3600"

line() {
  printf '%s\n' "----------------------------------------------------------------"
}

step() {
  echo
  line
  printf 'ETAPA %s - %s\n' "$1" "$2"
  line
}

show_params() {
  echo "Parametros:"
  for item in "$@"; do
    printf '  %s\n' "$item"
  done
}

show_tour() {
  if [ "$DEMO_CODE_TOUR" != "true" ]; then
    return
  fi

  echo "Tour do codigo:"
  for item in "$@"; do
    printf '  %s\n' "$item"
  done
}

show_command() {
  echo "Comando executado:"
  for item in "$@"; do
    printf '  %s\n' "$item"
  done
}

show_file() {
  local file_path="$1"

  if [ ! -s "$file_path" ]; then
    echo "  <sem corpo de resposta>"
    return
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    printf '  %s\n' "$line"
  done < "$file_path"
}

show_http_result() {
  local http_code="$1"
  local body_file="$2"

  echo "Resultado:"
  printf '  HTTP_CODE=%s\n' "$http_code"
  echo "  BODY:"
  show_file "$body_file"
}

expect_equals() {
  local actual="$1"
  local expected="$2"
  local label="$3"

  if [ "$actual" != "$expected" ]; then
    printf 'VALIDACAO=%s falhou esperado=%s obtido=%s\n' "$label" "$expected" "$actual"
    exit 1
  fi

  printf 'VALIDACAO=%s ok esperado=%s obtido=%s\n' "$label" "$expected" "$actual"
}

pause_for_explanation() {
  local next_step="$1"

  if [ "${DEMO_AUTO_ADVANCE:-false}" = "true" ]; then
    printf '\nPAUSA_PULADA=DEMO_AUTO_ADVANCE proxima_etapa="%s"\n' "$next_step"
    return
  fi

  echo
  echo "PAUSA=true"
  printf '>>> Pressione Enter para executar: %s\n' "$next_step"
  read -r _
}

json_value() {
  local file_path="$1"
  local key="$2"

  RESPONSE_FILE="$file_path" RESPONSE_KEY="$key" "$PYTHON_BIN" - <<'PY'
import json
import os

with open(os.environ["RESPONSE_FILE"], encoding="utf-8") as response_file:
    data = json.load(response_file)

print(data[os.environ["RESPONSE_KEY"]])
PY
}

json_count() {
  local file_path="$1"

  RESPONSE_FILE="$file_path" "$PYTHON_BIN" - <<'PY'
import json
import os

with open(os.environ["RESPONSE_FILE"], encoding="utf-8") as response_file:
    data = json.load(response_file)

print(len(data))
PY
}

echo "DEMO_GUIADA=SecureDocs"
echo "DEMO_ROOT=${DEMO_ROOT}"
echo "DEMO_BASE_URL=${BASE_URL}"
echo "PYTHON_BIN=${PYTHON_BIN}"
echo "DEMO_CODE_TOUR=${DEMO_CODE_TOUR}"
echo
echo "Use Enter para avancar quando terminar a explicacao."
pause_for_explanation "1. inicializar banco temporario"

step "1" "INICIALIZAR BANCO TEMPORARIO"
show_tour \
  "scripts/init_db.py: cria as tabelas a partir das models SQLAlchemy." \
  "scripts/seed.py: cria usuarios de demo com papeis admin, usuario e auditor." \
  "app/models.py: define users, documents, document_permissions e audit_logs."
show_params \
  "DATABASE_URL=${DATABASE_URL}" \
  "PRIVATE_STORAGE_DIR=${PRIVATE_STORAGE_DIR}" \
  "usuarios_seed=admin,usuario,auditor"
show_command \
  "${PYTHON_BIN} -m scripts.init_db" \
  "${PYTHON_BIN} -m scripts.seed"
"$PYTHON_BIN" -m scripts.init_db
"$PYTHON_BIN" -m scripts.seed
echo "Resultado:"
echo "  DEMO_DB_READY=true"
pause_for_explanation "2. subir API local temporaria"

step "2" "SUBIR API LOCAL TEMPORARIA"
show_tour \
  "app/main.py: monta a aplicacao FastAPI e inclui os routers." \
  "app/config.py: le variaveis como DATABASE_URL, storage e chave criptografica." \
  "app/database.py: configura engine e sessoes do banco usado pela demo."
show_params \
  "host=127.0.0.1" \
  "port=${DEMO_PORT}" \
  "healthcheck=${BASE_URL}/health" \
  "server_log=${SERVER_LOG}"
show_command \
  "${PYTHON_BIN} -m uvicorn app.main:app --host 127.0.0.1 --port ${DEMO_PORT}" \
  "curl --connect-timeout 1 --max-time 2 -fsS ${BASE_URL}/health"
"$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$DEMO_PORT" > "$SERVER_LOG" 2>&1 &
SERVER_PID="$!"

for attempt in $(seq 1 40); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Resultado:"
    echo "  DEMO_HEALTH_OK=false"
    echo "  SERVER_STARTED=false"
    echo "  Possivel causa: a porta ${DEMO_PORT} ja estava em uso por uma execucao anterior."
    echo "  UVICORN_LOG:"
    show_file "$SERVER_LOG"
    exit 1
  fi

  if curl --connect-timeout 1 --max-time 2 -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "Resultado:"
    echo "  DEMO_HEALTH_OK=true"
    echo "  SERVER_PID=${SERVER_PID}"
    break
  fi

  sleep 0.25

  if [ "$attempt" = "40" ]; then
    echo "Resultado:"
    echo "  DEMO_HEALTH_OK=false"
    echo "  UVICORN_LOG:"
    show_file "$SERVER_LOG"
    exit 1
  fi
done
pause_for_explanation "3. tentar rota protegida sem cookie"

step "3" "FALHA ESPERADA: ROTA PROTEGIDA SEM SESSAO"
show_tour \
  "app/deps.py: require_authenticated_user retorna 401 quando nao ha sessao valida." \
  "app/routes/documents.py: GET /documents depende de usuario autenticado."
show_params \
  "cookie=<nenhum>" \
  "endpoint=${BASE_URL}/documents" \
  "resultado_esperado=HTTP 401"
show_command "curl -sS -o ${NO_COOKIE_BODY} -w %{http_code} ${BASE_URL}/documents"
NO_COOKIE_CODE="$(
  curl -sS -o "$NO_COOKIE_BODY" -w "%{http_code}" \
    "${BASE_URL}/documents"
)"
show_http_result "$NO_COOKIE_CODE" "$NO_COOKIE_BODY"
expect_equals "$NO_COOKIE_CODE" "401" "rota_protegida_sem_cookie"
pause_for_explanation "4. tentar login com senha invalida"

step "4" "FALHA ESPERADA: LOGIN COM SENHA INVALIDA"
show_tour \
  "app/routes/auth.py: POST /login audita falha e retorna 401 para credenciais invalidas." \
  "app/services/auth_service.py: normaliza email e autentica usuario." \
  "app/security/passwords.py: verifica senha contra hash Argon2id."
show_params \
  "email=usuario@securedocs.local" \
  "password=<senha propositalmente invalida>" \
  "endpoint=${BASE_URL}/login" \
  "resultado_esperado=HTTP 401"
show_command \
  "curl -sS -o ${BAD_LOGIN_BODY} -w %{http_code} -X POST" \
  "  -F email=usuario@securedocs.local" \
  "  -F password=SenhaErrada!" \
  "  ${BASE_URL}/login"
BAD_LOGIN_CODE="$(
  curl -sS -o "$BAD_LOGIN_BODY" -w "%{http_code}" \
    -X POST \
    -F "email=usuario@securedocs.local" \
    -F "password=SenhaErrada!" \
    "${BASE_URL}/login"
)"
show_http_result "$BAD_LOGIN_CODE" "$BAD_LOGIN_BODY"
expect_equals "$BAD_LOGIN_CODE" "401" "login_invalido"
pause_for_explanation "5. login valido como usuario comum"

step "5" "SUCESSO: LOGIN COMO USUARIO COMUM"
show_tour \
  "app/routes/auth.py: em login valido cria sessao, seta cookie HttpOnly e audita sucesso." \
  "app/security/sessions.py: cria e valida token de sessao assinado." \
  "app/deps.py: recupera usuario atual a partir do cookie nas proximas rotas."
show_params \
  "email=usuario@securedocs.local" \
  "password=Usuario123!" \
  "cookie_saida=${USER_COOKIES}" \
  "endpoint=${BASE_URL}/login" \
  "resultado_esperado=HTTP 200"
show_command \
  "curl -sS -D ${USER_LOGIN_HEADERS} -c ${USER_COOKIES} -o ${USER_LOGIN_BODY} -w %{http_code} -X POST" \
  "  -F email=usuario@securedocs.local" \
  "  -F password=Usuario123!" \
  "  ${BASE_URL}/login"
USER_LOGIN_CODE="$(
  curl -sS -D "$USER_LOGIN_HEADERS" -c "$USER_COOKIES" -o "$USER_LOGIN_BODY" -w "%{http_code}" \
    -X POST \
    -F "email=usuario@securedocs.local" \
    -F "password=Usuario123!" \
    "${BASE_URL}/login"
)"
show_http_result "$USER_LOGIN_CODE" "$USER_LOGIN_BODY"
expect_equals "$USER_LOGIN_CODE" "200" "login_usuario"
if grep -qi "set-cookie: ${SESSION_COOKIE_NAME}=" "$USER_LOGIN_HEADERS"; then
  echo "VALIDACAO=session_cookie_emitido ok cookie=${SESSION_COOKIE_NAME}"
else
  echo "VALIDACAO=session_cookie_emitido falhou"
  exit 1
fi
pause_for_explanation "6. upload de documento pelo usuario"

step "6" "SUCESSO: UPLOAD DE DOCUMENTO PELO USUARIO"
printf "conteudo sensivel demonstravel\n" > "$DOCUMENT_FILE"
show_tour \
  "app/routes/documents.py: POST /documents recebe o campo multipart upload." \
  "app/deps.py: require_role permite upload apenas para admin e usuario." \
  "app/services/document_service.py: cifra bytes, grava arquivo e salva metadados." \
  "app/services/audit_service.py: registra document_upload success."
show_params \
  "cookie=${USER_COOKIES}" \
  "arquivo=${DOCUMENT_FILE}" \
  "conteudo=conteudo sensivel demonstravel" \
  "endpoint=${BASE_URL}/documents" \
  "resultado_esperado=HTTP 200"
show_command \
  "curl -sS -b ${USER_COOKIES} -o ${UPLOAD_BODY} -w %{http_code} -X POST" \
  "  -F upload=@${DOCUMENT_FILE};type=text/plain" \
  "  ${BASE_URL}/documents"
UPLOAD_CODE="$(
  curl -sS -b "$USER_COOKIES" -o "$UPLOAD_BODY" -w "%{http_code}" \
    -X POST \
    -F "upload=@${DOCUMENT_FILE};type=text/plain" \
    "${BASE_URL}/documents"
)"
show_http_result "$UPLOAD_CODE" "$UPLOAD_BODY"
expect_equals "$UPLOAD_CODE" "200" "upload_usuario"
DOCUMENT_ID="$(json_value "$UPLOAD_BODY" "id")"
echo "DOCUMENT_ID=${DOCUMENT_ID}"
pause_for_explanation "7. listar documentos visiveis ao usuario"

step "7" "SUCESSO: USUARIO LISTA DOCUMENTOS VISIVEIS"
show_tour \
  "app/routes/documents.py: GET /documents lista somente documentos legiveis." \
  "app/services/document_service.py: user_can_read_document aplica admin, dono ou permissao." \
  "app/models.py: Document.owner_id identifica o dono do documento."
show_params \
  "cookie=${USER_COOKIES}" \
  "endpoint=${BASE_URL}/documents" \
  "resultado_esperado=HTTP 200 e pelo menos 1 documento"
show_command "curl -sS -b ${USER_COOKIES} -o ${USER_LIST_BODY} -w %{http_code} ${BASE_URL}/documents"
USER_LIST_CODE="$(
  curl -sS -b "$USER_COOKIES" -o "$USER_LIST_BODY" -w "%{http_code}" \
    "${BASE_URL}/documents"
)"
show_http_result "$USER_LIST_CODE" "$USER_LIST_BODY"
expect_equals "$USER_LIST_CODE" "200" "lista_usuario"
USER_DOCUMENT_COUNT="$(json_count "$USER_LIST_BODY")"
echo "USER_VISIBLE_DOCUMENT_COUNT=${USER_DOCUMENT_COUNT}"
if [ "$USER_DOCUMENT_COUNT" -lt 1 ]; then
  echo "VALIDACAO=usuario_tem_documento_visivel falhou"
  exit 1
fi
echo "VALIDACAO=usuario_tem_documento_visivel ok"
pause_for_explanation "8. validar criptografia em repouso"

step "8" "SUCESSO: STORAGE NAO CONTEM TEXTO CLARO"
show_tour \
  "app/security/crypto.py: encrypt_bytes usa Fernet para cifrar conteudo." \
  "app/services/document_service.py: grava no storage um arquivo .bin com nome UUID." \
  "app/config.py: PRIVATE_STORAGE_DIR aponta para o storage temporario da demo."
show_params \
  "storage=${PRIVATE_STORAGE_DIR}" \
  "texto_buscado=conteudo sensivel demonstravel" \
  "resultado_esperado=plaintext nao encontrado"
show_command \
  "find ${PRIVATE_STORAGE_DIR} -type f | wc -l" \
  "grep -R -a -q 'conteudo sensivel demonstravel' ${PRIVATE_STORAGE_DIR}"
STORED_FILE_COUNT="$(find "$PRIVATE_STORAGE_DIR" -type f | wc -l)"
echo "Resultado:"
echo "  PRIVATE_STORAGE_FILE_COUNT=${STORED_FILE_COUNT}"
if grep -R -a -q "conteudo sensivel demonstravel" "$PRIVATE_STORAGE_DIR"; then
  echo "  STORAGE_CONTAINS_PLAINTEXT=true"
  echo "VALIDACAO=storage_cifrado falhou"
  exit 1
fi
echo "  STORAGE_CONTAINS_PLAINTEXT=false"
echo "VALIDACAO=storage_cifrado ok"
pause_for_explanation "9. download autorizado pelo dono"

step "9" "SUCESSO: DOWNLOAD AUTORIZADO PELO DONO"
show_tour \
  "app/routes/documents.py: GET /documents/{id}/download checa permissao antes de responder." \
  "app/services/document_service.py: read_decrypted_document le o arquivo cifrado e decifra." \
  "app/services/audit_service.py: registra document_download success."
show_params \
  "cookie=${USER_COOKIES}" \
  "document_id=${DOCUMENT_ID}" \
  "endpoint=${BASE_URL}/documents/${DOCUMENT_ID}/download" \
  "arquivo_saida=${DOWNLOAD_FILE}" \
  "resultado_esperado=HTTP 200 e conteudo igual ao upload"
show_command \
  "curl -sS -b ${USER_COOKIES} -o ${DOWNLOAD_FILE} -w %{http_code}" \
  "  ${BASE_URL}/documents/${DOCUMENT_ID}/download" \
  "cmp -s ${DOCUMENT_FILE} ${DOWNLOAD_FILE}"
OWNER_DOWNLOAD_CODE="$(
  curl -sS -b "$USER_COOKIES" -o "$DOWNLOAD_FILE" -w "%{http_code}" \
    "${BASE_URL}/documents/${DOCUMENT_ID}/download"
)"
echo "Resultado:"
echo "  HTTP_CODE=${OWNER_DOWNLOAD_CODE}"
echo "  DOWNLOADED_BODY:"
show_file "$DOWNLOAD_FILE"
expect_equals "$OWNER_DOWNLOAD_CODE" "200" "download_dono"
cmp -s "$DOCUMENT_FILE" "$DOWNLOAD_FILE"
echo "VALIDACAO=owner_download_matches_upload ok"
pause_for_explanation "10. login valido como auditor"

step "10" "SUCESSO: LOGIN COMO AUDITOR"
show_tour \
  "scripts/seed.py: define auditor@securedocs.local com role auditor." \
  "app/routes/auth.py: o mesmo fluxo de login autentica o auditor." \
  "app/models.py: User.role diferencia auditor de usuario comum e admin."
show_params \
  "email=auditor@securedocs.local" \
  "password=Auditor123!" \
  "cookie_saida=${AUDITOR_COOKIES}" \
  "endpoint=${BASE_URL}/login" \
  "resultado_esperado=HTTP 200"
show_command \
  "curl -sS -c ${AUDITOR_COOKIES} -o ${AUDITOR_LOGIN_BODY} -w %{http_code} -X POST" \
  "  -F email=auditor@securedocs.local" \
  "  -F password=Auditor123!" \
  "  ${BASE_URL}/login"
AUDITOR_LOGIN_CODE="$(
  curl -sS -c "$AUDITOR_COOKIES" -o "$AUDITOR_LOGIN_BODY" -w "%{http_code}" \
    -X POST \
    -F "email=auditor@securedocs.local" \
    -F "password=Auditor123!" \
    "${BASE_URL}/login"
)"
show_http_result "$AUDITOR_LOGIN_CODE" "$AUDITOR_LOGIN_BODY"
expect_equals "$AUDITOR_LOGIN_CODE" "200" "login_auditor"
pause_for_explanation "11. auditor lista documentos"

step "11" "SUCESSO COM RESTRICAO: AUDITOR NAO VE DOCUMENTO SEM PERMISSAO"
show_tour \
  "app/services/document_service.py: auditor nao passa como admin, dono ou permissao explicita." \
  "app/routes/documents.py: a lista filtra tudo que user_can_read_document negar." \
  "app/models.py: DocumentPermission existe para leitura explicita, mas nao foi concedida aqui."
show_params \
  "cookie=${AUDITOR_COOKIES}" \
  "endpoint=${BASE_URL}/documents" \
  "resultado_esperado=HTTP 200 com lista vazia"
show_command "curl -sS -b ${AUDITOR_COOKIES} -o ${AUDITOR_LIST_BODY} -w %{http_code} ${BASE_URL}/documents"
AUDITOR_LIST_CODE="$(
  curl -sS -b "$AUDITOR_COOKIES" -o "$AUDITOR_LIST_BODY" -w "%{http_code}" \
    "${BASE_URL}/documents"
)"
show_http_result "$AUDITOR_LIST_CODE" "$AUDITOR_LIST_BODY"
expect_equals "$AUDITOR_LIST_CODE" "200" "lista_auditor"
AUDITOR_DOCUMENT_COUNT="$(json_count "$AUDITOR_LIST_BODY")"
echo "AUDITOR_VISIBLE_DOCUMENT_COUNT=${AUDITOR_DOCUMENT_COUNT}"
expect_equals "$AUDITOR_DOCUMENT_COUNT" "0" "auditor_sem_documentos_visiveis"
pause_for_explanation "12. auditor tenta baixar documento alheio"

step "12" "FALHA ESPERADA: AUDITOR NAO BAIXA DOCUMENTO SEM PERMISSAO"
show_tour \
  "app/routes/documents.py: se user_can_read_document negar, retorna 403 Forbidden." \
  "app/services/document_service.py: evita IDOR porque ID na URL nao substitui permissao." \
  "app/services/audit_service.py: registra document_download denied."
show_params \
  "cookie=${AUDITOR_COOKIES}" \
  "document_id=${DOCUMENT_ID}" \
  "endpoint=${BASE_URL}/documents/${DOCUMENT_ID}/download" \
  "resultado_esperado=HTTP 403"
show_command \
  "curl -sS -b ${AUDITOR_COOKIES} -o ${AUDITOR_DOWNLOAD_BODY} -w %{http_code}" \
  "  ${BASE_URL}/documents/${DOCUMENT_ID}/download"
AUDITOR_DOWNLOAD_CODE="$(
  curl -sS -b "$AUDITOR_COOKIES" -o "$AUDITOR_DOWNLOAD_BODY" -w "%{http_code}" \
    "${BASE_URL}/documents/${DOCUMENT_ID}/download"
)"
show_http_result "$AUDITOR_DOWNLOAD_CODE" "$AUDITOR_DOWNLOAD_BODY"
expect_equals "$AUDITOR_DOWNLOAD_CODE" "403" "download_auditor_negado"
pause_for_explanation "13. auditor tenta fazer upload"

step "13" "FALHA ESPERADA: AUDITOR NAO FAZ UPLOAD"
show_tour \
  "app/deps.py: require_role implementa RBAC comparando User.role com papeis permitidos." \
  "app/routes/documents.py: DOCUMENT_WRITER_DEPENDENCY aceita apenas admin e usuario." \
  "scripts/seed.py: auditor tem role auditor, entao recebe 403 no upload."
show_params \
  "cookie=${AUDITOR_COOKIES}" \
  "arquivo=${DOCUMENT_FILE}" \
  "endpoint=${BASE_URL}/documents" \
  "resultado_esperado=HTTP 403"
show_command \
  "curl -sS -b ${AUDITOR_COOKIES} -o ${AUDITOR_UPLOAD_BODY} -w %{http_code} -X POST" \
  "  -F upload=@${DOCUMENT_FILE};type=text/plain" \
  "  ${BASE_URL}/documents"
AUDITOR_UPLOAD_CODE="$(
  curl -sS -b "$AUDITOR_COOKIES" -o "$AUDITOR_UPLOAD_BODY" -w "%{http_code}" \
    -X POST \
    -F "upload=@${DOCUMENT_FILE};type=text/plain" \
    "${BASE_URL}/documents"
)"
show_http_result "$AUDITOR_UPLOAD_CODE" "$AUDITOR_UPLOAD_BODY"
expect_equals "$AUDITOR_UPLOAD_CODE" "403" "upload_auditor_negado"
pause_for_explanation "14. auditor consulta logs"

step "14" "SUCESSO: AUDITOR CONSULTA LOGS DE AUDITORIA"
show_tour \
  "app/routes/audit.py: GET /audit/logs permite consulta para admin e auditor." \
  "app/services/audit_service.py: cria e lista eventos de auditoria." \
  "app/models.py: AuditLog guarda ator, acao, alvo, resultado, IP, user-agent e detalhes."
show_params \
  "cookie=${AUDITOR_COOKIES}" \
  "endpoint=${BASE_URL}/audit/logs" \
  "eventos_obrigatorios=login success,login failure,document_upload success,document_download success,document_download denied" \
  "resultado_esperado=HTTP 200"
show_command \
  "curl -sS -b ${AUDITOR_COOKIES} -o ${AUDIT_LOGS_BODY} -w %{http_code}" \
  "  ${BASE_URL}/audit/logs"
AUDIT_LOGS_CODE="$(
  curl -sS -b "$AUDITOR_COOKIES" -o "$AUDIT_LOGS_BODY" -w "%{http_code}" \
    "${BASE_URL}/audit/logs"
)"
show_http_result "$AUDIT_LOGS_CODE" "$AUDIT_LOGS_BODY"
expect_equals "$AUDIT_LOGS_CODE" "200" "consulta_auditoria"

AUDIT_LOGS_FILE="$AUDIT_LOGS_BODY" "$PYTHON_BIN" - <<'PY'
import json
import os

with open(os.environ["AUDIT_LOGS_FILE"], encoding="utf-8") as response_file:
    logs = json.load(response_file)

seen = {(item["action"], item["outcome"]) for item in logs}
required = {
    ("login", "success"),
    ("login", "failure"),
    ("document_upload", "success"),
    ("document_download", "success"),
    ("document_download", "denied"),
}

print("audit_log_count=" + str(len(logs)))
print(
    "audit_log_actions="
    + ",".join(item["action"] + ":" + item["outcome"] for item in logs)
)

missing = sorted(required - seen)
if missing:
    print("missing_required_audit_events=" + str(missing))
    raise SystemExit(1)

print("VALIDACAO=eventos_obrigatorios_auditoria ok")
PY

echo
line
echo "DEMONSTRACAO GUIADA CONCLUIDA"
line
echo "DEMO_RESULT=success"
