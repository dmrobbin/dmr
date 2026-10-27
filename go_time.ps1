# PowerShell version of go_time.sh: a shortcut for manage.py using the project's .venv.
#   .\go_time.ps1                              # no command: run the dev server
#   .\go_time.ps1 fetch_sets 290 291           # any manage.py command and its options
#   .\go_time.ps1 list_expansions nikke
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$manage = Join-Path $PSScriptRoot "manage.py"
if ($args.Count -eq 0) { $args = @("runserver") }
& $python $manage @args
exit $LASTEXITCODE
