terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

resource "azurerm_monitor_action_group" "this" {
  name                = "ag-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  short_name          = var.action_group_short_name

  dynamic "email_receiver" {
    for_each = var.contact_emails
    content {
      name                    = "email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }

  # With no address configured the group still exists and alerts still fire and
  # are visible in the portal. An alert with nowhere to go is worth less than
  # one with an address, and worth much more than no alert at all.
  tags = var.tags
}

# A failed execution, said by the bot rather than inferred from the platform.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "cycle_failed" {
  name                = "alert-${var.name_prefix}-cycle-failed"
  resource_group_name = var.resource_group_name
  location            = var.location

  scopes               = [var.log_analytics_workspace_id]
  severity             = 1
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query                   = file("${path.module}/queries/cycle-failed.kql")
    time_aggregation_method = "Total"
    metric_measure_column   = "FailureCount"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = true
  action {
    action_groups = [azurerm_monitor_action_group.this.id]
  }

  tags = var.tags
}

# Silence. The failure mode a scheduled job has and a running service does not.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "no_cycle" {
  name                = "alert-${var.name_prefix}-no-cycle"
  resource_group_name = var.resource_group_name
  location            = var.location

  scopes               = [var.log_analytics_workspace_id]
  severity             = 1
  evaluation_frequency = "PT15M"

  # Three missed cycles at a fifteen minute cadence. One missed cycle is a
  # transient; alerting on it would train the reader to ignore the alert.
  window_duration = var.no_cycle_window

  criteria {
    query                   = file("${path.module}/queries/no-cycle.kql")
    time_aggregation_method = "Total"
    metric_measure_column   = "CompletedCycles"
    threshold               = 0
    operator                = "LessThanOrEqual"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = true
  action {
    action_groups = [azurerm_monitor_action_group.this.id]
  }

  tags = var.tags
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "drawdown" {
  name                = "alert-${var.name_prefix}-drawdown"
  resource_group_name = var.resource_group_name
  location            = var.location

  scopes               = [var.log_analytics_workspace_id]
  severity             = 2
  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"

  criteria {
    query                   = file("${path.module}/queries/drawdown.kql")
    time_aggregation_method = "Maximum"
    metric_measure_column   = "MaxDrawdown"
    threshold               = var.drawdown_alert_ratio
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  auto_mitigation_enabled = true
  action {
    action_groups = [azurerm_monitor_action_group.this.id]
  }

  tags = var.tags
}

# The workbook is a JSON file in the repository, not something drawn in the
# portal. A dashboard that only exists in a portal is lost with the environment
# and cannot be reviewed in a pull request.
resource "azurerm_application_insights_workbook" "this" {
  name                = var.workbook_uuid
  resource_group_name = var.resource_group_name
  location            = var.location
  display_name        = "Trading bot — ${var.name_prefix}"
  source_id           = lower(var.log_analytics_workspace_id)
  category            = "workbook"

  data_json = templatefile("${path.module}/workbook.json", {
    workspace_id = var.log_analytics_workspace_id
  })

  tags = var.tags
}
