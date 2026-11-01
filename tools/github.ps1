# GitHub & Git helper tool for midev-tools
# Usage:
#   .\tools\github.ps1 info
#   .\tools\github.ps1 status
#   .\tools\github.ps1 commit -Message <Msg>
#   .\tools\github.ps1 push
#   .\tools\github.ps1 sync -Message <Msg>
param(
    [Parameter(Position = 0)]
    [ValidateSet("info", "status", "commit", "sync", "push")]
    [string]$Command = "status",

    [Parameter()]
    [string]$Message = "Update midev-tools",

    [Parameter()]
    [string[]]$Paths = @(),

    [Parameter()]
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$tokenFile = Join-Path $root "git_full_access_token.txt"
if (-not (Test-Path $tokenFile)) {
    throw "Missing token file: $tokenFile"
}
$token = (Get-Content -Raw $tokenFile).Trim()
$headers = @{
    Authorization          = "Bearer $token"
    Accept                 = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent"           = "PowerShell"
}

switch ($Command) {
    "info" {
        $repo = Invoke-RestMethod -Uri "https://api.github.com/repos/mikhaprive-flows/midev-tools" -Headers $headers -Method Get
        Write-Host "Repository : $($repo.full_name)"
        Write-Host "URL        : $($repo.html_url)"
        Write-Host "Visibility : $(if ($repo.private) { 'Private' } else { 'Public' })"
        Write-Host "Default Br : $($repo.default_branch)"
    }

    "status" {
        git status -s
        Write-Host "`nRecent commits:"
        git log -n 5 --pretty=format:"%h | %an | %ad | %s" --date=short 2>$null
        Write-Host ""
    }

    "push" {
        $ErrorActionPreference = "Continue"
        git push origin $Branch
    }

    "commit" {
        $ErrorActionPreference = "Continue"
        if ($Paths.Count -gt 0) {
            foreach ($p in $Paths) {
                if (Test-Path $p) {
                    git add -- $p
                }
            }
        } else {
            git add -A
        }
        git reset -q -- git_full_access_token.txt 2>$null
        git commit -m "$Message"
    }

    "sync" {
        $ErrorActionPreference = "Continue"
        if ($Paths.Count -gt 0) {
            foreach ($p in $Paths) {
                if (Test-Path $p) {
                    git add -- $p
                }
            }
        } else {
            git add -A
        }
        git reset -q -- git_full_access_token.txt 2>$null
        git commit -m "$Message"
        git pull --rebase origin $Branch 2>$null
        git push origin $Branch
        Write-Host "[GitHub] Synced successfully to $Branch : $Message"
    }
}
