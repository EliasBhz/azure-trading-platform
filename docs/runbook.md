# Runbook

Operational procedures for `azure-trading-platform`.

This file is a stub. Each section is written in phase 6, once the corresponding
alert and infrastructure actually exist. The sections are listed now so that the
incidents to cover are agreed up front.

## Planned sections

- Trading job execution failed
- No cycle executed in the last N minutes
- Drawdown alert fired
- Database unreachable from the job
- Activating and clearing the kill switch
- Rotating exchange API keys
- Rebuilding the whole environment from scratch after credit expiry

## Tearing down the dev environment

`terraform destroy` removes every managed resource and then fails on the
resource group itself:

    Error: deleting Resource Group "rg-tradingbot-dev-neu": the Resource Group
    still contains Resources

Azure creates an action group named `Application Insights Smart Detection`
alongside Application Insights. Terraform does not manage it, and the provider
is configured to refuse deleting a group that holds resources it does not know
about. Delete it, then re-run the destroy:

    az monitor action-group delete -g rg-tradingbot-dev-neu -n "Application Insights Smart Detection"
    terraform -chdir=infra/envs/dev destroy -var subscription_id=<SUBSCRIPTION_ID>

Verify nothing is left, including a soft-deleted vault that would block the
next apply on a reserved name:

    az group list --query "[].name" -o tsv
    az keyvault list-deleted --query "[].name" -o tsv
