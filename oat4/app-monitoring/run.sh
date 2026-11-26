#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " MecâniQA Automotive Tech — OAT 4 (API + Prometheus + Grafana)"
echo "============================================================"
echo ""

if ! command -v docker > /dev/null 2>&1; then
  echo "[ERRO] O comando 'docker' não foi encontrado no PATH."
  echo "       Instale o Docker Desktop (ou Docker Engine) e tente novamente."
  exit 1
fi

if ! docker info > /dev/null 2>&1; then
  echo "[ERRO] O daemon do Docker não está em execução."
  echo "       Inicie o Docker Desktop (macOS/Windows), Colima/OrbStack ou o serviço 'docker' (Linux)"
  echo "       e aguarde ele ficar ativo antes de executar ./run.sh novamente."
  exit 1
fi

if ! docker compose version > /dev/null 2>&1; then
  echo "[ERRO] O plugin 'docker compose' não está disponível."
  echo "       Atualize o Docker ou instale o Docker Compose v2 e tente novamente."
  exit 1
fi

echo "[1/3] Subindo containers (API Django, Prometheus e Grafana)..."
docker compose up -d --build

echo ""
echo "[2/3] Aguardando a API Django ficar disponível em http://localhost:8000/health/ ..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "      API disponível!"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[ERRO] A API não respondeu após 30 tentativas. Verifique 'docker compose logs api'."
    exit 1
  fi
  sleep 1
done

echo ""
echo "Serviços ativos:"
echo "  - API Django (endpoint):  http://localhost:8000/api/manutencoes/"
echo "  - Métricas Prometheus:    http://localhost:8000/metrics"
echo "  - Prometheus UI:          http://localhost:9090"
echo "  - Grafana UI:             http://localhost:3000  (usuário: admin | senha: admin)"
echo ""
echo "[3/3] Iniciando gerador contínuo de tráfego (2xx, 4xx e 5xx)..."
echo "      (Pressione Ctrl+C para parar o gerador; os containers continuarão rodando.)"
echo ""

python3 scripts/gerar_trafego.py --url http://localhost:8000
