import random
from datetime import datetime, timezone

from django.http import HttpResponse, JsonResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

# Contadores Prometheus para monitoramento no Grafana
REQUESTS_SUCCESS_TOTAL = Counter(
    "mecaniqa_api_requests_success_total",
    "Total de requisicoes com sucesso (2xx) na API MecaniQA",
    ["endpoint", "status_code"],
)

REQUESTS_ERROR_TOTAL = Counter(
    "mecaniqa_api_requests_error_total",
    "Total de requisicoes com erro (4xx e 5xx) na API MecaniQA",
    ["endpoint", "status_code", "error_class"],
)

REQUESTS_ALL_TOTAL = Counter(
    "mecaniqa_api_requests_total",
    "Total geral de requisicoes na API MecaniQA por classe de status",
    ["endpoint", "status_code", "status_class"],
)

SUCCESS_STATUS_CODES = [200, 200, 200, 201, 202]
CLIENT_ERROR_CODES = [400, 404, 422, 429]
SERVER_ERROR_CODES = [500, 502, 503]

SERVICOS_OFICINA = [
    "troca_de_oleo",
    "manutencao_motor",
    "alinhamento_balanceamento",
    "revisao_freios",
    "diagnostico_eletrico",
]


def health_view(request):
    """Endpoint simples de verificação de saúde da API."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "mecaniqa-oat4-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status=200,
    )


def manutencoes_view(request):
    """
    Endpoint principal monitorado pelo Prometheus/Grafana.

    Retorna aleatoriamente respostas de sucesso (2xx) ou erro (4xx / 5xx)
    e incrementa os contadores Prometheus correspondentes.

    Parâmetro opcional de query string:
      - error_rate (float entre 0.0 e 1.0): probabilidade de gerar erro.
        Padrão: 0.25 (25% de erro, 75% de sucesso).
    """
    endpoint_label = "/api/manutencoes/"

    try:
        error_rate = float(request.GET.get("error_rate", "0.25"))
        error_rate = max(0.0, min(1.0, error_rate))
    except ValueError:
        error_rate = 0.25

    is_error = random.random() < error_rate

    if not is_error:
        status_code = random.choice(SUCCESS_STATUS_CODES)
        REQUESTS_SUCCESS_TOTAL.labels(
            endpoint=endpoint_label,
            status_code=str(status_code),
        ).inc()
        REQUESTS_ALL_TOTAL.labels(
            endpoint=endpoint_label,
            status_code=str(status_code),
            status_class="2xx",
        ).inc()

        return JsonResponse(
            {
                "status": "success",
                "status_code": status_code,
                "servico": random.choice(SERVICOS_OFICINA),
                "oficina_id": random.randint(1, 35),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status_code,
        )

    # Erro: divide entre 4xx (60%) e 5xx (40%)
    if random.random() < 0.6:
        status_code = random.choice(CLIENT_ERROR_CODES)
        error_class = "4xx"
        mensagem = "Erro na requisicao do cliente da oficina."
    else:
        status_code = random.choice(SERVER_ERROR_CODES)
        error_class = "5xx"
        mensagem = "Erro interno temporario no servico de manutencoes."

    REQUESTS_ERROR_TOTAL.labels(
        endpoint=endpoint_label,
        status_code=str(status_code),
        error_class=error_class,
    ).inc()
    REQUESTS_ALL_TOTAL.labels(
        endpoint=endpoint_label,
        status_code=str(status_code),
        status_class=error_class,
    ).inc()

    return JsonResponse(
        {
            "status": "error",
            "status_code": status_code,
            "error_class": error_class,
            "detail": mensagem,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status=status_code,
    )


def metrics_view(request):
    """Expõe as métricas no formato esperado pelo Prometheus."""
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
