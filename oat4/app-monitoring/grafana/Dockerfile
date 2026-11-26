FROM grafana/grafana:11.2.2

ENV GF_SECURITY_ADMIN_USER=admin \
    GF_SECURITY_ADMIN_PASSWORD=admin \
    GF_USERS_ALLOW_SIGN_UP=false

# Equipe Macapá: copia todo o provisionamento (fonte de dados + os 2 dashboards da OAT 4),
# para que o Grafana já suba com "Requisições com Sucesso" e "Requisições com Erro".
COPY provisioning /etc/grafana/provisioning

EXPOSE 3000
