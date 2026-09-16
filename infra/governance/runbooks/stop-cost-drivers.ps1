<#
    Stops the PostgreSQL Flexible Servers belonging to this project.

    Invoked by an action group when the subscription budget reaches 100 percent
    of its ceiling. PostgreSQL is around ninety percent of the running cost, and
    stopping it is reversible and keeps the data, which is why this stops the
    server rather than deleting anything. Deleting would also desynchronise the
    Terraform state, turning a cost incident into an infrastructure incident.

    Servers are selected by tag, never by name, so a server created later is
    covered without editing this script, and a server belonging to something
    else is never touched.

    ARM is called through Invoke-AzRestMethod rather than the Az.PostgreSql
    cmdlets. Az.Accounts ships with the Automation account; Az.PostgreSql would
    have to be imported from the PowerShell Gallery, and an automation that only
    runs during an incident must not depend on a module import that can fail
    quietly months earlier.
#>

$ErrorActionPreference = 'Stop'

$SubscriptionId = '${subscription_id}'
$ProjectTag     = '${project_tag}'
$ApiVersion     = '2024-08-01'

Write-Output "Connecting with the automation account's managed identity."
Connect-AzAccount -Identity -SubscriptionId $SubscriptionId | Out-Null

$listUri = "/subscriptions/$SubscriptionId/providers/Microsoft.DBforPostgreSQL/flexibleServers?api-version=$ApiVersion"
$response = Invoke-AzRestMethod -Method GET -Path $listUri

if ($response.StatusCode -ne 200) {
    throw "Listing flexible servers failed with HTTP $($response.StatusCode): $($response.Content)"
}

$servers = ($response.Content | ConvertFrom-Json).value
if (-not $servers) {
    Write-Output 'No PostgreSQL Flexible Server in this subscription. Nothing to stop.'
    return
}

$stopped = 0
$skipped = 0

foreach ($server in $servers) {
    $tagValue = $null
    if ($server.tags) { $tagValue = $server.tags.project }

    if ($tagValue -ne $ProjectTag) {
        Write-Output "Skipping $($server.name): project tag is '$tagValue', not '$ProjectTag'."
        $skipped++
        continue
    }

    if ($server.properties.state -eq 'Stopped') {
        Write-Output "Skipping $($server.name): already stopped."
        $skipped++
        continue
    }

    Write-Output "Stopping $($server.name)."
    $stopUri = "$($server.id)/stop?api-version=$ApiVersion"
    $stopResponse = Invoke-AzRestMethod -Method POST -Path $stopUri

    # 202 Accepted is the normal answer: stopping is asynchronous.
    if ($stopResponse.StatusCode -notin @(200, 202)) {
        throw "Stopping $($server.name) failed with HTTP $($stopResponse.StatusCode): $($stopResponse.Content)"
    }

    $stopped++
}

Write-Output "Done. Stopped: $stopped. Skipped: $skipped."

# A stopped Flexible Server restarts by itself after seven days. This buys time
# and makes the spend visible; it is not a permanent ceiling.
Write-Output 'Reminder: Azure restarts a stopped Flexible Server automatically after seven days.'
