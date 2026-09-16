variable "name_prefix" {
  description = "Short prefix used in resource names."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that holds the environment and the jobs."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "infrastructure_subnet_id" {
  description = "Subnet the environment is injected into. Must be /23 or larger."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Workspace receiving container stdout."
  type        = string
}

variable "user_assigned_identity_id" {
  description = "Identity used to pull from the registry and to read Key Vault secrets."
  type        = string
}

variable "registry_server" {
  description = "Container registry login server."
  type        = string
}

variable "image" {
  description = "Fully qualified image reference, including the tag."
  type        = string
}

variable "cron_expression" {
  description = "Schedule for the trading cycle, in UTC."
  type        = string
  default     = "*/15 * * * *"
}

variable "replica_timeout_in_seconds" {
  description = "Maximum duration of one execution. Must stay well below the schedule interval."
  type        = number
  default     = 600
}

variable "cpu" {
  description = "vCPU per replica. 0.25 is the smallest Consumption allows."
  type        = number
  default     = 0.25
}

variable "memory" {
  description = "Memory per replica. Must pair with cpu at a 1 to 2 ratio."
  type        = string
  default     = "0.5Gi"
}

variable "environment_variables" {
  description = "Plain environment variables passed to every job."
  type        = map(string)
  default     = {}
}

variable "secret_environment_variables" {
  description = "Environment variables sourced from a job secret, variable name to secret name."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Job secrets, secret name to Key Vault versionless secret id."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
}

variable "workload_profile_name" {
  description = "Workload profile the jobs run on. Consumption is what a Consumption-only environment assigns."
  type        = string
  default     = "Consumption"
}
