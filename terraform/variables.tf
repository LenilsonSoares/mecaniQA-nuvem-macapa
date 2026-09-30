variable "kubeconfig_path" {
  description = "Caminho do kubeconfig usado pelo provider Kubernetes."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Contexto Kubernetes alvo."
  type        = string
  default     = "docker-desktop"
}

variable "mysql_root_password" {
  description = "Senha root do MySQL. Informe por TF_VAR_mysql_root_password."
  type        = string
  sensitive   = true
}

variable "api_image" {
  description = "Imagem da API disponível no cluster."
  type        = string
  default     = "mecaniqa-api:1.1"
}
