output "plan_client_id" {
  description = "Client id for the pull request workflow. Store as the AZURE_CLIENT_ID_PLAN repository variable."
  value       = azuread_application.plan.client_id
}

output "deploy_client_id" {
  description = "Client id for the deployment workflow. Store as the AZURE_CLIENT_ID_DEPLOY environment variable on the protected environment."
  value       = azuread_application.deploy.client_id
}

output "deploy_principal_id" {
  description = "Object id of the deployment service principal. Pass to the dev stack as acr_push_principal_ids so it can push images."
  value       = azuread_service_principal.deploy.object_id
}

output "tenant_id" {
  description = "Entra ID tenant. Store as the AZURE_TENANT_ID repository variable."
  value       = data.azuread_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Subscription. Store as the AZURE_SUBSCRIPTION_ID repository variable."
  value       = var.subscription_id
}

output "github_variables" {
  description = "Everything the workflows need. None of it is secret: an OIDC client id is useless without a token whose subject matches a federated credential."
  value       = <<-EOT
    AZURE_TENANT_ID        = ${data.azuread_client_config.current.tenant_id}
    AZURE_SUBSCRIPTION_ID  = ${var.subscription_id}
    AZURE_CLIENT_ID_PLAN   = ${azuread_application.plan.client_id}
    AZURE_CLIENT_ID_DEPLOY = ${azuread_application.deploy.client_id}
  EOT
}
