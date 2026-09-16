variable "name" {
  description = "Registry name. Globally unique, lowercase alphanumeric only."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{5,50}$", var.name))
    error_message = "Container registry names are 5 to 50 lowercase alphanumeric characters."
  }
}

variable "resource_group_name" {
  description = "Resource group that holds the registry."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Workspace receiving the registry logs."
  type        = string
}

variable "pull_principal_ids" {
  description = "Principals granted AcrPull, keyed by a readable name."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
}
