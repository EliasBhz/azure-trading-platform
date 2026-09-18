variable "name_prefix" {
  description = "Short prefix used in resource names."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that holds the alerts and the workbook."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Workspace the alert queries run against."
  type        = string
}

variable "action_group_short_name" {
  description = "Short name shown in notifications. Twelve characters maximum."
  type        = string
  default     = "tradingbot"

  validation {
    condition     = length(var.action_group_short_name) <= 12
    error_message = "action_group_short_name must be at most 12 characters."
  }
}

variable "contact_emails" {
  description = "Addresses notified. Empty by default so no address is committed to a public repository; alerts still fire and remain visible in the portal."
  type        = list(string)
  default     = []
}

variable "no_cycle_window" {
  description = "How long the bot may be silent before the alert fires. Three missed cycles at a fifteen minute cadence."
  type        = string
  default     = "PT45M"
}

variable "drawdown_alert_ratio" {
  description = "Intraday drawdown that raises an alert, as a fraction of the day's opening equity."
  type        = number
  default     = 0.05

  validation {
    condition     = var.drawdown_alert_ratio > 0 && var.drawdown_alert_ratio < 1
    error_message = "drawdown_alert_ratio is a fraction, strictly between 0 and 1."
  }
}

variable "workbook_uuid" {
  description = "Workbook name, which Azure requires to be a GUID. Fixed in configuration so redeploying updates the same workbook instead of creating another."
  type        = string
  default     = "6f1a4c2e-9b73-4d58-a0e1-2c7d5f8b3a49"
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
}
