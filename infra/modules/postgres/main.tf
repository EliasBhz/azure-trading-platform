terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

resource "azurerm_postgresql_flexible_server" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  version             = var.postgres_version

  # Private access. Injecting the server into a delegated subnet means it has no
  # public endpoint at all, rather than a public endpoint with a firewall in
  # front of it. The trade-off is that nothing outside the VNet can reach it,
  # including Terraform and CI, so migrations run as a Container Apps Job.
  delegated_subnet_id = var.delegated_subnet_id
  private_dns_zone_id = var.private_dns_zone_id

  # Must be stated, not left to the provider default. azurerm sends true
  # unless told otherwise, and Azure rejects the pair outright:
  # ConflictingPublicNetworkAccessAndVirtualNetworkConfiguration.
  public_network_access_enabled = false

  administrator_login    = var.administrator_login
  administrator_password = var.administrator_password

  sku_name   = var.sku_name
  storage_mb = var.storage_mb

  backup_retention_days = var.backup_retention_days
  # Geo-redundant backup roughly doubles the backup cost and cannot be changed
  # after creation. This environment is rebuilt from Terraform, and the data it
  # holds is simulated paper trades.
  geo_redundant_backup_enabled = false

  # Pinned rather than left to Azure: an unset zone produces a permanent diff on
  # every plan once Azure picks one.
  zone = var.availability_zone

  # checkov:skip=CKV_AZURE_136:Entra ID only authentication would remove the password entirely, but creating the managed identity's database role needs an admin connection from inside the VNet, which is a bootstrap job this phase does not build. Recorded in ADR-0009 as the next hardening step.
  # checkov:skip=CKV2_AZURE_57:Same reason.
  tags = var.tags
}

resource "azurerm_postgresql_flexible_server_database" "this" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Reject any connection that is not TLS. The default already requires it, but
# stating it makes the guarantee visible in the configuration rather than
# dependent on a default that could change.
resource "azurerm_postgresql_flexible_server_configuration" "require_secure_transport" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "on"
}

# Log every statement that takes longer than a second. Cheap, and it is the
# first thing anyone asks for when a fifteen minute job starts timing out.
resource "azurerm_postgresql_flexible_server_configuration" "log_min_duration" {
  name      = "log_min_duration_statement"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "1000"
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "diag-postgres"
  target_resource_id         = azurerm_postgresql_flexible_server.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "PostgreSQLLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
