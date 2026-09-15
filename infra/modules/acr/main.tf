terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"

  # The admin account is a shared username and password with push rights on the
  # whole registry. Disabling it is what forces every consumer, human or
  # workload, through Entra ID and a scoped role.
  admin_enabled = false

  # checkov:skip=CKV_AZURE_163:Registry-side vulnerability scanning is a Microsoft Defender for Containers feature, billed per vCPU of scanned workload. Images are scanned with Trivy in the pull request pipeline instead, which blocks a vulnerable image before it is pushed rather than reporting it afterwards.
  # checkov:skip=CKV_AZURE_233:Zone redundancy needs the Premium SKU. A registry holding one image for a dev environment does not justify the price difference.
  # checkov:skip=CKV_AZURE_237:Dedicated data endpoints need Premium.
  # checkov:skip=CKV_AZURE_164:Trusted content signing needs Premium.
  # checkov:skip=CKV_AZURE_165:Geo-replication needs Premium.
  # checkov:skip=CKV_AZURE_166:Quarantine on push needs Premium; images are scanned with Trivy in CI instead.
  # checkov:skip=CKV_AZURE_167:Retention policies need Premium.
  # checkov:skip=CKV_AZURE_139:Public network access is required: images are pushed from GitHub-hosted runners, which have no fixed egress address. Private access needs Premium and a private endpoint.
  # checkov:skip=CKV2_AZURE_44:Same reason.
  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "diag-acr"
  target_resource_id         = azurerm_container_registry.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "ContainerRegistryLoginEvents"
  }

  enabled_log {
    category = "ContainerRegistryRepositoryEvents"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_role_assignment" "pull" {
  for_each = var.pull_principal_ids

  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = each.value
}
