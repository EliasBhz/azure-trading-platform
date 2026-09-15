variable "name_prefix" {
  description = "Short prefix used in resource names."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that holds the workspace."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "retention_in_days" {
  description = "Log retention. 30 days is the free floor; longer is billed."
  type        = number
  default     = 30
}

variable "daily_quota_gb" {
  description = "Hard daily ingestion cap. Telemetry is dropped once reached."
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
}
