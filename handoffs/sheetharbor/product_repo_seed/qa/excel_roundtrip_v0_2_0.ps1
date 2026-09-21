param(
    [Parameter(Mandatory = $false)]
    [string]$ArtifactDir = ".",
    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "qa-results/excel"
)

$ErrorActionPreference = "Stop"
$Tolerance = 1e-9

$Products = @(
    @{
        Id = "SH-CANDLE"; File = "SheetHarbor_Candle_Economics_v0.2.0-alpha.xlsx"
        Sha256 = "b289019dbf6c129d640a7b431ab52f3431f9f6d5bf0ead387b309341005631ba"
        Sheet = "Candle Calculator"
        Checks = @{"B16"=50.0;"B32"=265.9166666666667;"B33"=5.539930555555556;"B35"=11.834908361970218;"B37"=0.45;"B40"=0.06379831831105186}
    },
    @{
        Id = "SH-FDM"; File = "SheetHarbor_FDM_3D_Printing_Economics_v0.2.0-alpha.xlsx"
        Sha256 = "94d69ceecf4f894ddacc8ae36f882dde25a918072aa7b802f2b9039a4631a94c"
        Sheet = "Job Calculator"
        Checks = @{"B19"=5.0;"B30"=69.04710144927536;"B32"=129.43383448462683;"B33"=12.943383448462683;"B35"=0.4;"B37"=44.377314680443476}
    },
    @{
        Id = "SH-EMB"; File = "SheetHarbor_Embroidery_Economics_v0.2.0-alpha.xlsx"
        Sha256 = "384108221ab99173f91c54d7b5cacbf1c24212b76ea07d05cd56c168fe37bc8d"
        Sheet = "Job Calculator"
        Checks = @{"B17"=25.0;"B32"=435.2363888888889;"B34"=845.7017259978427;"B35"=35.237571916576776;"B37"=0.45;"B38"=290.87830066167845}
    },
    @{
        Id = "SH-SCREEN"; File = "SheetHarbor_Screen_Printing_Economics_v0.2.0-alpha.xlsx"
        Sha256 = "702b5fd6fdcdc69638d570699b323c021b18d3540241d63a24a2828169241b84"
        Sheet = "Worked Example"
        Checks = @{"G6"=50.0;"G14"=279.00666666666666;"G15"=490.0116959064327;"G16"=10.208576998050681;"G17"=171.5040935672514;"G18"=0.35}
    }
)

function Release-ComObjectSafely([object]$Object) {
    if ($null -ne $Object -and [System.Runtime.InteropServices.Marshal]::IsComObject($Object)) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($Object)
    }
}

function Get-FormulaErrorCount([object]$Worksheet) {
    $xlCellTypeFormulas = -4123
    $xlErrors = 16
    try {
        $errors = $Worksheet.UsedRange.SpecialCells($xlCellTypeFormulas, $xlErrors)
        $count = [int]$errors.Count
        Release-ComObjectSafely $errors
        return $count
    } catch { return 0 }
}

function Test-WorkbookState([object]$Workbook, [hashtable]$Product, [string]$Stage) {
    $worksheet = $null
    $failures = New-Object System.Collections.Generic.List[string]
    try {
        $worksheet = $Workbook.Worksheets.Item($Product.Sheet)
        foreach ($address in $Product.Checks.Keys) {
            $cell = $null
            try {
                $cell = $worksheet.Range($address)
                $actual = [double]$cell.Value2
                $expected = [double]$Product.Checks[$address]
                $delta = [math]::Abs($actual - $expected)
                $scale = [math]::Max(1.0, [math]::Abs($expected))
                if (($delta / $scale) -gt $Tolerance) {
                    $failures.Add("$Stage $($Product.Sheet)!$address expected=$expected actual=$actual")
                }
                if (-not [bool]$cell.HasFormula) {
                    $failures.Add("$Stage $($Product.Sheet)!$address lost formula")
                }
            } finally { Release-ComObjectSafely $cell }
        }
        $formulaErrors = Get-FormulaErrorCount $worksheet
        if ($formulaErrors -gt 0) {
            $failures.Add("$Stage $($Product.Sheet) contains $formulaErrors formula error cell(s)")
        }
    } catch {
        $failures.Add("$Stage worksheet check failed: $($_.Exception.Message)")
    } finally { Release-ComObjectSafely $worksheet }
    return @($failures)
}

