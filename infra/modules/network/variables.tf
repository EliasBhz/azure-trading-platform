variable "name_prefix" {
  description = "Short prefix used in every resource name, for example tradingbot-dev."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that holds the network resources."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "address_space" {
  description = "VNet address space."
  type        = string
  default     = "10.40.0.0/16"
}

variable "container_apps_subnet_prefix" {
  description = "Subnet for the Container Apps environment. Must be /23 or larger."
  type        = string
  default     = "10.40.0.0/23"
}

variable "postgres_subnet_prefix" {
  description = "Delegated subnet for PostgreSQL Flexible Server."
  type        = string
  default     = "10.40.2.0/28"
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
}
