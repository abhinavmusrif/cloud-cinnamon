param(
 [ValidateSet('SSH','SSM','ExistingTunnel')][string]$Transport='SSH',
 [ValidatePattern('^[a-zA-Z0-9_.@-]+$')][string]$SshHost,
 [ValidatePattern('^[a-zA-Z0-9_.-]+$')][string]$AwsProfile,
 [ValidatePattern('^[a-z0-9-]+$')][string]$Region,
 [ValidatePattern('^i-[a-f0-9]+$')][string]$InstanceId,
 [ValidateRange(1024,65535)][int]$LocalPort=50001,
 [switch]$EnableTextHistory
)
$ErrorActionPreference='Stop'
$state=Join-Path $env:LOCALAPPDATA 'CloudCinnamon'
New-Item -ItemType Directory -Path $state -Force | Out-Null
$tunnel=$null
$guard=[Threading.Mutex]::new($false,('Local\CloudCinnamon-Connect-'+$LocalPort))
$owned=$false
try {$owned=$guard.WaitOne(0)} catch [Threading.AbandonedMutexException] {$owned=$true}
if(-not $owned){$guard.Dispose();throw 'A connection launcher for this local port is already running.'}
try {
if(Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue) {
 if($Transport -ne 'ExistingTunnel'){throw 'Port already occupied. Verify it, then explicitly use ExistingTunnel.'}
} elseif($Transport -eq 'ExistingTunnel'){throw 'No existing listener.'}
try {
 if($Transport -eq 'SSH') {
  if(-not $SshHost -or $SshHost.StartsWith('-')){throw 'Supply a known SSH host or user@host. Authenticate with SSH first.'}
  $ssh=(Get-Command ssh.exe -ErrorAction Stop).Source
  $tunnel=Start-Process -FilePath $ssh -ArgumentList @('-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=20','-o','ServerAliveCountMax=3','-L',"127.0.0.1:${LocalPort}:127.0.0.1:3389",$SshHost) -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $state 'tunnel-error.log')
 } elseif($Transport -eq 'SSM') {
  if(-not $AwsProfile -or -not $Region -or -not $InstanceId -or $AwsProfile.StartsWith('-')){throw 'Supply AwsProfile, Region, InstanceId. Authenticate AWS CLI first.'}
  $aws=(Get-Command aws.exe -ErrorAction Stop).Source
  $tunnel=Start-Process -FilePath $aws -ArgumentList @('ssm','start-session','--profile',$AwsProfile,'--region',$Region,'--target',$InstanceId,'--document-name','AWS-StartPortForwardingSession','--parameters',"portNumber=3389,localPortNumber=$LocalPort") -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $state 'tunnel.log') -RedirectStandardError (Join-Path $state 'tunnel-error.log')
 }
 $ready=$false
 for($i=0;$i -lt 60;$i++) {
  if($tunnel -and $tunnel.HasExited){throw 'Tunnel exited; inspect the local tunnel-error.log. No credential values are printed.'}
  if(Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue){$ready=$true;break}
  Start-Sleep -Milliseconds 500
 }
 if(-not $ready){throw 'Tunnel did not open within 30 seconds.'}
 # Bind RDP to loopback. Certificate warnings remain visible for human review.
 $rdp=Join-Path $state 'desktop.rdp'
 (Get-Content (Join-Path $PSScriptRoot 'desktop.rdp.example') -Raw).Replace('127.0.0.1:50001',"127.0.0.1:$LocalPort") | Set-Content -LiteralPath $rdp -Encoding ascii
 $arguments='-STA -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'Rdp-ClipboardPng.ps1')+'"'
 if($EnableTextHistory){$arguments+=' -EnableTextHistory'}
 Start-Process -FilePath (Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList $arguments -WindowStyle Hidden | Out-Null
 $client=Start-Process mstsc.exe -ArgumentList ('"'+$rdp+'"') -PassThru
 $client.WaitForExit()
} finally {
 if($tunnel -and -not $tunnel.HasExited){Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue}
}
} finally {
 if($owned){$guard.ReleaseMutex()}
 $guard.Dispose()
}
