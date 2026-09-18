# Runbook

Operational procedures for `azure-trading-platform`.

This file is a stub. Each section is written in phase 6, once the corresponding
alert and infrastructure actually exist. The sections are listed now so that the
incidents to cover are agreed up front.

## Still to write

- Database unreachable from the job
- Rotating exchange API keys

## Where to look first

Every alert below is backed by a query over the bot's own structured logs. The
workbook runs the same queries, so if a workbook panel is empty the alert that
depends on it is blind too.

    az monitor log-analytics query       --workspace <WORKSPACE_GUID>       --analytics-query "ContainerAppConsoleLogs_CL | where ContainerName_s == 'trading-cycle' | extend p = parse_json(Log_s) | project TimeGenerated, Message = tostring(p.message), Outcome = tostring(p.outcome), Reason = tostring(p.reason) | order by TimeGenerated desc | take 20"

Get the workspace GUID with:

    az monitor log-analytics workspace show -g <RG> -n log-tradingbot-dev --query customerId -o tsv

## Alert: alert-tradingbot-dev-cycle-failed

The bot logged `cycle.failed` or `cycle.crashed`. `failed` is a known error type
the bot raised deliberately; `crashed` is an unhandled exception and always
deserves a look at the stack trace.

1. Find the failures and their error type:

       ContainerAppConsoleLogs_CL
       | where ContainerName_s == "trading-cycle"
       | extend p = parse_json(Log_s)
       | where tostring(p.message) in ("cycle.failed", "cycle.crashed")
       | project TimeGenerated, tostring(p.error_type), tostring(p.error)
       | order by TimeGenerated desc

2. `ExchangeError` on stale market data is usually the venue, not us. Confirm
   the next scheduled cycle recovers before doing anything.
3. A repeated `ConfigurationError` means the environment is wrong, not the
   market. Check the job's environment variables and the Key Vault secrets.
4. Nothing needs restarting by hand: the next cron execution is the retry. Fix
   the cause, not the symptom.

## Alert: alert-tradingbot-dev-no-cycle

No `cycle.completed` in the last 45 minutes, which is three missed executions.
This is the failure mode a scheduled job has and a running service does not:
nothing errors, nothing alerts, and the bot simply stops trading.

1. Check whether executions are being created at all:

       az containerapp job execution list -n caj-tradingbot-dev-cycle -g <RG>          --query "[].{name:name, status:properties.status, start:properties.startTime}" -o tsv

2. No executions at all means the schedule or the job is gone. Confirm the job
   exists and that `terraform plan` reports no drift.
3. Executions present but failing means this alert is a symptom; the
   `cycle-failed` alert is the one to work from.
4. Executions succeeding but no `cycle.completed` line means log ingestion is
   broken, not the bot. Check the Log Analytics daily quota: hitting the cap
   drops telemetry silently.

       az monitor log-analytics workspace show -g <RG> -n log-tradingbot-dev          --query "{quota:workspaceCapping.dailyQuotaGb, reset:workspaceCapping.quotaNextResetTime}"

## Alert: alert-tradingbot-dev-drawdown

Intraday drawdown passed the configured fraction of the day's opening equity.

**This alert is informational, not an incident.** The policy engine already
refuses to place orders once the daily loss limit is reached, and it records the
refusal. The alert exists because a bot that correctly stopped trading looks
exactly like a bot that quietly died.

1. Confirm the policy engine is refusing rather than failing:

       ContainerAppConsoleLogs_CL
       | where ContainerName_s == "trading-cycle"
       | extend p = parse_json(Log_s)
       | where tostring(p.message) == "cycle.decision"
       | project TimeGenerated, Outcome = tostring(p.outcome), Reason = tostring(p.reason)
       | order by TimeGenerated desc

   `outcome=hold` with `reason=daily loss limit reached` is the system working.

2. The limit resets at the first equity snapshot of the next UTC day. Nothing
   needs doing to resume trading.
3. If the drawdown is larger than the configured daily loss limit should allow,
   that is a real defect in the policy engine. Stop the bot with the kill switch
   before investigating.

## Activating and clearing the kill switch

The kill switch is a Key Vault secret so that tripping it is a secret update
rather than a redeployment.

    az keyvault secret set --vault-name <VAULT> --name kill-switch --value true
    az keyvault secret set --vault-name <VAULT> --name kill-switch --value false

The job reads it at execution start, so the next scheduled cycle honours it.
Setting it does not stop an execution already running.

Confirm it took effect on the next cycle:

    ContainerAppConsoleLogs_CL
    | where ContainerName_s == "trading-cycle"
    | extend p = parse_json(Log_s)
    | where tostring(p.message) == "cycle.decision"
    | project TimeGenerated, KillSwitch = tobool(p.kill_switch_engaged), Reason = tostring(p.reason)
    | order by TimeGenerated desc
    | take 5

Writing the secret needs Key Vault Secrets Officer on the vault. Being
subscription Owner is not enough: that is a control-plane role and this is a
data action.

## "Caller is not authorized" when running Terraform locally

    Error: making Read request on Azure KeyVault Secret ...
    StatusCode=403 ... Assignment: (not found)

Your identity holds no Key Vault Secrets Officer role on the vault, so Terraform
cannot read the existing secrets to build a plan. Being subscription Owner is
not enough: that is a control-plane role and reading a secret is a data action.

The configuration grants the role to every identity listed in
`secret_writer_principal_ids`, but it cannot apply itself without the permission
it grants. Break the cycle with a targeted apply, which refreshes only the
role assignment and therefore never touches the secrets:

    terraform -chdir=infra/envs/dev apply       -target='module.keyvault.azurerm_role_assignment.secrets_officer["operator"]'       -var subscription_id=<SUBSCRIPTION_ID>

Terraform warns that applied changes may be incomplete. That is expected and is
the point of the targeted run.

Role assignments are eventually consistent. If the next plan still returns 403,
wait and retry rather than granting anything else.

If your identity is not in the variable's default, add it there first. Do not
grant it out of band with `az role assignment create`: Terraform would then plan
to create an assignment Azure already has and the next apply fails with
`RoleAssignmentExists`.

## "RoleAssignmentExists" during a deployment

    Error: unexpected status 409 (409 Conflict) with error: RoleAssignmentExists

Two entries in `secret_writer_principal_ids` resolve to the same principal. A
role assignment is identified by principal, scope and role, so Azure rejects the
duplicate even though the map keys differ.

This happened when one entry was derived from whoever ran apply: locally it
resolved to a person, in the pipeline to the pipeline's own service principal,
which already had its own named entry. Worse, each run destroyed the other
identity's assignment before trying to recreate it.

Never derive an entry from the caller. List every identity explicitly, so the
plan is identical no matter who runs it.

### If a failed deployment left the environment without its jobs

A failed `Apply the platform` step can destroy the Container Apps jobs before
failing, because the first pass runs with `jobs_enabled=false`. The bot then
stops trading silently, which the no-cycle alert reports within forty-five
minutes.

Confirm and repair:

    az containerapp job list -g <RG> --query "[].name" -o tsv
    terraform -chdir=infra/envs/dev apply       -var subscription_id=<SUBSCRIPTION_ID>       -var image_tag=<SHA ALREADY IN THE REGISTRY>

Pass the tag that is already in the registry. Applying with the default tag
would point the jobs at an image that may not exist and Azure rejects the job
with `MANIFEST_UNKNOWN`.

## Rebuilding the whole environment from scratch

The deployment pipeline does this unattended, which is the point of phase 4.
Push to `main`, approve the deployment on the `dev` environment, and it runs
apply, push, apply, migrate and a smoke test.

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
