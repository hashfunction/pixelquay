// Copyright 2026 Trieflow LLC. MIT. Eager Unicode clipboard data; capture only.
using System;
using System.ComponentModel;
using System.Runtime.ExceptionServices;
using System.Runtime.InteropServices;
namespace TintFableMarketing {
 internal interface IClipboardApi {
  uint CurrentThread(); long CreateOwner(); void DestroyOwner(long owner);
  void Open(long owner); void Close(); int Count(); long Owner(); uint Sequence();
  void Empty(); void WriteUnicode(string text); string ReadUnicode();
 }
 public sealed class FilenameClipboard {
  readonly IClipboardApi api; readonly string text; readonly uint thread;
  bool finished;
  public long Owner { get; private set; }
  public uint Sequence { get; private set; }
  public uint BeforeCloseSequence { get; private set; }
  FilenameClipboard(string value,IClipboardApi native) {text=value;api=native;thread=api.CurrentThread();}
  public static FilenameClipboard Begin(string text) {return Begin(text,new NativeClipboard());}
  internal static FilenameClipboard Begin(string text,IClipboardApi api) {
   if(String.IsNullOrEmpty(text) || text.Length>4096 || text.IndexOf('\0')>=0)throw new ArgumentException("Invalid bounded capture clipboard text");
   var lease=new FilenameClipboard(text,api);lease.Owner=api.CreateOwner();
   try {
    lease.Locked(delegate {
     // A NULL owner is NOT proof of an empty clipboard. Count under the lock
     // before any mutation; the isolated capture only accepts an empty baseline.
     if(api.Count()!=0)throw new InvalidOperationException("Initial clipboard is not empty; preserved");
     api.Empty();api.WriteUnicode(text);lease.Sequence=api.Sequence();lease.Match();lease.BeforeCloseSequence=lease.Sequence;
    });
    // Publishing is complete only after CloseClipboard. Windows can synthesize
    // companion text formats then, advancing the sequence without changing our
    // owner or eager Unicode data. Establish the lease in one fresh locked read.
    lease.Locked(delegate {
     if(api.Owner()!=lease.Owner || api.ReadUnicode()!=text)
      throw new InvalidOperationException("Clipboard publication owner/text changed; data preserved");
     lease.Sequence=api.Sequence();lease.Match();
    });
    return lease;
   }catch(Exception first) {
    try{api.DestroyOwner(lease.Owner);}catch(Exception cleanup){throw new AggregateException(first,cleanup);}
    throw;
   }
  }
  void Active() {
   if(finished)throw new InvalidOperationException("Clipboard lease already finished; no replay");
   if(api.CurrentThread()!=thread)throw new InvalidOperationException("Clipboard owner thread changed");
  }
  void Match() {
   uint observed=api.Sequence();long owner=api.Owner();bool sameText=api.ReadUnicode()==text;
   if(Sequence==0 || observed!=Sequence || owner!=Owner || !sameText)
    throw new InvalidOperationException("Clipboard changed; data preserved. Expected sequence="+Sequence+", actual="+observed+", expected owner="+Owner+", actual="+owner+", same Unicode="+sameText);
  }
  void Locked(Action operation) {
   api.Open(Owner);Exception failure=null;
   try{operation();}catch(Exception error){failure=error;}
   try{api.Close();}catch(Exception cleanup){failure=failure==null?cleanup:new AggregateException(failure,cleanup);}
   if(failure!=null)ExceptionDispatchInfo.Capture(failure).Throw();
  }
  public void Verify() {Active();Locked(Match);}
  public void RestoreEmpty() {
   Active();finished=true;Exception failure=null;
   try {
    // Never erase a changed clipboard, even if the new text happens to match.
    Locked(delegate {Match();api.Empty();if(api.Count()!=0)throw new InvalidOperationException("Clipboard empty baseline was not restored");});
   }catch(Exception error){failure=error;}
   try{api.DestroyOwner(Owner);}catch(Exception cleanup){failure=failure==null?cleanup:new AggregateException(failure,cleanup);}
   if(failure!=null)ExceptionDispatchInfo.Capture(failure).Throw();
  }
 }
 internal sealed class NativeClipboard : IClipboardApi {
  const uint UnicodeText=13;
  static void Check(bool ok,string operation){if(!ok)throw new Win32Exception(Marshal.GetLastWin32Error(),operation);}
  public uint CurrentThread(){return GetCurrentThreadId();}
  public long CreateOwner() {
   // A message-only standard window owns eager data without becoming visible
   // or activating. OpenClipboard(NULL) cannot establish a SetClipboardData owner.
   IntPtr window=CreateWindowExW(0,"STATIC","TintFable capture clipboard",0,0,0,0,0,new IntPtr(-3),IntPtr.Zero,IntPtr.Zero,IntPtr.Zero);
   Check(window!=IntPtr.Zero,"Create capture clipboard owner");return window.ToInt64();
  }
  public void DestroyOwner(long owner){Check(DestroyWindow(new IntPtr(owner)),"Destroy capture clipboard owner");}
  public void Open(long owner){Check(OpenClipboard(new IntPtr(owner)),"Open capture clipboard; not retried");}
  public void Close(){Check(CloseClipboard(),"Close capture clipboard");}
  public int Count(){int count=CountClipboardFormats();if(count==0 && Marshal.GetLastWin32Error()!=0)throw new Win32Exception(Marshal.GetLastWin32Error(),"Count clipboard formats");return count;}
  public long Owner(){return GetClipboardOwner().ToInt64();}
  public uint Sequence(){return GetClipboardSequenceNumber();}
  public void Empty(){Check(EmptyClipboard(),"Restore/claim empty capture clipboard");}
  public void WriteUnicode(string text) {
   char[] chars=(text+"\0").ToCharArray();IntPtr memory=GlobalAlloc(0x42,new UIntPtr(checked((uint)chars.Length*2)));
   Check(memory!=IntPtr.Zero,"Allocate eager Unicode clipboard data");bool transferred=false;
   Exception failure=null;
   try {
    WithMemory(memory,delegate(IntPtr pointer){Marshal.Copy(chars,0,pointer,chars.Length);});
    Check(SetClipboardData(UnicodeText,memory)!=IntPtr.Zero,"Transfer eager Unicode clipboard data");transferred=true;
   }catch(Exception error){failure=error;}
   // Ownership transfers to Windows only on successful SetClipboardData.
   if(!transferred){try{Check(GlobalFree(memory)==IntPtr.Zero,"Free untransferred clipboard data");}catch(Exception cleanup){failure=failure==null?cleanup:new AggregateException(failure,cleanup);}}
   if(failure!=null)ExceptionDispatchInfo.Capture(failure).Throw();
  }
  public string ReadUnicode() {
   IntPtr memory=GetClipboardData(UnicodeText);Check(memory!=IntPtr.Zero,"Read eager Unicode clipboard data");
   ulong size=GlobalSize(memory).ToUInt64();
   if(size<2 || size>16384 || size%2!=0)throw new InvalidOperationException("Unbounded Unicode clipboard allocation");
   string result=null;
   WithMemory(memory,delegate(IntPtr pointer) {
    string value=Marshal.PtrToStringUni(pointer,checked((int)size/2));int end=value.IndexOf('\0');
    if(end<0 || end>4096)throw new InvalidOperationException("Unterminated/bounded Unicode clipboard readback");
    result=value.Substring(0,end);
   });return result;
  }
  static void WithMemory(IntPtr memory,Action<IntPtr> operation) {
   IntPtr pointer=GlobalLock(memory);Check(pointer!=IntPtr.Zero,"Lock clipboard memory");Exception failure=null;
   try{operation(pointer);}catch(Exception error){failure=error;}
   try{Unlock(memory);}catch(Exception cleanup){failure=failure==null?cleanup:new AggregateException(failure,cleanup);}
   if(failure!=null)ExceptionDispatchInfo.Capture(failure).Throw();
  }
  static void Unlock(IntPtr memory){bool locked=GlobalUnlock(memory);if(!locked && Marshal.GetLastWin32Error()!=0)throw new Win32Exception(Marshal.GetLastWin32Error(),"Unlock clipboard memory");}
  [DllImport("kernel32.dll")]static extern uint GetCurrentThreadId();
  [DllImport("user32.dll",CharSet=CharSet.Unicode,ExactSpelling=true,SetLastError=true)]static extern IntPtr CreateWindowExW(uint ex,string cls,string name,uint style,int x,int y,int width,int height,IntPtr parent,IntPtr menu,IntPtr instance,IntPtr parameter);
  [DllImport("user32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]static extern bool DestroyWindow(IntPtr window);
  [DllImport("user32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]static extern bool OpenClipboard(IntPtr window);
  [DllImport("user32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]static extern bool CloseClipboard();
  [DllImport("user32.dll",SetLastError=true)]static extern int CountClipboardFormats();
  [DllImport("user32.dll")]static extern IntPtr GetClipboardOwner();
  [DllImport("user32.dll")]static extern uint GetClipboardSequenceNumber();
  [DllImport("user32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]static extern bool EmptyClipboard();
  [DllImport("user32.dll",SetLastError=true)]static extern IntPtr SetClipboardData(uint format,IntPtr memory);
  [DllImport("user32.dll",SetLastError=true)]static extern IntPtr GetClipboardData(uint format);
  [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr GlobalAlloc(uint flags,UIntPtr bytes);
  [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr GlobalLock(IntPtr memory);
  [DllImport("kernel32.dll",SetLastError=true)][return:MarshalAs(UnmanagedType.Bool)]static extern bool GlobalUnlock(IntPtr memory);
  [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr GlobalFree(IntPtr memory);
  [DllImport("kernel32.dll",SetLastError=true)]static extern UIntPtr GlobalSize(IntPtr memory);
 }
}
