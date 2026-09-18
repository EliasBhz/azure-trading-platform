terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
  }
}

resource "azurerm_key_vault" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  # RBAC rather than access policies: permissions are then visible in the same
  # place as every other role assignment, and they can be granted to a managed
  # identity without editing the vault itself.
  rbac_authorization_enabled = true

  # Purge protection is off and the retention window is the seven day minimum,
  # on purpose. A soft-deleted vault keeps its name reserved, so purge
  # protection would make `destroy` followed by `apply` fail on a name that
  # cannot be reused. This environment is designed to be destroyed; a production
  # vault would make the opposite choice.
  purge_protection_enabled   = false
  soft_delete_retention_days = 7

  public_network_access_enabled = true

  network_acls {
    bypass         = "AzureServices"
    default_action = "Allow"
  }

  # checkov:skip=CKV_AZURE_109:Network ACLs default to Allow because the vault must be writable by Terraform from a developer machine and from GitHub-hosted runners, neither of which has a stable egress address. Authorisation is by Entra ID RBAC. Restricting to a private endpoint requires the deployment pipeline to run inside the VNet and is a separate change.
  # checkov:skip=CKV_AZURE_189:Same reason.
  # checkov:skip=CKV_AZURE_110:Purge protection is deliberately disabled
  # checkov:skip=CKV_AZURE_42:Purge protection is deliberately disabled so the environment can be destroyed and recreated; the reasoning is in the comment above and in ADR-0009.
  # checkov:skip=CKV2_AZURE_32:A private endpoint would make the vault unreachable from the deployment pipeline.
  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "diag-keyvault"
  target_resource_id         = azurerm_key_vault.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  # Audit events answer "who read which secret and when", which is the one
  # question worth being able to answer about a vault after an incident.
  enabled_log {
    category = "AuditEvent"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_key_vault_secret" "this" {
  # Secret names are not secret, only their values. Unwrapping the keys keeps
  # the map sensitive while still allowing one resource instance per secret;
  # a sensitive value cannot be a for_each key because it would appear in the
  # resource address.
  for_each = nonsensitive(toset(keys(var.secrets)))

  name         = each.key
  value        = var.secrets[each.key]
  key_vault_id = azurerm_key_vault.this.id
  content_type = "text/plain"
  tags         = var.tags

  # checkov:skip=CKV_AZURE_41:No expiry date. These are a generated database password and an operational flag, both rotated by re-running Terraform rather than by an expiry that would take the bot down at an arbitrary moment.

  depends_on = [time_sleep.rbac_propagation]
}

# Writing a secret is a data action. Owner on the subscription does not grant
# it, so every identity that may run apply needs this role explicitly, and it
# has to exist before the first secret is written.
#
# A set rather than "whoever is running apply". Deriving it from the caller made
# a human plan propose deleting the pipeline's permission, and a pipeline plan
# propose deleting the human's: two identities fighting over one resource, with
# the loser finding out at the next apply.
resource "azurerm_role_assignment" "secrets_officer" {
  for_each = var.secret_writer_principal_ids

  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "reader_secrets_user" {
  for_each = var.secret_reader_principal_ids

  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

# Entra ID role assignments are eventually consistent. Writing a secret straight
# after granting the role fails intermittently, and an intermittent failure in a
# deployment pipeline is worse than a fixed minute of waiting.
resource "time_sleep" "rbac_propagation" {
  depends_on      = [azurerm_role_assignment.secrets_officer]
  create_duration = "60s"
}
