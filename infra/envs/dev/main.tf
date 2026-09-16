data "azurerm_client_config" "current" {}

locals {
  name_prefix = "${var.project_short_name}-${var.environment}"

  tags = {
    project       = "azure-trading-platform"
    env           = var.environment
    owner         = var.owner
    "cost-center" = var.cost_center
  }
}

# Key Vault, registry and database names are globally unique and stay reserved
# for a while after deletion. A suffix held in state keeps destroy followed by
# apply working, which this project treats as a requirement.
resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false

  keepers = {
    resource_group = var.resource_group_name
  }
}

resource "random_password" "postgres_admin" {
  length      = 32
  special     = true
  min_lower   = 4
  min_upper   = 4
  min_numeric = 4
  min_special = 2
  # PostgreSQL rejects these in a password passed through a URL, and the
  # connection string is assembled below.
  override_special = "-_=+"

  keepers = {
    resource_group = var.resource_group_name
  }
}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# One identity for the whole workload. Jobs and, later, the dashboard use it to
# pull images and read secrets, so every permission the platform grants is
# visible as a role assignment on a single principal.
resource "azurerm_user_assigned_identity" "workload" {
  name                = "id-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = local.tags
}

module "observability" {
  source = "../../modules/observability"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  retention_in_days   = var.log_retention_in_days
  daily_quota_gb      = var.log_daily_quota_gb
  tags                = local.tags
}

module "network" {
  source = "../../modules/network"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = local.tags
}

module "acr" {
  source = "../../modules/acr"

  name                       = "acr${replace(local.name_prefix, "-", "")}${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  log_analytics_workspace_id = module.observability.workspace_id
  tags                       = local.tags

  pull_principal_ids = {
    workload = azurerm_user_assigned_identity.workload.principal_id
  }
}

module "postgres" {
  source = "../../modules/postgres"

  name                       = "psql-${local.name_prefix}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  delegated_subnet_id        = module.network.postgres_subnet_id
  private_dns_zone_id        = module.network.postgres_private_dns_zone_id
  administrator_password     = random_password.postgres_admin.result
  log_analytics_workspace_id = module.observability.workspace_id
  tags                       = local.tags

  # The server cannot be created before its FQDN is resolvable inside the VNet.
  depends_on = [module.network]
}

module "keyvault" {
  source = "../../modules/keyvault"

  name                       = "kv-${local.name_prefix}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  log_analytics_workspace_id = module.observability.workspace_id
  deployer_object_id         = data.azurerm_client_config.current.object_id
  tags                       = local.tags

  secret_reader_principal_ids = {
    workload = azurerm_user_assigned_identity.workload.principal_id
  }

  secrets = {
    # sslmode=require rather than verify-full: the server is only reachable
    # inside the VNet and its certificate chain would need to be shipped in the
    # image to verify. Recorded as a hardening item rather than left implicit.
    "database-url" = join("", [
      "postgresql+psycopg://",
      module.postgres.administrator_login,
      ":",
      urlencode(random_password.postgres_admin.result),
      "@",
      module.postgres.fqdn,
      ":5432/",
      module.postgres.database_name,
      "?sslmode=require",
    ])

    # The kill switch lives here so that tripping it is a secret update, not a
    # redeployment. Phase 5 reads it from Key Vault on every cycle; until then
    # the job resolves it at execution start.
    "kill-switch" = "false"

    "appinsights-connection-string" = module.observability.application_insights_connection_string
  }
}

module "container_apps" {
  source = "../../modules/container_apps"

  name_prefix                = local.name_prefix
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  infrastructure_subnet_id   = module.network.container_apps_subnet_id
  log_analytics_workspace_id = module.observability.workspace_id
  user_assigned_identity_id  = azurerm_user_assigned_identity.workload.id
  registry_server            = module.acr.login_server
  image                      = "${module.acr.login_server}/${var.image_repository}:${var.image_tag}"
  cron_expression            = var.cron_expression
  tags                       = local.tags

  secrets = {
    "database-url"                  = module.keyvault.secret_versionless_ids["database-url"]
    "kill-switch"                   = module.keyvault.secret_versionless_ids["kill-switch"]
    "appinsights-connection-string" = module.keyvault.secret_versionless_ids["appinsights-connection-string"]
  }

  secret_environment_variables = {
    BOT_DATABASE_URL                      = "database-url"
    BOT_KILL_SWITCH                       = "kill-switch"
    APPLICATIONINSIGHTS_CONNECTION_STRING = "appinsights-connection-string"
  }

  environment_variables = {
    BOT_ENVIRONMENT      = var.environment
    BOT_EXCHANGE_BACKEND = var.exchange_backend
    BOT_SYMBOL           = var.symbol
    BOT_TIMEFRAME        = var.timeframe
    BOT_LOG_LEVEL        = var.log_level

    # azure-identity picks the right managed identity from this. A user-assigned
    # identity is ambiguous without it when more than one is attached.
    AZURE_CLIENT_ID = azurerm_user_assigned_identity.workload.client_id
  }
}

# A budget alerts, it does not stop anything. The only control that actually
# caps spend here is destroying the environment, which is why the stack is built
# to be destroyed and recreated.
resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "budget-${local.name_prefix}"
  resource_group_id = azurerm_resource_group.this.id
  amount            = var.monthly_budget_amount
  time_grain        = "Monthly"

  time_period {
    start_date = var.budget_start_date
    end_date   = var.budget_end_date
  }

  dynamic "notification" {
    for_each = var.budget_alert_thresholds
    content {
      enabled   = true
      threshold = notification.value
      operator  = "GreaterThanOrEqualTo"
      # Actual spend, not forecast: a forecast alert on a burstable database
      # fires on the first day and then gets ignored.
      threshold_type = "Actual"
      contact_roles  = ["Owner"]
    }
  }

  lifecycle {
    # Azure rewrites the start date to the beginning of the current period, so
    # comparing it against a literal produces a diff on every plan.
    ignore_changes = [time_period[0].start_date]
  }
}
