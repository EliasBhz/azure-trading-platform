variable "subscription_id" {
  description = "Azure subscription the environment is deployed into."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  # Not West Europe: that region refuses new customers on this subscription.
  # See ADR-0008.
  default = "northeurope"
}

variable "resource_group_name" {
  description = "Single resource group holding the whole environment."
  type        = string
  default     = "rg-tradingbot-dev-neu"
}

variable "project_short_name" {
  description = "Short project name used to build resource names."
  type        = string
  default     = "tradingbot"
}

variable "environment" {
  description = "Environment name, also used as the env tag."
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Value of the mandatory owner tag."
  type        = string
  default     = "eliasbaghazou"
}

variable "cost_center" {
  description = "Value of the mandatory cost-center tag."
  type        = string
  default     = "personal"
}

variable "image_repository" {
  description = "Repository holding the bot image inside the registry."
  type        = string
  default     = "trading-bot"
}

variable "image_tag" {
  description = "Image tag the jobs run. CI replaces this with the commit SHA."
  type        = string
  default     = "bootstrap"
}

variable "cron_expression" {
  description = "Trading cycle schedule, in UTC."
  type        = string
  default     = "*/15 * * * *"
}

variable "exchange_backend" {
  description = "simulated or ccxt_sandbox. There is no third option."
  type        = string
  default     = "simulated"

  validation {
    condition     = contains(["simulated", "ccxt_sandbox"], var.exchange_backend)
    error_message = "exchange_backend must be simulated or ccxt_sandbox: live trading has no code path."
  }
}

variable "symbol" {
  description = "Traded pair."
  type        = string
  default     = "BTC/USDT"
}

variable "timeframe" {
  description = "Candle timeframe. Must be consistent with the cron schedule."
  type        = string
  default     = "15m"
}

variable "log_level" {
  description = "Bot log level."
  type        = string
  default     = "INFO"
}

variable "log_retention_in_days" {
  description = "Log Analytics retention."
  type        = number
  default     = 30
}

variable "log_daily_quota_gb" {
  description = "Hard daily ingestion cap on the workspace."
  type        = number
  default     = 1
}

variable "monthly_budget_amount" {
  description = "Monthly budget for the resource group, in the billing currency."
  type        = number
  default     = 15
}

variable "budget_alert_thresholds" {
  description = "Percentages of the budget that raise an alert."
  type        = list(number)
  default     = [50, 80, 100]
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
