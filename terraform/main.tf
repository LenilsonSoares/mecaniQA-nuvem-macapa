resource "kubernetes_namespace_v1" "mecaniqa" {
  metadata {
    name = "mecaniqa"
  }
}

resource "kubernetes_secret_v1" "mecaniqa" {
  metadata {
    name      = "mecaniqa-secrets"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }

  data = {
    "mysql-root-password" = var.mysql_root_password
  }

  type = "Opaque"
}

resource "kubernetes_persistent_volume_claim_v1" "mysql" {
  metadata {
    name      = "mysql-data"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = { storage = "5Gi" }
    }
  }
}

resource "kubernetes_persistent_volume_claim_v1" "redis" {
  metadata {
    name      = "redis-data"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = { storage = "2Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "mysql" {
  metadata {
    name      = "mysql"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }

  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "mysql" }
    }

    template {
      metadata {
        labels = { app = "mysql" }
      }
      spec {
        container {
          name  = "mysql"
          image = "mysql:8.0"
          port {
            container_port = 3306
          }
          env {
            name = "MYSQL_ROOT_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.mecaniqa.metadata[0].name
                key  = "mysql-root-password"
              }
            }
          }
          env {
            name  = "MYSQL_DATABASE"
            value = "mecaniqa_db"
          }
          volume_mount {
            name       = "mysql-storage"
            mount_path = "/var/lib/mysql"
          }
          startup_probe {
            tcp_socket {
              port = 3306
            }
            period_seconds    = 10
            failure_threshold = 30
          }
          readiness_probe {
            tcp_socket {
              port = 3306
            }
            initial_delay_seconds = 10
            period_seconds        = 10
          }
          liveness_probe {
            tcp_socket {
              port = 3306
            }
            initial_delay_seconds = 20
            period_seconds        = 20
          }
          resources {
            requests = { cpu = "250m", memory = "512Mi" }
            limits   = { cpu = "1", memory = "1Gi" }
          }
        }
        volume {
          name = "mysql-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.mysql.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "db" {
  metadata {
    name      = "db"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }
  spec {
    selector = { app = "mysql" }
    port {
      name        = "mysql"
      port        = 3306
      target_port = 3306
    }
    type = "ClusterIP"
  }
}

resource "kubernetes_deployment_v1" "redis" {
  metadata {
    name      = "redis"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "redis" }
    }
    template {
      metadata {
        labels = { app = "redis" }
      }
      spec {
        container {
          name  = "redis"
          image = "redis:alpine"
          args  = ["redis-server", "--appendonly", "yes"]
          port {
            container_port = 6379
          }
          volume_mount {
            name       = "redis-storage"
            mount_path = "/data"
          }
          startup_probe {
            tcp_socket {
              port = 6379
            }
            period_seconds    = 5
            failure_threshold = 12
          }
          readiness_probe {
            tcp_socket {
              port = 6379
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
          liveness_probe {
            tcp_socket {
              port = 6379
            }
            initial_delay_seconds = 15
            period_seconds        = 20
          }
          resources {
            requests = { cpu = "50m", memory = "64Mi" }
            limits   = { cpu = "250m", memory = "256Mi" }
          }
        }
        volume {
          name = "redis-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.redis.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "cache" {
  metadata {
    name      = "cache"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }
  spec {
    selector = { app = "redis" }
    port {
      name        = "redis"
      port        = 6379
      target_port = 6379
    }
    type = "ClusterIP"
  }
}

resource "kubernetes_deployment_v1" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = { app = "java-api" }
    }
    template {
      metadata {
        labels = { app = "java-api" }
      }
      spec {
        container {
          name              = "api"
          image             = var.api_image
          image_pull_policy = "IfNotPresent"
          port {
            container_port = 8080
          }
          startup_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            period_seconds    = 5
            failure_threshold = 12
          }
          env {
            name  = "PORT"
            value = "8080"
          }
          env {
            name  = "DB_HOST"
            value = kubernetes_service_v1.db.metadata[0].name
          }
          env {
            name  = "DB_PORT"
            value = "3306"
          }
          env {
            name  = "REDIS_HOST"
            value = kubernetes_service_v1.cache.metadata[0].name
          }
          env {
            name  = "REDIS_PORT"
            value = "6379"
          }
          readiness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 10
            period_seconds        = 10
          }
          liveness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 20
            period_seconds        = 20
          }
          resources {
            requests = { cpu = "100m", memory = "128Mi" }
            limits   = { cpu = "500m", memory = "384Mi" }
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "api" {
  metadata {
    name      = "api-service"
    namespace = kubernetes_namespace_v1.mecaniqa.metadata[0].name
  }
  spec {
    selector = { app = "java-api" }
    port {
      name        = "http"
      port        = 8080
      target_port = 8080
      node_port   = 30080
    }
    type = "NodePort"
  }
}
