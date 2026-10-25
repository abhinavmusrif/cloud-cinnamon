$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
foreach($file in Get-ChildItem (Join-Path $root 'windows') -Filter '*.ps1') {
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
 if($errors.Count){throw ($file.Name+': '+($errors.Message -join '; '))}
 Write-Output ('PowerShell parse OK: '+$file.Name)
}
python -m unittest discover -s (Join-Path $root 'tests') -p 'test_repository.py' -v
if($LASTEXITCODE){throw 'Repository tests failed'}
