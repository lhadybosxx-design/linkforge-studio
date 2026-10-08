Set-Location $PSScriptRoot
if (Test-Path "data\analytics.db") {
    Remove-Item "data\analytics.db"
    Write-Host "✓ analytics.db deleted" -ForegroundColor Green
}
if (Test-Path "data\tracker_map.json") {
    Remove-Item "data\tracker_map.json"
    Write-Host "✓ tracker_map.json deleted" -ForegroundColor Green
}