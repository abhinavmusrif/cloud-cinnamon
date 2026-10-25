param([Parameter(Mandatory=$true)][uint32]$ExpectedSequence)
# One-shot, supervised text materializer. No text is logged or written to disk.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class RdpTextHistorySequence {
 [DllImport("user32.dll")] public static extern uint GetClipboardSequenceNumber();
 [DllImport("user32.dll")] public static extern IntPtr GetClipboardOwner();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
}
'@
function Result([string]$status,[uint32]$sequence=$ExpectedSequence) {
 @{Status=$status;Sequence=$sequence} | ConvertTo-Json -Compress
}
try {
 if([RdpTextHistorySequence]::GetClipboardSequenceNumber() -ne $ExpectedSequence){Result 'clipboard-changed';return}
 $owner=[uint32]0
 [void][RdpTextHistorySequence]::GetWindowThreadProcessId([RdpTextHistorySequence]::GetClipboardOwner(),[ref]$owner)
 $ownerProcess=Get-Process -Id $owner -ErrorAction SilentlyContinue
 if(-not $ownerProcess -or $ownerProcess.ProcessName -ne 'mstsc'){Result 'not-rdp';return}
 $source=[Windows.Forms.Clipboard]::GetDataObject()
 $formats=@($source.GetFormats($false))
 if($formats -contains 'ExcludeClipboardContentFromMonitorProcessing'){Result 'explicitly-protected';return}
 if(-not $source.GetDataPresent('UnicodeText',$false) -or $source.GetDataPresent('FileDrop',$true) -or $source.GetDataPresent('Bitmap',$true) -or $source.GetDataPresent('PNG',$false)){Result 'not-plain-text';return}
 $allowed=@('UnicodeText','Text','OEMText','Locale','Rich Text Format','HTML Format','Csv','CanIncludeInClipboardHistory','CanUploadToCloudClipboard')
 if(@($formats | Where-Object {$_ -notin $allowed}).Count){Result 'additional-formats-preserved';return}
 $value=$source.GetData('UnicodeText',$false)
 if($value -isnot [string] -or $value.Length -eq 0 -or $value.Length -gt 1048576){Result 'text-size-limit';return}
 if([RdpTextHistorySequence]::GetClipboardSequenceNumber() -ne $ExpectedSequence){Result 'clipboard-changed';return}
 $null=[Windows.ApplicationModel.DataTransfer.Clipboard,Windows.ApplicationModel.DataTransfer,ContentType=WindowsRuntime]
 $null=[Windows.ApplicationModel.DataTransfer.ClipboardHistoryItemsResult,Windows.ApplicationModel.DataTransfer,ContentType=WindowsRuntime]
 if(-not [Windows.ApplicationModel.DataTransfer.Clipboard]::IsHistoryEnabled()){Result 'history-disabled';return}
 $asTask=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'} | Select-Object -First 1
 function AwaitResult($op,[Type]$type) {
  $task=$asTask.MakeGenericMethod($type).Invoke($null,@($op))
  if(-not $task.Wait(500)){throw 'History service busy'}
  return $task.Result
 }
 $clock=[Diagnostics.Stopwatch]::StartNew()
 $history=AwaitResult ([Windows.ApplicationModel.DataTransfer.Clipboard]::GetHistoryItemsAsync()) ([Windows.ApplicationModel.DataTransfer.ClipboardHistoryItemsResult])
 if($history.Status.ToString() -ne 'Success'){Result 'history-unavailable';return}
 foreach($item in $history.Items) {
  if($clock.ElapsedMilliseconds -gt 1800){Result 'history-service-busy';return}
  if($item.Content.Contains('Text') -and (AwaitResult ($item.Content.GetTextAsync()) ([string])) -ceq $value){Result 'already-in-history';return}
 }
 $copy=[Windows.Forms.DataObject]::new()
 foreach($format in $formats) {
  if($format -in @('CanIncludeInClipboardHistory','CanUploadToCloudClipboard')){continue}
  $data=$source.GetData($format,$false)
  if($data -is [IO.MemoryStream]){
   if($data.Length -gt 4194304){Result 'format-size-limit';return}
   $data=[IO.MemoryStream]::new($data.ToArray())
  }
  if($null -ne $data){$copy.SetData($format,$false,$data)}
 }
 # Explicit local history eligibility, with cloud roaming kept disabled.
 $yes=[IO.MemoryStream]::new([BitConverter]::GetBytes([uint32]1))
 $no=[IO.MemoryStream]::new([BitConverter]::GetBytes([uint32]0))
 $copy.SetData('CanIncludeInClipboardHistory',$false,$yes)
 $copy.SetData('CanUploadToCloudClipboard',$false,$no)
 if([RdpTextHistorySequence]::GetClipboardSequenceNumber() -ne $ExpectedSequence){Result 'clipboard-changed';return}
 [Windows.Forms.Clipboard]::SetDataObject($copy,$true,3,40)
 Result 'history-enabled' ([RdpTextHistorySequence]::GetClipboardSequenceNumber())
} catch {
 Result ('unavailable-'+$_.Exception.GetType().Name)
}
