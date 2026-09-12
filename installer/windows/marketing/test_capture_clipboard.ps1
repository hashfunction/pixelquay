$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$source=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'capture_clipboard.cs') -Raw
$fixture=@'
namespace TintFableMarketing {
 internal sealed class ReplayClipboard : IClipboardApi {
  internal int Formats,Empties,Writes,Destroyed,Opened,Closed; internal uint Stamp=5;
  internal long Owning; internal string Text=""; internal bool Busy,FailWrite,FailClose; internal uint Thread=17;
  public uint CurrentThread(){return Thread;}
  public long CreateOwner(){return 444;}
  public void DestroyOwner(long owner){if(owner!=444)throw new System.Exception("Wrong destroyed owner");Destroyed++;}
  public void Open(long owner){if(Busy)throw new System.Exception("Clipboard busy");Opened++;}
  public void Close(){Closed++;if(FailClose)throw new System.Exception("Clipboard close failed");}
  public int Count(){return Formats;}
  public long Owner(){return Owning;}
  public uint Sequence(){return Stamp;}
  public string ReadUnicode(){return Text;}
  public void Empty(){Empties++;Formats=0;Text="";Owning=444;Stamp++;}
  public void WriteUnicode(string text){Writes++;if(FailWrite)throw new System.Exception("Clipboard allocation/transfer failed");Formats=1;Text=text;Stamp++;}
 }
 public static class ClipboardReplay {
  static void Require(bool b,string message){if(!b)throw new System.Exception(message);}
  public static int Run() {
   const string path="C:\\TintFable Demo\\Cedar Coast – résumé.png";int cases=0;
   var api=new ReplayClipboard();var lease=FilenameClipboard.Begin(path,api);
   Require(lease.Owner==444 && lease.Sequence==7 && api.Opened==api.Closed,"Missing production publication proof");
   lease.Verify();lease.RestoreEmpty();Require(api.Formats==0 && api.Empties==2 && api.Writes==1 && api.Destroyed==1,"Empty baseline not restored exactly once");cases++;
   try{lease.RestoreEmpty();throw new System.Exception("Second restoration accepted");}catch(System.InvalidOperationException){}cases++;
   foreach(string failure in new[]{"nonempty-ownerless","nonempty-foreign","busy","write","close"}) {
    api=new ReplayClipboard();if(failure.StartsWith("nonempty")){api.Formats=2;api.Text="foreign";api.Owning=failure.EndsWith("foreign")?999:0;}
    api.Busy=failure=="busy";api.FailWrite=failure=="write";api.FailClose=failure=="close";bool refused=false;
    try{FilenameClipboard.Begin(path,api);}catch{refused=true;}
    Require(refused && api.Destroyed==1,"Publication failure accepted or owner leaked: "+failure);
    if(failure.StartsWith("nonempty") || failure=="busy")Require(api.Empties==0 && api.Writes==0,"Foreign/locked clipboard mutated");
    if(failure.StartsWith("nonempty"))Require(api.Text=="foreign" && api.Formats==2,"Foreign clipboard lost");cases++;
   }
   foreach(string change in new[]{"owner","sequence","unicode","same-text-new-sequence","unavailable-sequence","busy","thread"}) {
    api=new ReplayClipboard();lease=FilenameClipboard.Begin(path,api);
    if(change=="owner")api.Owning=999;
    if(change=="sequence" || change=="same-text-new-sequence")api.Stamp++;
    if(change=="unicode")api.Text="foreign";
    if(change=="unavailable-sequence")api.Stamp=0;
    if(change=="busy")api.Busy=true;
    if(change=="thread")api.Thread++;
    bool refused=false;try{lease.Verify();}catch{refused=true;}Require(refused,"Changed clipboard accepted before paste: "+change);
    string retained=api.Text;refused=false;try{lease.RestoreEmpty();}catch{refused=true;}
    Require(refused && api.Empties==1 && api.Text==retained,"Changed clipboard cleared: "+change);cases++;
   }
   foreach(string invalid in new[]{"",new string('x',4097),"a\0b"}) {
    api=new ReplayClipboard();bool refused=false;try{FilenameClipboard.Begin(invalid,api);}catch(System.ArgumentException){refused=true;}
    Require(refused && api.Opened==0 && api.Empties==0,"Invalid text reached native clipboard");cases++;
   }
   return cases;
  }
 }
}
'@
Add-Type -TypeDefinition ($source+"`n"+$fixture)
$count=[TintFableMarketing.ClipboardReplay]::Run()
Write-Output "PASS $count actual clipboard-lease policy replays: empty/foreign/ownerless, lock/transfer/close failures, stale owner/sequence/text/thread and no foreign clear."
if($IsWindows) {
 # Real eager Unicode allocation/transfer, native owner, sequence and cleanup.
 # This fixture deliberately shares production's truly-empty CI baseline gate.
 $lease=[TintFableMarketing.FilenameClipboard]::Begin('C:\TintFable Demo\Cedar Coast – résumé.png')
 try{$lease.Verify()}finally{$lease.RestoreEmpty()}
 Write-Output 'PASS actual Windows native eager Unicode clipboard publish/read/empty-baseline restore.'
}else{Write-Output 'SKIP actual Windows clipboard execution on this non-Windows host.'}
