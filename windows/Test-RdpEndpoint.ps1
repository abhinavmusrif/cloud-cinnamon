function Test-RdpEndpoint {
  param([ValidateRange(1024,65535)][int]$Port, [ValidateRange(100,10000)][int]$TimeoutMs = 2000)
  # Negotiate TLS only; never authenticate or create a desktop session.
  $tcp = New-Object Net.Sockets.TcpClient
  try {
    $pending = $tcp.BeginConnect('127.0.0.1', $Port, $null, $null)
    try {
      if (-not $pending.AsyncWaitHandle.WaitOne($TimeoutMs)) { return $false }
      $tcp.EndConnect($pending)
    } finally { $pending.AsyncWaitHandle.Close() }
    $stream = $tcp.GetStream()
    $stream.ReadTimeout = $TimeoutMs
    $stream.WriteTimeout = $TimeoutMs
    [byte[]]$request = 3,0,0,19,14,224,0,0,0,0,0,1,0,8,0,1,0,0,0
    $stream.Write($request,0,$request.Length)
    $reply = New-Object byte[] 19
    $offset = 0
    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMs)
    while ($offset -lt $reply.Length) {
      $remaining = [int]($deadline - [DateTime]::UtcNow).TotalMilliseconds
      if ($remaining -le 0) { return $false }
      $stream.ReadTimeout = [Math]::Max(1,$remaining)
      $count = $stream.Read($reply,$offset,$reply.Length-$offset)
      if ($count -eq 0) { return $false }
      $offset += $count
    }
    return ($reply[0] -eq 3 -and $reply[1] -eq 0 -and $reply[2] -eq 0 -and
      $reply[3] -eq 19 -and $reply[4] -eq 14 -and $reply[5] -eq 208 -and
      $reply[11] -eq 2 -and $reply[13] -eq 8 -and $reply[14] -eq 0 -and
      $reply[15] -eq 1 -and $reply[16] -eq 0 -and $reply[17] -eq 0 -and $reply[18] -eq 0)
  } catch { return $false }
  finally { $tcp.Dispose() }
}
