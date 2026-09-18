terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
    # azurerm has no resource for Container Apps authentication. azapi is the
    # provider Microsoft maintains for exactly this gap, and it keeps the
    # configuration declarative instead of pushing it into a CLI call that runs
    # outside Terraform and leaves no state.
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
  }
}

# A Consumption-only environment: no workload profile block, so nothing is
# billed while no replica runs. Injecting it into a subnet is what lets the job
# reach a PostgreSQL server that has no public endpoint.
resource "azurerm_container_app_environment" "this" {
  name                = "cae-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location

  infrastructure_subnet_id   = var.infrastructure_subnet_id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  # The dashboard added in a later phase needs public ingress. An internal load
  # balancer would require a VPN or a jump host to reach it, which is a cost and
  # an operational burden this project does not need: the dashboard is protected
  # by Entra ID authentication, not by network position.
  internal_load_balancer_enabled = false

  tags = var.tags

  lifecycle {
    # Azure attaches an implicit Consumption workload profile to the
    # environment after creation. Terraform sees a profile it did not declare
    # and plans to remove it on every run. Removing it is not the intent, and
    # declaring it here would turn this into a workload profiles environment
    # with a different billing model.
    ignore_changes = [workload_profile]
  }
}

locals {
  # Every job shares the same image and the same wiring. Differences are the
  # trigger and the command, which is what the two entries below express.
  common_env = concat(
    [
      for name, value in var.environment_variables : {
        name        = name
        value       = value
        secret_name = null
      }
    ],
    [
      for name, secret in var.secret_environment_variables : {
        name        = name
        value       = null
        secret_name = secret
      }
    ],
  )
}

# Azure validates the image manifest when a job is created and answers
# MANIFEST_UNKNOWN if the tag does not exist. The registry is created by this
# same stack, so on an empty registry the jobs cannot exist yet. The deployment
# pipeline applies once with this off to create the registry, pushes the image,
# then applies again with it on.
resource "azurerm_container_app_job" "trading_cycle" {
  count = var.jobs_enabled ? 1 : 0

  name                         = "caj-${var.name_prefix}-cycle"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  container_app_environment_id = azurerm_container_app_environment.this.id

  # Azure assigns this on creation. Leaving it unset makes every subsequent plan
  # propose clearing it, which is drift that never converges.
  workload_profile_name = var.workload_profile_name

  # One cycle has to finish well inside its own schedule interval, otherwise
  # executions overlap and two processes reason about the same bar.
  replica_timeout_in_seconds = var.replica_timeout_in_seconds

  # One retry, not zero and not five. A transient venue error deserves a second
  # attempt; repeated retries would keep re-running a cycle whose bar has since
  # gone stale, and the staleness guard would reject it anyway.
  replica_retry_limit = 1

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

  schedule_trigger_config {
    cron_expression          = var.cron_expression
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name   = "trading-cycle"
      image  = var.image
      cpu    = var.cpu
      memory = var.memory

      dynamic "env" {
        for_each = local.common_env
        content {
          name        = env.value.name
          value       = env.value.value
          secret_name = env.value.secret_name
        }
      }
    }
  }

  tags = var.tags
}

# Migrations run here rather than from CI because the database has no public
# endpoint: a GitHub-hosted runner cannot reach it. Manual trigger, so a
# deployment starts it explicitly and a failure is visible as a failed
# execution rather than buried in a start-up log.
resource "azurerm_container_app_job" "migrate" {
  count = var.jobs_enabled ? 1 : 0

  name                         = "caj-${var.name_prefix}-migrate"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  container_app_environment_id = azurerm_container_app_environment.this.id

  workload_profile_name = var.workload_profile_name

  replica_timeout_in_seconds = var.replica_timeout_in_seconds
  replica_retry_limit        = 0

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

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "migrate"
      image   = var.image
      cpu     = var.cpu
      memory  = var.memory
      command = ["alembic"]
      args    = ["upgrade", "head"]

      dynamic "env" {
        for_each = local.common_env
        content {
          name        = env.value.name
          value       = env.value.value
          secret_name = env.value.secret_name
        }
      }
    }
  }

  tags = var.tags
}
