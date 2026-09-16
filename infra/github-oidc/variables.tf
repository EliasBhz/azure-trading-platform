variable "subscription_id" {
  description = "Azure subscription the identities are granted access to."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "github_owner" {
  description = "GitHub account or organisation owning the repository."
  type        = string
  default     = "EliasBhz"
}

variable "github_repository" {
  description = "Repository whose workflows may obtain these credentials."
  type        = string
  default     = "azure-trading-platform"
}

variable "github_owner_id" {
  description = "Numeric id of the GitHub account. Part of the immutable OIDC subject; read it with `gh api users/OWNER --jq .id`."
  type        = number
  default     = 100379191
}

variable "github_repository_id" {
  description = "Numeric id of the repository. Part of the immutable OIDC subject; read it with `gh api repos/OWNER/REPO --jq .id`."
  type        = number
  default     = 1371256764
}

variable "github_environment" {
  description = "GitHub environment that gates deployments. Its protection rules are what make the deploy identity unreachable without an approval."
  type        = string
  default     = "dev"
}

variable "application_prefix" {
  description = "Prefix for the two Entra ID application display names."
  type        = string
  default     = "github-actions-tradingbot"
}

variable "state_resource_group_name" {
  description = "Resource group holding the Terraform state storage account, created by infra/bootstrap."
  type        = string
  default     = "rg-tfstate-tradingbot-neu"
}

variable "state_storage_account_name" {
  description = "Terraform state storage account, created by infra/bootstrap."
  type        = string
  default     = "sttfstatetrading4vqxmldp"
}
