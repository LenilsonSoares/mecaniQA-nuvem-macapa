output "namespace" {
  description = "Namespace criado para o projeto."
  value       = kubernetes_namespace_v1.mecaniqa.metadata[0].name
}

output "api_node_port" {
  description = "NodePort da API."
  value       = kubernetes_service_v1.api.spec[0].port[0].node_port
}
