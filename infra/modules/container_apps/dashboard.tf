# The dashboard. Same image as the jobs, different command: one build, one scan,
# one tag, and no second supply chain to keep current.
resource "azurerm_container_app" "dashboard" {
  count = var.dashboard_enabled ? 1 : 0

  name                         = "ca-${var.name_prefix}-dashboard"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  workload_profile_name        = var.workload_profile_name

  identity {
    type         = "UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.user_assigned_identity_id
  }

  dynamic "secret" {
    for_each = var.secrets
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.user_assigned_identity_id
    }
  }

  # Easy Auth reads the client secret from the app's own secret store by name,
  # so it has to be declared here as well as in the auth config. Versionless, so
  # rotating the credential does not require a new revision.
  secret {
    name                = local.client_secret_name
    key_vault_secret_id = azurerm_key_vault_secret.dashboard_client_secret[0].versionless_id
    identity            = var.user_assigned_identity_id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    # Terminate TLS at the ingress and refuse plain HTTP outright, rather than
    # redirecting. A redirect still accepts the first request in clear.
    allow_insecure_connections = false

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    # Scale to zero. The page is read by a person a few times a day, so paying
    # for an idle replica is paying for nothing. The cost is a cold start on the
    # first request, which is the right trade for a dashboard and would be the
    # wrong one for the trading job.
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "dashboard"
      image  = var.image
      cpu    = var.cpu
      memory = var.memory

      command = ["uvicorn"]
      args = [
        "trading_bot.dashboard.app:create_app",
        "--factory",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
      ]

      dynamic "env" {
        for_each = local.common_env
        content {
          name        = env.value.name
          value       = env.value.value
          secret_name = env.value.secret_name
        }
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/healthz"
      }

      # Readiness touches the database, liveness does not. A liveness probe that
      # fails during a database outage makes the platform restart replicas it
      # cannot fix, turning an outage into a restart loop.
      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/readyz"
      }
    }
  }

  tags = var.tags
}
