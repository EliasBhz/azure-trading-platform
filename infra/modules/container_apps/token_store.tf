# Easy Auth needs somewhere to keep a session, and without it Container Apps
# falls back to answering a bearer challenge instead of redirecting to a sign-in
# page. That was measured, not assumed: with the token store disabled the app
# stored `RedirectToLoginPage` and still answered 401 with a
# `www-authenticate: Bearer` header, which protects the page and makes it
# unusable in a browser.
#
# The container is addressed by URI with a managed identity rather than a SAS
# token, so no storage key or shared access signature exists to rotate or leak.

resource "azurerm_storage_account" "token_store" {
  count = var.dashboard_enabled ? 1 : 0

  name                = var.token_store_account_name
  resource_group_name = var.resource_group_name
  location            = var.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  public_network_access_enabled   = true

  # checkov:skip=CKV_AZURE_206:Local redundancy is deliberate. This account holds session tokens, which are short lived and reissued by signing in again; paying for geo-redundancy to protect them would be paying to avoid one sign-in.
  # checkov:skip=CKV_AZURE_59:Public network access is required because the Container Apps auth middleware reaches the blob service from the platform, not from inside the VNet. Shared keys are disabled, so access is by Entra ID identity only.
  # checkov:skip=CKV_AZURE_33:The queue service is unused; only the blob service is.
  # checkov:skip=CKV_AZURE_34:Container access is private by default and set explicitly below.
  # checkov:skip=CKV_AZURE_35:Network rules would have to allow the platform, which has no fixed address. Authorisation is by Entra ID RBAC.
  # checkov:skip=CKV_AZURE_43:The name is supplied by the caller and validated there.
  # checkov:skip=CKV_AZURE_190:Blob public access is already disabled account wide.
  # checkov:skip=CKV2_AZURE_1:Customer-managed keys would add a key to manage for data that is regenerated on every sign-in.
  # checkov:skip=CKV2_AZURE_18:Same reason.
  # checkov:skip=CKV2_AZURE_21:Blob read logging needs a diagnostic setting whose value here is low: the data is session tokens, not business records.
  # checkov:skip=CKV2_AZURE_33:A private endpoint would make the account unreachable from the auth middleware.
  # checkov:skip=CKV2_AZURE_38:Soft delete is deliberately off. This container holds session tokens, and retaining deleted ones would keep credentials alive past the moment they were meant to disappear. A signed-out session should be gone, not recoverable.
  # checkov:skip=CKV2_AZURE_40:Shared key authorisation is already disabled, which is the stronger control.
  # checkov:skip=CKV2_AZURE_41:SAS policies do not apply when shared keys are disabled.
  tags = var.tags
}

resource "azurerm_storage_container" "token_store" {
  count = var.dashboard_enabled ? 1 : 0

  name                  = "tokens"
  storage_account_id    = azurerm_storage_account.token_store[0].id
  container_access_type = "private"

  # checkov:skip=CKV2_AZURE_21:See the account above.

  depends_on = [time_sleep.token_store_rbac]
}

# The workload identity reads and writes session tokens. Data Contributor rather
# than Owner: it never needs to change access policies on the container.
resource "azurerm_role_assignment" "token_store_workload" {
  count = var.dashboard_enabled ? 1 : 0

  scope                = azurerm_storage_account.token_store[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.user_assigned_identity_principal_id
}

# Creating the container is a data action, so the deploying identity needs one
# too. Owner on the subscription does not grant it.
resource "azurerm_role_assignment" "token_store_deployer" {
  count = var.dashboard_enabled ? 1 : 0

  scope                = azurerm_storage_account.token_store[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.deployer_object_id
}

resource "time_sleep" "token_store_rbac" {
  count = var.dashboard_enabled ? 1 : 0

  depends_on = [
    azurerm_role_assignment.token_store_workload,
    azurerm_role_assignment.token_store_deployer,
  ]
  create_duration = "60s"
}
