# Commit and push today's progress, and log it in DEVLOG.md.
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\daily-push.ps1 -Message "DE-1: Airflow DAG ingests Olist into raw schema"
#   add -NoLog to skip the DEVLOG entry
param(
    [Parameter(Mandatory = $true)][string]$Message,
    [switch]$NoLog
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Safety: only ever commit inside this portfolio repository.
$top = (git rev-parse --show-toplevel) -replace '/', '\'
if ($top -ne $root) {
    Write-Error "Git root is '$top', expected '$root'. Aborting so nothing outside the portfolio is committed."
    exit 1
}

if (-not $NoLog) {
    $log = Join-Path $root 'DEVLOG.md'
    $today = Get-Date -Format 'yyyy-MM-dd'
    $content = [IO.File]::ReadAllText($log, [Text.Encoding]::UTF8)
    $entry = ''
    if (-not $content.EndsWith("`n")) { $entry += "`n" }
    if ($content -notmatch "(?m)^## $today\s*$") { $entry += "`n## $today`n`n" }
    $entry += "- $Message`n"
    [IO.File]::AppendAllText($log, $entry, (New-Object Text.UTF8Encoding $false))
}

git add -A
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host 'Nothing to commit.'
    exit 0
}

git commit -m $Message
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git push
exit $LASTEXITCODE
