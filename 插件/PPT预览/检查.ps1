# PPT预览 插件的检查：本机有 PowerPoint（能被调用）或 LibreOffice（soffice）就能用。只看，不开任何程序。
if ([type]::GetTypeFromProgID('PowerPoint.Application')) { '用 PowerPoint'; exit 0 }
$soffice = (Get-Command soffice -ErrorAction SilentlyContinue).Source
if (-not $soffice) {
  foreach ($p in @("$env:ProgramFiles\LibreOffice\program\soffice.exe", "${env:ProgramFiles(x86)}\LibreOffice\program\soffice.exe")) {
    if ($p -and (Test-Path -LiteralPath $p)) { $soffice = $p; break }
  }
}
if ($soffice) { '用 LibreOffice'; exit 0 }
'没有 PowerPoint，也没有 LibreOffice：照 插件.md 的「安装」装一个'
exit 1