$artifactRoot = (Resolve-Path $ArtifactDir).Path
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$outputRoot = (Resolve-Path $OutputDir).Path
$excel = $null
$results = New-Object System.Collections.Generic.List[object]
$overallFailures = New-Object System.Collections.Generic.List[string]

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    try { $excel.AutomationSecurity = 3 } catch { }
    $excelVersion = [string]$excel.Version
    $excelBuild = [string]$excel.Build

    foreach ($product in $Products) {
        $source = Join-Path $artifactRoot $product.File
        $result = [ordered]@{
            product_id=$product.Id; source_file=$product.File
            source_sha256_expected=$product.Sha256; source_sha256_actual=$null
            excel_version=$excelVersion; excel_build=$excelBuild
            first_open_checks="pending"; reopen_checks="pending"
            roundtrip_file=$null; roundtrip_sha256=$null; failures=@()
        }
        $failures = New-Object System.Collections.Generic.List[string]

        if (-not (Test-Path $source)) {
            $failures.Add("Missing source artifact: $source")
        } else {
            $actualHash = (Get-FileHash -Algorithm SHA256 -Path $source).Hash.ToLowerInvariant()
            $result.source_sha256_actual = $actualHash
            if ($actualHash -ne $product.Sha256) {
                $failures.Add("Source SHA-256 mismatch expected=$($product.Sha256) actual=$actualHash")
            }
        }

        if ($failures.Count -eq 0) {
            $roundtripName = [System.IO.Path]::GetFileNameWithoutExtension($product.File) + "-excel-roundtrip.xlsx"
            $roundtripPath = Join-Path $outputRoot $roundtripName
            Copy-Item -Force $source $roundtripPath
            $result.roundtrip_file = $roundtripName
            $workbook = $null

            try {
                $workbook = $excel.Workbooks.Open($roundtripPath, 0, $false)
                $excel.CalculateFullRebuild()
                $stageFailures = @(Test-WorkbookState $workbook $product "first-open")
                foreach ($f in $stageFailures) { $failures.Add($f) }
                if ($stageFailures.Count -eq 0) { $result.first_open_checks = "pass" } else { $result.first_open_checks = "fail" }
                $workbook.Save()
                $workbook.Close($true)
                Release-ComObjectSafely $workbook
                $workbook = $null

                $workbook = $excel.Workbooks.Open($roundtripPath, 0, $false)
                $excel.CalculateFullRebuild()
                $reopenFailures = @(Test-WorkbookState $workbook $product "reopen")
                foreach ($f in $reopenFailures) { $failures.Add($f) }
                if ($reopenFailures.Count -eq 0) { $result.reopen_checks = "pass" } else { $result.reopen_checks = "fail" }
                $workbook.Close($false)
                Release-ComObjectSafely $workbook
                $workbook = $null

                $result.roundtrip_sha256 = (Get-FileHash -Algorithm SHA256 -Path $roundtripPath).Hash.ToLowerInvariant()
            } catch {
                $failures.Add("Excel COM round trip failed: $($_.Exception.Message)")
                if ($null -ne $workbook) { try { $workbook.Close($false) } catch { } }
            } finally { Release-ComObjectSafely $workbook }
        }

        $result.failures = @($failures)
        if ($failures.Count -gt 0) {
            foreach ($f in $failures) { $overallFailures.Add("$($product.Id): $f") }
        }
        $results.Add([pscustomobject]$result)
    }

    $evidence = [ordered]@{
        gate="microsoft_excel_roundtrip"
        tested_at_utc=[DateTime]::UtcNow.ToString("o")
        excel_version=$excelVersion; excel_build=$excelBuild
        products=@($results); pass=($overallFailures.Count -eq 0)
        failures=@($overallFailures)
    }
    $evidencePath = Join-Path $outputRoot "excel-roundtrip-results.json"
    $evidence | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $evidencePath

    if ($overallFailures.Count -gt 0) {
        Write-Host "GATE: FAIL ($($overallFailures.Count) failure(s))"
        foreach ($failure in $overallFailures) { Write-Host " - $failure" }
        exit 1
    }

    Write-Host "GATE: PASS (4/4 products; Microsoft Excel $excelVersion build $excelBuild; open/recalc/save/reopen verified)"
    exit 0
}
finally {
    if ($null -ne $excel) { try { $excel.Quit() } catch { } }
    Release-ComObjectSafely $excel
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
