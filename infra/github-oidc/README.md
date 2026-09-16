# GitHub OIDC identities

Creates the two Entra ID applications GitHub Actions authenticates as. No client
secret exists anywhere. See ADR-0010.

## What it creates

| | `plan` | `deploy` |
|---|---|---|
| Federated subject | `repo:OWNER/REPO:pull_request` | `repo:OWNER/REPO:environment:dev` |
| Subscription role | Reader | Contributor, Role Based Access Control Administrator |
| State storage role | Storage Blob Data Reader | Storage Blob Data Contributor |

## Usage

Run after `infra/bootstrap`, from an account that may register applications in
the tenant and assign roles on the subscription.

    cd infra/github-oidc
    terraform init
    terraform plan  -var subscription_id=<SUBSCRIPTION_ID> -out tfplan
    terraform apply tfplan
    terraform output github_variables

## Wiring the output into GitHub

These are **variables, not secrets**. A client id is useless without a token
whose subject matches a federated credential, so marking it secret would be
security theatre and would make the workflows harder to read.

    gh variable set AZURE_TENANT_ID        --body <TENANT_ID>
    gh variable set AZURE_SUBSCRIPTION_ID  --body <SUBSCRIPTION_ID>
    gh variable set AZURE_CLIENT_ID_PLAN   --body <PLAN_CLIENT_ID>

    gh variable set AZURE_CLIENT_ID_DEPLOY     --env dev --body <DEPLOY_CLIENT_ID>
    gh variable set AZURE_DEPLOY_PRINCIPAL_ID  --env dev --body <DEPLOY_PRINCIPAL_ID>

The `dev` environment must exist, must require a reviewer, and must accept
deployments only from protected branches. Without the reviewer the federated
subject is obtainable by any push to `main`, which removes the human from the
loop entirely.

    gh api -X PUT repos/OWNER/REPO/environments/dev --input environment.json

`main` must stay protected. The environment refuses deployments from
unprotected branches, so dropping branch protection silently disables
deployment rather than failing loudly.

## Destroying

Deleting these identities breaks CI and CD immediately and does not affect any
running workload.

    terraform destroy -var subscription_id=<SUBSCRIPTION_ID>

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_azuread"></a> [azuread](#requirement\_azuread) | ~> 3.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | ~> 4.0 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_azuread"></a> [azuread](#provider\_azuread) | ~> 3.0 |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | ~> 4.0 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [azuread_application.deploy](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application) | resource |
| [azuread_application.plan](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application) | resource |
| [azuread_application_federated_identity_credential.deploy_environment](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application_federated_identity_credential) | resource |
| [azuread_application_federated_identity_credential.plan_pull_request](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application_federated_identity_credential) | resource |
| [azuread_service_principal.deploy](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/service_principal) | resource |
| [azuread_service_principal.plan](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/service_principal) | resource |
| [azurerm_role_assignment.deploy_contributor](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_assignment.deploy_rbac_administrator](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_assignment.deploy_state_contributor](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_assignment.plan_reader](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azurerm_role_assignment.plan_state_reader](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/role_assignment) | resource |
| [azuread_client_config.current](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/data-sources/client_config) | data source |
| [azurerm_storage_account.state](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/storage_account) | data source |
| [azurerm_subscription.current](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/subscription) | data source |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_application_prefix"></a> [application\_prefix](#input\_application\_prefix) | Prefix for the two Entra ID application display names. | `string` | `"github-actions-tradingbot"` | no |
| <a name="input_github_environment"></a> [github\_environment](#input\_github\_environment) | GitHub environment that gates deployments. Its protection rules are what make the deploy identity unreachable without an approval. | `string` | `"dev"` | no |
| <a name="input_github_owner"></a> [github\_owner](#input\_github\_owner) | GitHub account or organisation owning the repository. | `string` | `"EliasBhz"` | no |
| <a name="input_github_repository"></a> [github\_repository](#input\_github\_repository) | Repository whose workflows may obtain these credentials. | `string` | `"azure-trading-platform"` | no |
| <a name="input_state_resource_group_name"></a> [state\_resource\_group\_name](#input\_state\_resource\_group\_name) | Resource group holding the Terraform state storage account, created by infra/bootstrap. | `string` | `"rg-tfstate-tradingbot-neu"` | no |
| <a name="input_state_storage_account_name"></a> [state\_storage\_account\_name](#input\_state\_storage\_account\_name) | Terraform state storage account, created by infra/bootstrap. | `string` | `"sttfstatetrading4vqxmldp"` | no |
| <a name="input_subscription_id"></a> [subscription\_id](#input\_subscription\_id) | Azure subscription the identities are granted access to. | `string` | n/a | yes |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_deploy_client_id"></a> [deploy\_client\_id](#output\_deploy\_client\_id) | Client id for the deployment workflow. Store as the AZURE\_CLIENT\_ID\_DEPLOY environment variable on the protected environment. |
| <a name="output_deploy_principal_id"></a> [deploy\_principal\_id](#output\_deploy\_principal\_id) | Object id of the deployment service principal. Pass to the dev stack as acr\_push\_principal\_ids so it can push images. |
| <a name="output_github_variables"></a> [github\_variables](#output\_github\_variables) | Everything the workflows need. None of it is secret: an OIDC client id is useless without a token whose subject matches a federated credential. |
| <a name="output_plan_client_id"></a> [plan\_client\_id](#output\_plan\_client\_id) | Client id for the pull request workflow. Store as the AZURE\_CLIENT\_ID\_PLAN repository variable. |
| <a name="output_subscription_id"></a> [subscription\_id](#output\_subscription\_id) | Subscription. Store as the AZURE\_SUBSCRIPTION\_ID repository variable. |
| <a name="output_tenant_id"></a> [tenant\_id](#output\_tenant\_id) | Entra ID tenant. Store as the AZURE\_TENANT\_ID repository variable. |
<!-- END_TF_DOCS -->
