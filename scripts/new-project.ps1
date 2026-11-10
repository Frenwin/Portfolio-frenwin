# Create a new project folder from templates\project-README.md.
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\new-project.ps1 -Role 01-data-engineer -Name de-01-elt-bigquery-dbt -Title "Batch ELT to BigQuery with dbt"
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('01-data-engineer', '02-data-analyst', '03-data-scientist', '04-ai-engineer')]
    [string]$Role,
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Title
)

$root = Split-Path -Parent $PSScriptRoot
$dir = Join-Path $root (Join-Path $Role $Name)
if (Test-Path $dir) {
    Write-Error "Folder already exists: $dir"
    exit 1
}

$roleNames = @{
    '01-data-engineer'  = 'Data Engineer'
    '02-data-analyst'   = 'Data Analyst'
    '03-data-scientist' = 'Data Scientist'
    '04-ai-engineer'    = 'AI Engineer'
}

New-Item -ItemType Directory -Path (Join-Path $dir 'docs') -Force | Out-Null
New-Item -ItemType File -Path (Join-Path $dir 'docs\.gitkeep') | Out-Null

$template = [IO.File]::ReadAllText((Join-Path $root 'templates\project-README.md'), [Text.Encoding]::UTF8)
$readme = $template.Replace('{{TITLE}}', $Title).Replace('{{ROLE}}', $roleNames[$Role]).Replace('{{DATE}}', (Get-Date -Format 'yyyy-MM-dd'))
[IO.File]::WriteAllText((Join-Path $dir 'README.md'), $readme, (New-Object Text.UTF8Encoding $false))

Write-Host "Created $dir"
Write-Host "Next: update the Status column in README.md and $Role\README.md to 'In progress'."
