# OAT 2 — Registro da Sessão de 21/10

**Problema:** Escalonamento Automático (HPA), Alarmes no Grafana e Teste de Estresse  
**Equipe:** Macapá  
**Data:** 21/10/2026  

## Papéis da Sessão

| Papel | Integrante |
| :--- | :--- |
| Piloto | Kayky Ribeiro |
| Copiloto | Lenilson Dias |
| QA | Joab Nascimento |
| Arquiteto | Artur Maia |
| Scrum Master | Douglas Renan |

---

## 1. O Teste de Estresse e Critérios de Sucesso Absoluto

A missão inclui injetar carga simulando sensores IoT para assistir o HPA escalar os Pods enquanto o Grafana dispara os alertas. Para a arquitetura do MecaniQA, o teste é um **sucesso absoluto** quando cumpre:

1. **Reação do HPA (Elasticidade):** O HPA detecta o aumento de CPU (> 60%) e escala o Deployment `mecaniqa-iot` de 1 para até 5 réplicas dinamicamente, sem intervenção manual.
2. **Disparo dos 4 Alarmes no Grafana:**
   - **CPU:** Violação do limiar de uso por núcleo (> 75% da request).
   - **Memória:** Consumo elevado do container (> 80% do limite).
   - **Erros da Aplicação:** Aumento na taxa de leituras rejeitadas (`result="error"` > 5 erros/min).
   - **Sucessos / Volume Injetado:** Pico de requisições de sucesso (`result="success"` > 50 req/min).
3. **Resiliência:** Zero mortes por falta de memória (`OOMKilled`) e zero quedas em `CrashLoopBackOff`. O endpoint `/health` permanece respondendo 200 OK.
4. **Scale Down Gracioso:** Após a cessação da carga, o HPA reduz progressivamente as réplicas de volta para 1 Pod respeitando a janela de estabilização de 60 segundos.

---

## 2. Artefatos Desenvolvidos e Entregues

1. **Manifesto do HPA (`k8s/oat2/hpa.yaml`):**
   - Recursos alvos: 60% de CPU média e 70% de memória média.
   - Limites: `minReplicas: 1`, `maxReplicas: 5`.
   - Política com janela de estabilização de 0s para *scale-up* imediato em testes de estresse.
2. **Provisionamento de Alarmes (`k8s/oat2/grafana-alerting.yaml`):**
   - Quatro regras de alerta nativas do Grafana Unified Alerting provisionadas via ConfigMap e montadas no Deployment do Grafana em `/etc/grafana/provisioning/alerting`.
3. **Gerador e Script de Teste de Estresse:**
   - `scripts/stress_generator.py`: gerador multithread com injeção concorrente de payloads válidos e inválidos.
   - `scripts/stress-test.ps1`: automação PowerShell para disparo de carga com parâmetros `-DurationSeconds`, `-Concurrency` e `-ErrorRatio`.
4. **Coleta de Evidências e Capturas de Tela:**
   - `scripts/capture-evidence.ps1`: dump do HPA (`kubectl describe hpa`), topologia de Pods e eventos do cluster salvos em `out/stress-test/`.
   - `scripts/take_screenshots.py`: automação Playwright para capturar os dashboards e a tela de alertas em `docs/evidencias/`.

---

## 3. Roteiro de Execução para Piloto e Copiloto

No computador com Docker Desktop e Kubernetes ativo:

```powershell
# 1. Aplicar stack completa (Deployments, Services, HPA e Alarmes)
kubectl apply -k k8s/oat2/

# 2. Iniciar túneis locais (em janelas separadas)
kubectl port-forward -n mecaniqa svc/mecaniqa-iot 8000:8000
kubectl port-forward -n mecaniqa svc/grafana 3000:3000

# 3. Monitorar o HPA em tempo real
kubectl get hpa,pods -n mecaniqa -l app=mecaniqa-iot -w

# 4. Disparar injeção de carga IoT (90 segundos)
.\scripts\stress-test.ps1 -BaseUrl "http://127.0.0.1:8000" -DurationSeconds 90 -Concurrency 40 -ErrorRatio 0.20

# 5. Capturar logs e prints das evidências
.\scripts\capture-evidence.ps1
python .\scripts\take_screenshots.py
```
