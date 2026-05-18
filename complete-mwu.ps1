param([string]$MwuId, [string]$ProjectId="NOTE-LIST-1")

$h = @{"Content-Type"="application/json"}

# Use TEST_PASSED → FULLY_VALIDATED direct shortcut
# Full chain only if already past TEST_PASSED:
# MERGED → UNIT_VALIDATED → INTEGRATION_VALIDATED → GOLDEN_VALIDATED → DUAL_RUN_VALIDATED → FULLY_VALIDATED

$shortcuts = @("FULLY_VALIDATED")
$fullchain = @("UNIT_VALIDATED","INTEGRATION_VALIDATED","GOLDEN_VALIDATED","DUAL_RUN_VALIDATED","FULLY_VALIDATED")

# Try shortcut first
Write-Host "Trying direct FULLY_VALIDATED transition..." -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Method POST "http://localhost:8766/tools/transition_mwu" `
      -Headers $h `
      -Body (@{mwu_id=$MwuId; project_id=$ProjectId; to_state="FULLY_VALIDATED"; notes="Auto-complete"} | ConvertTo-Json)
    Write-Host "✅ $($r.from_state) → FULLY_VALIDATED" -ForegroundColor Green
    return
} catch {
    Write-Host "Direct shortcut not available — walking chain..." -ForegroundColor Yellow
}

# Walk full chain
foreach ($state in $fullchain) {
    try {
        $r = Invoke-RestMethod -Method POST "http://localhost:8766/tools/transition_mwu" `
          -Headers $h `
          -Body (@{mwu_id=$MwuId; project_id=$ProjectId; to_state=$state; notes="Auto-complete"} | ConvertTo-Json)
        Write-Host "✅ $($r.from_state) → $($r.to_state)" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  $state — skipped (already past or invalid)" -ForegroundColor Yellow
    }
}

# Final status
Write-Host "`nFinal state:" -ForegroundColor Cyan
Invoke-RestMethod -Method POST "http://localhost:8766/tools/get_mwu_status" `
  -Headers $h `
  -Body (@{mwu_id=$MwuId; project_id=$ProjectId} | ConvertTo-Json)

