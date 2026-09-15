variable "subscription_id" {
  description = "Azure subscription that hosts the Terraform state."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "location" {
  description = "Azure region for the state storage account."
  type        = string
  # Not West Europe: that region refuses new customers on this subscription and
  # returns RequestDisallowedByAzure on storage account creation.
  default = "northeurope"
}

variable "resource_group_name" {
  description = "Resource group holding the Terraform state storage account."
  type        = string
  default     = "rg-tfstate-tradingbot-neu"
}

variable "storage_account_prefix" {
  description = "Prefix for the state storage account name. A random suffix is appended to keep the globally unique name available after a destroy."
  type        = string
  default     = "sttfstatetrading"

  validation {
    condition     = can(regex("^[a-z0-9]{3,16}$", var.storage_account_prefix))
    error_message = "storage_account_prefix must be 3 to 16 lowercase alphanumeric characters."
  }
}

variable "container_name" {
  description = "Blob container holding the state files."
  type        = string
  default     = "tfstate"
}

variable "state_retention_days" {
  description = "Days a deleted or overwritten state blob stays recoverable."
  type        = number
  default     = 30

  validation {
    condition     = var.state_retention_days >= 7
    error_message = "state_retention_days must be at least 7: a shorter window is not enough to notice a corrupted state."
  }
}

variable "tags" {
  description = "Tags applied to every resource. project, env, owner and cost-center are mandatory across this repository."
  type        = map(string)
  default = {
    project       = "azure-trading-platform"
    env           = "shared"
    owner         = "eliasbaghazou"
    "cost-center" = "personal"
    component     = "terraform-state"
  }
}
