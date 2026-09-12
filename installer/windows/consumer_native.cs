// Copyright 2026 Trieflow LLC. MIT licensed.
// Qualification input only; this assembly is never loaded by PixelQuay.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
namespace PixelQuayQualification {
public sealed class ConsumerTargetEvidence {
    public bool AppLive, TargetLive, MainLive, WindowLive, Visible, Enabled;
    public int AppPid, MainPid, TargetPid, WindowPid;
    public long Main, Window, Foreground;
    public long[] Owners;
    public string ExpectedTitle, Title;
}
public static class ConsumerNative {
    public static void Validate(ConsumerTargetEvidence e,bool foreground) {
        if(!e.AppLive || !e.TargetLive || !e.MainLive || !e.WindowLive || !e.Visible || !e.Enabled ||
            e.Main==0 || e.Window==0 || e.AppPid<=0 || e.TargetPid<=0 || e.AppPid!=e.MainPid || e.TargetPid!=e.WindowPid ||
            e.Owners==null || Array.IndexOf(e.Owners,e.Main)<0 || e.ExpectedTitle!=e.Title ||
            (foreground && e.Foreground!=e.Window))throw new InvalidOperationException("Exact consumer process/window/foreground ownership changed");
    }
    [DllImport("user32.dll")] static extern bool IsWindow(IntPtr w);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr w);
    [DllImport("user32.dll")] static extern bool IsWindowEnabled(IntPtr w);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr w, uint command);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr w, out uint pid);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr w);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr w, StringBuilder value, int count);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr w, StringBuilder value, int count);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumCallback cb, IntPtr data);
    delegate bool EnumCallback(IntPtr w, IntPtr data);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr w, out RECT rect);
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int index);
    [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint count, INPUT[] inputs, int size);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] struct KEY { public ushort Vk, Scan; public uint Flags, Time; public UIntPtr Extra; }
    [StructLayout(LayoutKind.Sequential)] struct MOUSE { public int X,Y; public uint Data,Flags,Time; public UIntPtr Extra; }
    [StructLayout(LayoutKind.Explicit)] struct UNION { [FieldOffset(0)] public KEY Key; [FieldOffset(0)] public MOUSE Mouse; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint Type; public UNION Value; }
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint WaitForSingleObject(Microsoft.Win32.SafeHandles.SafeProcessHandle handle, uint timeout);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetExitCodeProcess(Microsoft.Win32.SafeHandles.SafeProcessHandle handle, out uint code);
    public static int? ExitCode(Process process,int timeout) {
        var handle=process.SafeHandle;
        if(handle.IsInvalid || handle.IsClosed)throw new InvalidOperationException("Retained process handle is unavailable");
        uint status=WaitForSingleObject(handle,checked((uint)timeout));
        if(status==258)return null;
        uint code;
        if(status!=0 || !GetExitCodeProcess(handle,out code))throw new InvalidOperationException("Retained process exit is unproven");
        return unchecked((int)code);
    }
    public static int Pid(long w) { uint p; GetWindowThreadProcessId((IntPtr)w, out p); return checked((int)p); }
    public static long ForegroundWindow() { return GetForegroundWindow().ToInt64(); }
    public static string Title(long w) { var s=new StringBuilder(4096); GetWindowText((IntPtr)w,s,s.Capacity); return s.ToString(); }
    public static string Class(long w) { var s=new StringBuilder(256); GetClassName((IntPtr)w,s,s.Capacity); return s.ToString(); }
    public static long[] Owners(long w) {
        var r=new List<long>();
        while(w!=0 && r.Count<8 && !r.Contains(w) && IsWindow((IntPtr)w)) { r.Add(w); w=GetWindow((IntPtr)w,4).ToInt64(); }
        return r.ToArray();
    }
    public static long[] Windows(long main) {
        var r=new List<long>(); int observed=0;
        EnumCallback cb=(w,d)=> { observed++; if(observed>256)return false; if(IsWindowVisible(w) && Array.IndexOf(Owners(w.ToInt64()),main)>=0)r.Add(w.ToInt64()); return true; };
        EnumWindows(cb,IntPtr.Zero); GC.KeepAlive(cb);
        if(observed>256)throw new InvalidOperationException("Window inventory exceeded bound");
        return r.ToArray();
    }
    public static void Require(Process app, long main, Process target, long w, string title, bool foreground) {
        Validate(new ConsumerTargetEvidence {
            AppLive=!app.SafeHandle.IsInvalid && !app.SafeHandle.IsClosed && !app.HasExited,
            TargetLive=!target.SafeHandle.IsInvalid && !target.SafeHandle.IsClosed && !target.HasExited,
            MainLive=IsWindow((IntPtr)main),WindowLive=IsWindow((IntPtr)w),Visible=IsWindowVisible((IntPtr)w),Enabled=IsWindowEnabled((IntPtr)w),
            AppPid=app.Id,MainPid=Pid(main),TargetPid=target.Id,WindowPid=Pid(w),Main=main,Window=w,Foreground=ForegroundWindow(),
            Owners=Owners(w),ExpectedTitle=title,Title=Title(w)
        },foreground);
    }
    public static void Foreground(Process app,long main,Process target,long w,string title) {
        Require(app,main,target,w,title,false);
        for(int i=0;i<20;i++) { SetForegroundWindow((IntPtr)w); if(ForegroundWindow()==w) { Require(app,main,target,w,title,true); return; } Thread.Sleep(50); }
        throw new InvalidOperationException("Owned window could not become foreground");
    }
    public static int[] Bounds(Process app,long main,Process target,long w,string title) {
        Require(app,main,target,w,title,true); RECT r;
        if(!GetWindowRect((IntPtr)w,out r))throw new InvalidOperationException("Window bounds unavailable");
        int x=GetSystemMetrics(76),y=GetSystemMetrics(77),width=GetSystemMetrics(78),height=GetSystemMetrics(79);
        if(r.Left<x || r.Top<y || r.Right>x+width || r.Bottom>y+height || r.Right<=r.Left || r.Bottom<=r.Top || (long)(r.Right-r.Left)*(r.Bottom-r.Top)>16000000)
            throw new InvalidOperationException("Owned window is not fully visible within bounded desktop");
        return new int[]{r.Left,r.Top,r.Right-r.Left,r.Bottom-r.Top,x,y,width,height};
    }
    static INPUT Key(ushort vk,ushort scan,uint flags) { return new INPUT { Type=1, Value=new UNION { Key=new KEY { Vk=vk,Scan=scan,Flags=flags } } }; }
    static void Send(Process app,long main,Process target,long w,string title,INPUT[] inputs) {
        Require(app,main,target,w,title,true);
        if(SendInput((uint)inputs.Length,inputs,Marshal.SizeOf<INPUT>())!=inputs.Length)throw new InvalidOperationException("Partial native input delivery");
        Thread.Sleep(100);
    }
    public static void Chord(Process app,long main,Process target,long w,string title,int[] keys) {
        if(keys.Length<1 || keys.Length>3)throw new ArgumentException("Unbounded chord");
        var inputs=new INPUT[keys.Length*2];
        for(int i=0;i<keys.Length;i++) { if(keys[i]<1 || keys[i]>255)throw new ArgumentException("Invalid key"); inputs[i]=Key((ushort)keys[i],0,0); inputs[inputs.Length-1-i]=Key((ushort)keys[i],0,2); }
        Send(app,main,target,w,title,inputs);
    }
    public static void Text(Process app,long main,Process target,long w,string title,string text) {
        if(text.Length==0 || text.Length>4096 || text.IndexOf('\0')>=0)throw new ArgumentException("Unbounded text");
        var inputs=new INPUT[text.Length*2];
        for(int i=0;i<text.Length;i++) { inputs[2*i]=Key(0,text[i],4); inputs[2*i+1]=Key(0,text[i],6); }
        Send(app,main,target,w,title,inputs);
    }
}
}
