param([Parameter(Mandatory = $true)][string]$In, [Parameter(Mandatory = $true)][string]$Out)
# PPT预览 插件的转换：PPT → PDF。只读打开原文件，不改它；只写 -Out 这一个文件；不弹窗口。
$ErrorActionPreference = 'Stop'
if ([type]::GetTypeFromProgID('PowerPoint.Application')) {
  $pp = New-Object -ComObject PowerPoint.Application
  $had = $pp.Presentations.Count
  try {
    $pres = $pp.Presentations.Open($In, -1, 0, 0)            # 只读、不当新文件、不开窗口
    try { $pres.SaveAs($Out, 32) } finally { $pres.Close() }  # 32 = 存成 PDF
  } finally {
    if ($had -eq 0 -and $pp.Presentations.Count -eq 0) { $pp.Quit() }   # 你本来开着 PowerPoint 就不关它
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp)
  }
} else {
  $soffice = (Get-Command soffice -ErrorAction SilentlyContinue).Source
  if (-not $soffice) { $soffice = "$env:ProgramFiles\LibreOffice\program\soffice.exe" }
  if (-not (Test-Path -LiteralPath $soffice)) { Write-Error '没有 PowerPoint，也没有 LibreOffice'; exit 3 }
  $dir = Join-Path ([IO.Path]::GetTempPath()) ('ppt预览-' + [guid]::NewGuid())
  New-Item -ItemType Directory -Path $dir | Out-Null
  try {
    & $soffice --headless --convert-to pdf --outdir $dir $In | Out-Null
    $pdf = Get-ChildItem -LiteralPath $dir -Filter *.pdf | Select-Object -First 1
    if (-not $pdf) { exit 4 }
    Move-Item -LiteralPath $pdf.FullName -Destination $Out -Force
  } finally { Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue }
}
if (-not (Test-Path -LiteralPath $Out)) { exit 2 }
