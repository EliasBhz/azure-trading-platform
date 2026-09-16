resource "azurerm_resource_group" "governance" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_automation_account" "cost_guard" {
  name                = "aa-${var.name_prefix}-cost-guard"
  resource_group_name = azurerm_resource_group.governance.name
  location            = azurerm_resource_group.governance.location
  sku_name            = "Basic"

  # Jobs run in the Azure-managed sandbox, which is reachable only over the
  # public endpoint. Restricting this to a private endpoint would require a
  # hybrid worker, meaning a virtual machine paid for continuously so that an
  # automation can save money once a month. The account holds no secret and
  # its identity can do exactly one thing.
  public_network_access_enabled = true

  # A system-assigned identity rather than a stored credential: the runbook
  # authenticates as the automation account itself, and there is nothing to
  # rotate or leak.
  identity {
    type = "SystemAssigned"
  }

  # checkov:skip=CKV2_AZURE_24:Private networking would require a hybrid worker, which means paying for a virtual machine continuously so that a cost-control automation can run. The account stores no credential and its managed identity holds a custom role limited to reading and stopping PostgreSQL servers.
  # checkov:skip=CKV2_AZURE_38:Local authentication is not used; the runbook signs in with the account's managed identity.
  tags = var.tags
}

# The automation may stop a PostgreSQL server and do nothing else. Contributor
# would have worked and would have meant a budget alert could delete the
# environment. A custom role is a few lines and turns "the automation is
# trusted" into "the automation is incapable of anything worse".
resource "azurerm_role_definition" "cost_guard" {
  name        = "${var.name_prefix}-cost-guard"
  scope       = data.azurerm_subscription.current.id
  description = "Read PostgreSQL Flexible Servers and stop them. Nothing else."

  permissions {
    actions = [
      "Microsoft.Resources/subscriptions/resourceGroups/read",
      "Microsoft.DBforPostgreSQL/flexibleServers/read",
      "Microsoft.DBforPostgreSQL/flexibleServers/stop/action",
    ]
    not_actions = []
  }

  assignable_scopes = [data.azurerm_subscription.current.id]
}

resource "azurerm_role_assignment" "cost_guard" {
  scope              = data.azurerm_subscription.current.id
  role_definition_id = azurerm_role_definition.cost_guard.role_definition_resource_id
  principal_id       = azurerm_automation_account.cost_guard.identity[0].principal_id
}

resource "azurerm_automation_runbook" "stop_cost_drivers" {
  name                    = "Stop-CostDrivers"
  resource_group_name     = azurerm_resource_group.governance.name
  location                = azurerm_resource_group.governance.location
  automation_account_name = azurerm_automation_account.cost_guard.name
  runbook_type            = "PowerShell72"
  log_verbose             = true
  log_progress            = true
  description             = "Stops the project's PostgreSQL Flexible Servers when the subscription budget is reached."

  content = templatefile("${path.module}/runbooks/stop-cost-drivers.ps1", {
    subscription_id = var.subscription_id
    project_tag     = var.project_tag
  })

  tags = var.tags
}

# An action group can only start a runbook through a webhook, so one has to
# exist. Its URI is a bearer credential and lives in the Terraform state, which
# is why the state account has shared keys disabled and is reachable only
# through Entra ID RBAC.
resource "azurerm_automation_webhook" "stop_cost_drivers" {
  name                    = "wh-stop-cost-drivers"
  resource_group_name     = azurerm_resource_group.governance.name
  automation_account_name = azurerm_automation_account.cost_guard.name
  runbook_name            = azurerm_automation_runbook.stop_cost_drivers.name
  expiry_time             = var.webhook_expiry_time
  enabled                 = true
}

resource "azurerm_monitor_action_group" "cost_guard" {
  name                = "ag-${var.name_prefix}-cost-guard"
  resource_group_name = azurerm_resource_group.governance.name
  short_name          = "costguard"

  automation_runbook_receiver {
    name                    = "stop-cost-drivers"
    automation_account_id   = azurerm_automation_account.cost_guard.id
    runbook_name            = azurerm_automation_runbook.stop_cost_drivers.name
    webhook_resource_id     = azurerm_automation_webhook.stop_cost_drivers.id
    service_uri             = azurerm_automation_webhook.stop_cost_drivers.uri
    is_global_runbook       = false
    use_common_alert_schema = true
  }

  dynamic "email_receiver" {
    for_each = var.contact_emails
    content {
      name          = "email-${email_receiver.key}"
      email_address = email_receiver.value
    }
  }

  tags = var.tags
}
