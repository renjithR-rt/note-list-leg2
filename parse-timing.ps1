param(
    [string]$LogFile   = "",
    [string]$ProjectDir = "E:\Claude\note-list-leg1\output\pipeline-runs",
    [string]$MwuFilter  = ""
)

# Collect log content
if ($LogFile) {
    $allContent = Get-Content $LogFile
} else {
    $logs = Get-ChildItem $ProjectDir -Filter "*.log" -ErrorAction SilentlyContinue |
        Where-Object { ($MwuFilter -eq "") -or ($_.Name -match $MwuFilter) } |
        Sort-Object LastWriteTime
    Write-Host "Parsing $($logs.Count) log file(s)..." -ForegroundColor Cyan
    $allContent = $logs | ForEach-Object { Get-Content $_.FullName }
}

$phases  = @()
$current = $null

foreach ($line in $allContent) {
    # Extract timestamp
    $ts = $null
    if ($line -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+") {
        $ts = [datetime]$Matches[1]
    }

    # Extract MWU
    $mwu = ""
    if ($line -match "\[worker:(.+?)\]") { $mwu = $Matches[1] }

    # Phase START
    if ($line -match "START — (.+?)\s*[▶◀─]+\s*$" -or $line -match "START — (.+)") {
        $current = @{
            Phase       = $Matches[1].Trim()
            Start       = $ts
            End         = $null
            MWU         = $mwu
            DurationSec = 0
        }
    }

    if ($current -and $mwu) { $current.MWU = $mwu }

    # Duration line
    if ($current -and $line -match "Duration:\s+(\d+)s") {
        $current.DurationSec = [int]$Matches[1]
    }

    # Phase FINISH
    if ($current -and ($line -match "FINISH —" -or $line -match "◀◀◀")) {
        $current.End = $ts
        $phases += [PSCustomObject]@{
            MWU         = $current.MWU
            Phase       = $current.Phase
            Start       = $current.Start
            End         = $current.End
            DurationSec = $current.DurationSec
        }
        $current = $null
    }
}

Write-Host "`n=== PIPELINE PHASE TIMING ===" -ForegroundColor Cyan

$results = $phases | ForEach-Object {
    $dur = if ($_.DurationSec -gt 0) {
        $_.DurationSec
    } elseif ($_.Start -and $_.End) {
        [int]($_.End - $_.Start).TotalSeconds
    } else { 0 }

    [PSCustomObject]@{
        MWU      = $_.MWU
        Phase    = $_.Phase
        Start    = if ($_.Start) { $_.Start.ToString("HH:mm:ss") } else { "—" }
        "Sec"    = $dur
        "Min"    = [math]::Round($dur / 60, 1)
    }
}

$results | Format-Table MWU, Phase, Start, Sec, Min -AutoSize

# Totals per MWU
Write-Host "── TOTALS PER MWU" -ForegroundColor Yellow
$results | Group-Object MWU | ForEach-Object {
    $totalSec = ($_.Group | Measure-Object "Sec" -Sum).Sum
    Write-Host ("  {0,-20} {1,5}s  {2} min" -f $_.Name, $totalSec, [math]::Round($totalSec/60,1))
}

# Grand total
$grand = ($results | Measure-Object "Sec" -Sum).Sum
Write-Host "`n── GRAND TOTAL: $grand sec  ($([math]::Round($grand/60,1)) min)  |  Phases: $($results.Count)" -ForegroundColor Green
