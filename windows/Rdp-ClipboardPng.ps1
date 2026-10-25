param([switch]$EnableTextHistory)
# Session-scoped RDP image-format compatibility. No network or screenshot capture.
# Preserve native image formats, adding lossless PNG for capable RDP servers.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class RdpClipboardSequence {
 [DllImport("user32.dll")] public static extern uint GetClipboardSequenceNumber();
 [DllImport("user32.dll")] public static extern IntPtr GetClipboardOwner();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@
$mutex = [Threading.Mutex]::new($false, 'Local\CloudCinnamon-RDP-ClipboardPng')
$owned = $false
$log = Join-Path $PSScriptRoot 'rdp-clipboard-png.log'
$pidFile = Join-Path $PSScriptRoot 'rdp-clipboard-png.pid'
function WriteStatus([string]$message) {
 if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt 65536) {
  Move-Item -LiteralPath $log -Destination ($log + '.previous') -Force
 }
 Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' ' + $message)
}
try {
 try { $owned=$mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $owned=$true }
 if (-not $owned) { return }
 Set-Content -LiteralPath $pidFile -Value $PID -Encoding ascii
 $last=[uint32]::MaxValue
 $missing=0
 $failures=0
 $ticks=0
 while ($true) {
  if ($ticks % 10 -eq 0) {
   if (@(Get-Process mstsc -ErrorAction SilentlyContinue).Count -eq 0) { $missing++ } else { $missing=0 }
   if ($missing -ge 30) { break }
  }
  $ticks++
  $seq=[RdpClipboardSequence]::GetClipboardSequenceNumber()
  if ($seq -ne $last) {
   $image=$null
   try {
    $ownerPid=[uint32]0
    [void][RdpClipboardSequence]::GetWindowThreadProcessId([RdpClipboardSequence]::GetClipboardOwner(),[ref]$ownerPid)
    $ownerProcess=Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
    # Never render remote bitmaps here. Ordinary remote text gets a bounded,
    # separate worker so delayed clipboard rendering cannot stall image support.
    if ($ownerProcess -and $ownerProcess.ProcessName -eq 'mstsc') {
     $last=$seq
     $textSource=[Windows.Forms.Clipboard]::GetDataObject()
     if ($EnableTextHistory -and $textSource -and $textSource.GetDataPresent('UnicodeText',$false) -and -not $textSource.GetDataPresent('Bitmap',$true) -and -not $textSource.GetDataPresent('PNG',$false)) {
      $worker=Join-Path $PSScriptRoot 'Rdp-TextHistory.ps1'
      if(Test-Path -LiteralPath $worker) {
       $info=[Diagnostics.ProcessStartInfo]::new()
       $info.FileName=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
       $info.Arguments='-STA -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$worker+'" -ExpectedSequence '+$seq
       $info.UseShellExecute=$false;$info.CreateNoWindow=$true
       $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
       $child=[Diagnostics.Process]::Start($info)
       try {
        if($child.WaitForExit(4000)) {
         $output=$child.StandardOutput.ReadToEnd()
         if($child.ExitCode -eq 0 -and $output.Trim()) {
          $state=$output | ConvertFrom-Json
          if($state.Status -eq 'history-enabled'){$last=[uint32]$state.Sequence}
          WriteStatus ('remote-text '+$state.Status)
         }
        } else {
         $child.Kill();[void]$child.WaitForExit(1000)
         WriteStatus 'remote-text worker-timeout'
        }
       } finally {$child.Dispose()}
      }
     }
     continue
    }
    $source=[Windows.Forms.Clipboard]::GetDataObject()
    if ($null -eq $source -or $source.GetDataPresent('PNG',$false) -or -not $source.GetDataPresent([Windows.Forms.DataFormats]::Bitmap,$true)) {
     $last=$seq
    } else {
     $formats=@($source.GetFormats($false))
     # Mixed text/files/HTML clipboards must retain their original semantics.
     $extra=@($formats | Where-Object { $_ -notin @('Bitmap','DeviceIndependentBitmap','Format17') })
     if ($extra.Count -gt 0) { $last=$seq } else {
      $watch=[Diagnostics.Stopwatch]::StartNew()
      $image=[Windows.Forms.Clipboard]::GetImage()
      if ($null -eq $image -or [long]$image.Width*$image.Height -gt 33554432) { $last=$seq } else {
       $stream=[IO.MemoryStream]::new()
       $image.Save($stream,[Drawing.Imaging.ImageFormat]::Png)
       if ($stream.Length -le 67108864 -and [RdpClipboardSequence]::GetClipboardSequenceNumber() -eq $seq) {
        $copy=[Windows.Forms.DataObject]::new()
        foreach ($format in $formats) {
         $value=$source.GetData($format,$false)
         if ($null -ne $value) { $copy.SetData($format,$false,$value) }
        }
        $stream.Position=0
        $copy.SetData('PNG',$false,$stream)
        # Check once more after delayed rendering; never replace a newer copy.
        if ([RdpClipboardSequence]::GetClipboardSequenceNumber() -eq $seq) {
         [Windows.Forms.Clipboard]::SetDataObject($copy,$true,3,40)
         $last=[RdpClipboardSequence]::GetClipboardSequenceNumber()
         WriteStatus ('png-added width='+$image.Width+' height='+$image.Height+' bytes='+$stream.Length+' elapsed_ms='+$watch.ElapsedMilliseconds)
         $failures=0
        }
       }
       $stream.Dispose()
      }
     }
    }
   } catch {
    $failures++
    if ($failures -eq 1 -or $failures % 20 -eq 0) { WriteStatus ('clipboard-busy '+$_.Exception.GetType().Name) }
    if ($failures -ge 20) { $last=$seq; $failures=0 }
   } finally { if ($null -ne $image) { $image.Dispose() } }
  }
  Start-Sleep -Milliseconds 100
 }
} finally {
 if ($owned) {
  if ((Test-Path -LiteralPath $pidFile) -and (Get-Content -LiteralPath $pidFile -Raw).Trim() -eq $PID.ToString()) {
   Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
  }
  $mutex.ReleaseMutex()
 }
 $mutex.Dispose()
}
