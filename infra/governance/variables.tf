variable "subscription_id" {
  description = "Azure subscription the budget watches."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "budget_name" {
  description = "Budget name, visible in Cost Management."
  type        = string
  default     = "budget-subscription-monthly"
}

variable "monthly_budget_amount" {
  description = "Monthly ceiling in the billing currency. This alerts; it does not stop anything."
  type        = number
  default     = 50
}

variable "warning_alert_thresholds" {
  description = "Percentages that warn people. The 100 percent threshold is declared separately because it also starts the automation."
  type        = list(number)
  default     = [50, 80]
}

variable "contact_roles" {
  description = "Subscription roles notified. Owner reaches whoever holds the subscription without hardcoding an address."
  type        = list(string)
  default     = ["Owner"]
}

variable "contact_emails" {
  description = "Extra addresses notified. Empty by default so no address is committed to a public repository."
  type        = list(string)
  default     = []
}

variable "budget_start_date" {
  description = "First day of the budget period. Azure requires the first of a month."
  type        = string
  default     = "2026-09-01T00:00:00Z"
}

variable "budget_end_date" {
  description = "End of the budget period."
  type        = string
  default     = "2030-01-01T00:00:00Z"
}

variable "location" {
  description = "Azure region for the governance resources."
  type        = string
  default     = "northeurope"
}

variable "resource_group_name" {
  description = "Resource group holding the budget automation. Separate from the environment so that destroying the environment does not remove what watches spending."
  type        = string
  default     = "rg-tradingbot-governance-neu"
}

variable "name_prefix" {
  description = "Short prefix used in resource names."
  type        = string
  default     = "tradingbot"
}

variable "project_tag" {
  description = "Value of the project tag the automation matches. A server without it is never touched."
  type        = string
  default     = "azure-trading-platform"
}

variable "webhook_expiry_time" {
  description = "Expiry of the webhook the action group calls. Azure refuses a webhook without one, so it has to be renewed deliberately rather than living forever."
  type        = string
  default     = "2030-01-01T00:00:00Z"
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default = {
    project       = "azure-trading-platform"
    env           = "shared"
    owner         = "eliasbaghazou"
    "cost-center" = "personal"
    component     = "governance"
  }
}
