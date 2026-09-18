variable "name" {
  description = "Key Vault name. Globally unique, 3 to 24 characters."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.name))
    error_message = "Key Vault names are 3 to 24 characters, alphanumeric and hyphens, starting with a letter."
  }
}

variable "resource_group_name" {
  description = "Resource group that holds the vault."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "tenant_id" {
  description = "Entra ID tenant that owns the vault."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Workspace receiving the vault audit log."
  type        = string
}

variable "secret_writer_principal_ids" {
  description = "Every principal that may run apply, keyed by a readable name. All get Key Vault Secrets Officer, so a plan run by one does not propose removing another."
  type        = map(string)
}

variable "secret_reader_principal_ids" {
  description = "Principals granted Key Vault Secrets User, keyed by a readable name."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets to create, name to value."
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
}
