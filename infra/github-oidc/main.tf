data "azurerm_subscription" "current" {}

# Looked up rather than passed in as a resource id. A caller typing the id by
# hand gets it wrong in ways that surface as an opaque MissingSubscription
# error, and on Windows a shell will happily rewrite a leading slash into a
# local path before Terraform ever sees it.
data "azurerm_storage_account" "state" {
  name                = var.state_storage_account_name
  resource_group_name = var.state_resource_group_name
}

locals {
  subject_prefix = "repo:${var.github_owner}/${var.github_repository}"
}

# Two identities, not one. A pull request from a fork can run workflows, so the
# credential a pull request can obtain must not be able to change anything. The
# split is the whole point of this stack: plan reads, deploy writes, and only
# deploy is reachable from a protected GitHub environment.

# ---------------------------------------------------------------------------
# Plan: used by pull request workflows. Read only.
# ---------------------------------------------------------------------------

resource "azuread_application" "plan" {
  display_name     = "${var.application_prefix}-plan"
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  description = "Read-only identity used by pull request workflows to run terraform plan."
}

resource "azuread_service_principal" "plan" {
  client_id = azuread_application.plan.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# The subject is matched exactly by Entra ID. `pull_request` covers every pull
# request in this repository and nothing else: a push to a branch produces a
# different subject and gets no token.
resource "azuread_application_federated_identity_credential" "plan_pull_request" {
  application_id = azuread_application.plan.id
  display_name   = "github-pull-request"
  description    = "Pull request workflows in ${local.subject_prefix}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "${local.subject_prefix}:pull_request"
}

resource "azurerm_role_assignment" "plan_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Reader"
  principal_id         = azuread_service_principal.plan.object_id
}

# Reading the state is a data action; Reader on the subscription does not grant
# it. Data Reader and not Data Contributor, which is why pull request plans run
# with -lock=false: acquiring a blob lease is a write, and a plan that cannot
# write is a plan that cannot corrupt state.
resource "azurerm_role_assignment" "plan_state_reader" {
  scope                = data.azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azuread_service_principal.plan.object_id
}

# ---------------------------------------------------------------------------
# Deploy: used only from the protected GitHub environment. Read and write.
# ---------------------------------------------------------------------------

resource "azuread_application" "deploy" {
  display_name     = "${var.application_prefix}-deploy"
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  description = "Deployment identity. Reachable only from the protected GitHub environment ${var.github_environment}."
}

resource "azuread_service_principal" "deploy" {
  client_id = azuread_application.deploy.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# The environment subject is what makes the GitHub approval gate a security
# control rather than a formality: without an approved deployment to that
# environment, GitHub never mints a token with this subject, so the credential
# cannot be obtained at all.
resource "azuread_application_federated_identity_credential" "deploy_environment" {
  application_id = azuread_application.deploy.id
  display_name   = "github-environment-${var.github_environment}"
  description    = "Deployments to the ${var.github_environment} environment of ${local.subject_prefix}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "${local.subject_prefix}:environment:${var.github_environment}"
}

resource "azurerm_role_assignment" "deploy_contributor" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.deploy.object_id
}

# The dev stack creates role assignments of its own, which Contributor cannot
# do. This is the most privileged grant in the project and the one a reviewer
# should question: it is scoped to the subscription because the resource group
# it manages does not exist before the first apply, and it is reachable only
# through an approved deployment.
resource "azurerm_role_assignment" "deploy_rbac_administrator" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = azuread_service_principal.deploy.object_id
}

resource "azurerm_role_assignment" "deploy_state_contributor" {
  scope                = data.azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.deploy.object_id
}

data "azuread_client_config" "current" {}
