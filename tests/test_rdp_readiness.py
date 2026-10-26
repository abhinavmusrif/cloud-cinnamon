"""Protocol readiness regressions. A listening socket must not imply usable RDP."""
import pathlib,shutil,socket,subprocess,threading,time,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
PS=shutil.which('powershell.exe')
@unittest.skipUnless(PS,'Windows PowerShell required')
class RdpReadinessTests(unittest.TestCase):
 def probe(self,mode):
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);port=listener.getsockname()[1]
  reply=bytes.fromhex('030000130ed000001234000201080001000000')
  def serve():
   try:
    listener.settimeout(5)
    conn,_=listener.accept()
    with conn:
     conn.settimeout(2);conn.recv(256)
     if mode=='valid':conn.sendall(reply)
     elif mode=='fragmented':
      for b in reply:conn.sendall(bytes([b]));time.sleep(.003)
     elif mode=='invalid':conn.sendall(b'HTTP/1.1 200 OK\r\n\r\nxx')
     elif mode=='failure':conn.sendall(reply[:11]+bytes([3])+reply[12:])
     elif mode=='timeout':time.sleep(.8)
   except (OSError,TimeoutError):pass
   finally:listener.close()
  thread=threading.Thread(target=serve,daemon=True);thread.start()
  path=str(ROOT/'windows/Test-RdpEndpoint.ps1').replace("'","''")
  started=time.monotonic();r=subprocess.run([PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',f". '{path}'; Test-RdpEndpoint -Port {port} -TimeoutMs 300"],capture_output=True,text=True,timeout=8)
  thread.join(2);self.assertEqual(r.returncode,0,r.stderr);self.assertLess(time.monotonic()-started,5)
  return r.stdout.strip()
 def test_valid_tls_negotiation(self):self.assertEqual(self.probe('valid'),'True')
 def test_fragmented_response(self):self.assertEqual(self.probe('fragmented'),'True')
 def test_wrong_protocol_rejected(self):self.assertEqual(self.probe('invalid'),'False')
 def test_rdp_failure_rejected(self):self.assertEqual(self.probe('failure'),'False')
 def test_silent_listener_rejected(self):self.assertEqual(self.probe('timeout'),'False')
 def test_closed_listener_rejected(self):self.assertEqual(self.probe('closed'),'False')
if __name__=='__main__':unittest.main()
