data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 8
  lower   = true
  upper   = false
  numeric = true
  special = false

  # The storage account name is globally unique and stays reserved for a while
  # after a delete. A suffix that survives in state keeps `destroy` followed by
  # `apply` working, which is a requirement here and not a convenience.
  keepers = {
    resource_group = var.resource_group_name
  }
}

resource "azurerm_resource_group" "state" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "state" {
  name                = "${var.storage_account_prefix}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.state.name
  location            = azurerm_resource_group.state.location

  account_tier = "Standard"
  # Geo-redundant rather than local: losing this state blocks every future
  # apply and destroy. The state is a few kilobytes, so the premium over LRS
  # is not measurable on the bill.
  account_replication_type = "GRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"

  min_tls_version                   = "TLS1_2"
  https_traffic_only_enabled        = true
  allow_nested_items_to_be_public   = false
  public_network_access_enabled     = true
  shared_access_key_enabled         = false
  infrastructure_encryption_enabled = true

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = var.state_retention_days
    }

    container_delete_retention_policy {
      days = var.state_retention_days
    }
  }

  # checkov:skip=CKV_AZURE_59:Public network access is required. GitHub-hosted runners have no fixed egress addresses, so an IP allow list would either be permanently open or break CI. Access is restricted by Entra ID RBAC instead, with shared keys disabled.
  # checkov:skip=CKV_AZURE_33:Queue service logging is irrelevant: this account exposes only a blob container and the queue service is unused.
  # checkov:skip=CKV2_AZURE_1:Customer-managed keys would require a Key Vault that this stack bootstraps before any Key Vault exists. Microsoft-managed keys with infrastructure encryption are the deliberate trade-off.
  # checkov:skip=CKV2_AZURE_18:Same reason as CKV2_AZURE_1.
  # checkov:skip=CKV2_AZURE_33:A private endpoint would make the backend unreachable from GitHub-hosted runners and from a developer machine outside the VNet.
  # checkov:skip=CKV2_AZURE_40:Shared key authorisation is already disabled, which is the stronger control.
  # checkov:skip=CKV2_AZURE_41:SAS policies do not apply when shared keys are disabled.
  tags = var.tags
}

resource "azurerm_storage_container" "state" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"

  # checkov:skip=CKV2_AZURE_21:Blob read logging needs a diagnostic setting with a destination, and this stack runs before any Log Analytics workspace exists. The state is protected by Entra ID RBAC, blob versioning and soft delete; adding a workspace here to audit reads of non-secret configuration is not worth the cost or the ordering problem.

  depends_on = [time_sleep.rbac_propagation]
}

# Owner does not grant data-plane access. Reading and writing state blobs needs
# an explicit data role, which is the whole point of disabling shared keys.
resource "azurerm_role_assignment" "state_blob_owner" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Entra ID role assignments are eventually consistent. Creating the container
# immediately after the assignment fails often enough to be worth waiting out
# rather than asking the operator to re-run apply.
resource "time_sleep" "rbac_propagation" {
  depends_on      = [azurerm_role_assignment.state_blob_owner]
  create_duration = "60s"
}
