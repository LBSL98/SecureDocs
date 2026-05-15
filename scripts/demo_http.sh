#!/usr/bin/env bash
set -euo pipefail

DEMO_PORT="${DEMO_PORT:-8001}"
BASE_URL="http://127.0.0.1:${DEMO_PORT}"
DEMO_ROOT="$(mktemp -d)"
SERVER_LOG="${DEMO_ROOT}/uvicorn.log"
USER_COOKIES="${DEMO_ROOT}/user_cookies.txt"
AUDITOR_COOKIES="${DEMO_ROOT}/auditor_cookies.txt"
DOCUMENT_FILE="${DEMO_ROOT}/documento_demo.txt"
DOWNLOAD_FILE="${DEMO_ROOT}/documento_baixado.txt"
AUDITOR_DOWNLOAD_FILE="${DEMO_ROOT}/auditor_download_response.txt"
AUDITOR_UPLOAD_FILE="${DEMO_ROOT}/auditor_upload_response.txt"

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

echo "DEMO_ROOT=${DEMO_ROOT}"
echo "DEMO_BASE_URL=${BASE_URL}"

echo
echo "===== 1. INICIALIZAR BANCO TEMPORARIO ====="
"$PYTHON_BIN" -m scripts.init_db
"$PYTHON_BIN" -m scripts.seed
echo "DEMO_DB_READY=true"

echo
echo "===== 2. SUBIR API LOCAL TEMPORARIA ====="
"$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$DEMO_PORT" > "$SERVER_LOG" 2>&1 &
SERVER_PID="$!"

for attempt in $(seq 1 40); do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "DEMO_HEALTH_OK=true"
    break
  fi

  sleep 0.25

  if [ "$attempt" = "40" ]; then
    echo "DEMO_HEALTH_OK=false"
    echo "===== UVICORN LOG ====="
    cat "$SERVER_LOG"
    exit 1
  fi
done

echo
echo "===== 3. LOGIN COMO USUARIO COMUM ====="
USER_LOGIN_RESPONSE="$(
  curl -sS -c "$USER_COOKIES" \
    -X POST \
    -F "email=usuario@securedocs.local" \
    -F "password=Usuario123!" \
    "${BASE_URL}/login"
)"
echo "USER_LOGIN_RESPONSE=${USER_LOGIN_RESPONSE}"

echo
echo "===== 4. UPLOAD DE DOCUMENTO PELO USUARIO ====="
printf "conteudo sensivel demonstravel\n" > "$DOCUMENT_FILE"

UPLOAD_RESPONSE="$(
  curl -sS -b "$USER_COOKIES" \
    -X POST \
    -F "upload=@${DOCUMENT_FILE};type=text/plain" \
    "${BASE_URL}/documents"
)"
echo "UPLOAD_RESPONSE=${UPLOAD_RESPONSE}"

DOCUMENT_ID="$(
  UPLOAD_RESPONSE="$UPLOAD_RESPONSE" "$PYTHON_BIN" - <<'PY'
import json
import os

response = json.loads(os.environ["UPLOAD_RESPONSE"])
print(response["id"])
PY
)"
echo "UPLOADED_DOCUMENT_ID=${DOCUMENT_ID}"

echo
echo "===== 5. VALIDAR QUE ARMAZENAMENTO ESTA CIFRADO ====="
STORED_FILE_COUNT="$(find "$PRIVATE_STORAGE_DIR" -type f | wc -l)"
echo "PRIVATE_STORAGE_FILE_COUNT=${STORED_FILE_COUNT}"

if grep -R -a -q "conteudo sensivel demonstravel" "$PRIVATE_STORAGE_DIR"; then
  echo "STORAGE_CONTAINS_PLAINTEXT=true"
  exit 1
fi

echo "STORAGE_CONTAINS_PLAINTEXT=false"

echo
echo "===== 6. DOWNLOAD AUTORIZADO PELO DONO ====="
curl -fsS -b "$USER_COOKIES" \
  "${BASE_URL}/documents/${DOCUMENT_ID}/download" \
  -o "$DOWNLOAD_FILE"

cmp -s "$DOCUMENT_FILE" "$DOWNLOAD_FILE"
echo "OWNER_DOWNLOAD_MATCHES_UPLOAD=true"

echo
echo "===== 7. LOGIN COMO AUDITOR ====="
AUDITOR_LOGIN_RESPONSE="$(
  curl -sS -c "$AUDITOR_COOKIES" \
    -X POST \
    -F "email=auditor@securedocs.local" \
    -F "password=Auditor123!" \
    "${BASE_URL}/login"
)"
echo "AUDITOR_LOGIN_RESPONSE=${AUDITOR_LOGIN_RESPONSE}"

echo
echo "===== 8. AUDITOR NAO VE DOCUMENTOS SEM PERMISSAO ====="
AUDITOR_LIST_RESPONSE="$(
  curl -fsS -b "$AUDITOR_COOKIES" \
    "${BASE_URL}/documents"
)"
echo "AUDITOR_LIST_RESPONSE=${AUDITOR_LIST_RESPONSE}"

AUDITOR_LIST_COUNT="$(
  AUDITOR_LIST_RESPONSE="$AUDITOR_LIST_RESPONSE" "$PYTHON_BIN" - <<'PY'
import json
import os

documents = json.loads(os.environ["AUDITOR_LIST_RESPONSE"])
print(len(documents))
PY
)"
echo "AUDITOR_VISIBLE_DOCUMENT_COUNT=${AUDITOR_LIST_COUNT}"
test "$AUDITOR_LIST_COUNT" = "0"

echo
echo "===== 9. AUDITOR NAO BAIXA DOCUMENTO SEM PERMISSAO ====="
AUDITOR_DOWNLOAD_CODE="$(
  curl -sS -o "$AUDITOR_DOWNLOAD_FILE" -w "%{http_code}" \
    -b "$AUDITOR_COOKIES" \
    "${BASE_URL}/documents/${DOCUMENT_ID}/download"
)"
echo "AUDITOR_DOWNLOAD_HTTP_CODE=${AUDITOR_DOWNLOAD_CODE}"
cat "$AUDITOR_DOWNLOAD_FILE"
echo
test "$AUDITOR_DOWNLOAD_CODE" = "403"

echo
echo "===== 10. AUDITOR NAO FAZ UPLOAD ====="
AUDITOR_UPLOAD_CODE="$(
  curl -sS -o "$AUDITOR_UPLOAD_FILE" -w "%{http_code}" \
    -b "$AUDITOR_COOKIES" \
    -X POST \
    -F "upload=@${DOCUMENT_FILE};type=text/plain" \
    "${BASE_URL}/documents"
)"
echo "AUDITOR_UPLOAD_HTTP_CODE=${AUDITOR_UPLOAD_CODE}"
cat "$AUDITOR_UPLOAD_FILE"
echo
test "$AUDITOR_UPLOAD_CODE" = "403"

echo
echo "===== 11. AUDITOR CONSULTA LOGS ====="
AUDIT_LOGS="$(
  curl -fsS -b "$AUDITOR_COOKIES" \
    "${BASE_URL}/audit/logs"
)"

AUDIT_LOGS="$AUDIT_LOGS" "$PYTHON_BIN" - <<'PY'
import json
import os

logs = json.loads(os.environ["AUDIT_LOGS"])
seen = {(item["action"], item["outcome"]) for item in logs}

required = {
    ("login", "success"),
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
PY

echo
echo "===== DEMONSTRACAO CONCLUIDA ====="
echo "DEMO_RESULT=success"
