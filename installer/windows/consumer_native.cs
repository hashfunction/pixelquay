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
public sealed class FileNameAncestorEvidence {
    public long Window, Parent;
    public int ProcessId, ControlId;
    public bool Descendant;
    public string Class;
}
public sealed class FileNameEvidence {
    public long Window, Focus, ExpectedFocus, Active;
    public int DialogPid, FocusPid;
    public bool Exists, Visible, Enabled, Descendant, ReadOnly, HasFileNameId;
    public string Class;
    // Read-only refusal diagnostics. They do not authorize a different focus route.
    public long Style, FinalFocus, FinalActive;
    public uint DialogThread, FocusThread;
    public bool AncestryReachedDialog, AncestryTruncated, FinalFocusObserved;
    public string ObservationStage;
    public string[] FailedPredicates;
    public FileNameAncestorEvidence[] Ancestors;
}
public sealed class NativeButtonEvidence {
    public long Window, Parent, Style;
    public int ProcessId, ControlId;
    public string Class, Label;
    public bool Exists, Visible, Enabled, Descendant;
    public uint Thread;
}
public sealed class ChooseButtonEvidence {
    public long Window, Filename, Button, Parent, DialogItem, NextTab, Focus, Active, Style, FinalFocus, FinalActive;
    public int DialogPid, ButtonPid, ControlId, CandidateCount;
    public string Class, Label, ObservationStage;
    public uint DialogThread, ButtonThread;
    public bool Exists, Visible, Enabled, Descendant, FinalFocusObserved;
    public NativeButtonEvidence[] Candidates;
}
public sealed class ConsumerGeometry {
    // Raw native x,y,width,height values, without cropping or DPI conversion.
    public int[] Window, Desktop, WorkArea;
    public uint Dpi;
}
public static class ConsumerNative {
    public static void ValidateChooseButton(ChooseButtonEvidence e,string title,bool focused,ChooseButtonEvidence retained) {
        if(e==null || title!="Export destination" || e.Window==0 || e.Filename==0 || e.Button==0 || e.Button==e.Filename ||
            e.Parent!=e.Window || e.DialogItem!=e.Button || e.NextTab!=e.Button || e.Active!=e.Window ||
            e.Focus!=(focused?e.Button:e.Filename) || e.DialogPid<=0 || e.ButtonPid!=e.DialogPid || e.ControlId<=0 ||
            e.DialogThread==0 || e.ButtonThread!=e.DialogThread || e.Class!="Button" || e.Label!="Choose" ||
            !e.Exists || !e.Visible || !e.Enabled || !e.Descendant || e.CandidateCount!=1 ||
            (e.Style&0x50010000)!=0x50010000 || (e.Style&15)>1 ||
            (focused && retained==null) || (retained!=null && (e.Window!=retained.Window || e.Filename!=retained.Filename ||
                e.Button!=retained.Button || e.ControlId!=retained.ControlId || e.DialogPid!=retained.DialogPid || e.DialogThread!=retained.DialogThread))) {
            var error=new InvalidOperationException("Exact source-labelled native Choose button/focus ownership is unproven");
            error.Data["PixelQuay.ChooseButtonEvidence"]=e;throw error;
        }
    }
    public static bool FileNameReadOnly(long style) {
        // A visible child Edit necessarily has nonzero WS_VISIBLE/WS_CHILD
        // style bits. Zero is unavailable data, never proof of writability.
        if(style==0)throw new InvalidOperationException("Native filename style unavailable");
        return (style & 0x800)!=0;
    }
    // Windows run34681764386: the modern Save dialog uses this exact native
    // filename chain. A generic Edit1001 or any other dialog is insufficient.
    public static bool IsObservedModernSaveFileName(FileNameEvidence e,string title) {
        if(title!="Save Image File" || e==null || !e.AncestryReachedDialog || e.AncestryTruncated ||
            e.Ancestors==null || e.Ancestors.Length!=5 || e.Focus==0 || e.Window==0 || e.DialogPid<=0)return false;
        string[] classes={"Edit","ComboBox","FloatNotifySink","DirectUIHWND","DUIViewWndClassName"};
        foreach(var node in e.Ancestors)if(node==null)return false;
        var seen=new HashSet<long>();
        for(int i=0;i<classes.Length;i++) {
            var a=e.Ancestors[i];
            if(a==null || a.Window==0 || a.Window==e.Window || !seen.Add(a.Window) ||
                a.ProcessId!=e.DialogPid || !a.Descendant || a.Class!=classes[i] ||
                a.ControlId!=(i==0?1001:0) || (i==0 && a.Window!=e.Focus) ||
                a.Parent!=(i==classes.Length-1?e.Window:e.Ancestors[i+1].Window))return false;
        }
        return true;
    }
    // Windows run34682286222 and ExportRecipeDialog.ChooseDestination:
    // SelectFolder exposes this single direct-child folder Edit. The exact
    // title/topology identifies the field; all later input guards still apply.
    public static bool IsObservedExportFolderName(FileNameEvidence e,string title) {
        if(title!="Export destination" || e==null || !e.AncestryReachedDialog || e.AncestryTruncated ||
            e.Ancestors==null || e.Ancestors.Length!=1 || e.Focus==0 || e.Window==0 || e.DialogPid<=0 ||
            e.DialogThread==0 || e.FocusThread!=e.DialogThread)return false;
        var a=e.Ancestors[0];
        return a!=null && a.Window!=0 && a.Window!=e.Window && a.Window==e.Focus &&
            a.Parent==e.Window && a.ProcessId==e.DialogPid && a.Descendant &&
            a.Class=="Edit" && a.ControlId==1152;
    }
    public static void ValidateFileName(FileNameEvidence e) {
        var failures=new List<string>();
        if(e.Window==0)failures.Add("window");
        if(e.Focus==0)failures.Add("focus");
        if(e.ExpectedFocus!=0 && e.Focus!=e.ExpectedFocus)failures.Add("retained_focus");
        if(e.Active!=e.Window)failures.Add("active_window");
        if(e.DialogPid<=0)failures.Add("dialog_pid");
        if(e.FocusPid!=e.DialogPid)failures.Add("focus_pid");
        if(!e.Exists)failures.Add("exists");
        if(!e.Visible)failures.Add("visible");
        if(!e.Enabled)failures.Add("enabled");
        if(!e.Descendant)failures.Add("descendant");
        if(e.ReadOnly)failures.Add("writable");
        if(!e.HasFileNameId)failures.Add("filename_id_1148");
        if(e.Class!="Edit")failures.Add("edit_class");
        e.FailedPredicates=failures.ToArray();
        if(failures.Count!=0) {
            var error=new InvalidOperationException("Focused native filename control differs from the exact owned dialog: "+string.Join(",",failures));
            error.Data["PixelQuay.FileNameEvidence"]=e;
            throw error;
        }
    }
    public static void Validate(ConsumerTargetEvidence e,bool foreground) {
        if(!e.AppLive || !e.TargetLive || !e.MainLive || !e.WindowLive || !e.Visible || !e.Enabled ||
            e.Main==0 || e.Window==0 || e.AppPid<=0 || e.TargetPid<=0 || e.AppPid!=e.MainPid || e.TargetPid!=e.WindowPid ||
            e.Owners==null || Array.IndexOf(e.Owners,e.Main)<0 || e.ExpectedTitle!=e.Title ||
            (foreground && e.Foreground!=e.Window))throw new InvalidOperationException("Exact consumer process/window/foreground ownership changed");
    }
    [DllImport("user32.dll")] static extern bool IsWindow(IntPtr w);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr w);
    [DllImport("user32.dll")] static extern bool IsWindowEnabled(IntPtr w);
    [DllImport("user32.dll")] static extern bool IsChild(IntPtr parent, IntPtr child);
    [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr child);
    [DllImport("user32.dll")] static extern int GetDlgCtrlID(IntPtr child);
    [DllImport("user32.dll")] static extern IntPtr GetDlgItem(IntPtr dialog,int id);
    [DllImport("user32.dll")] static extern IntPtr GetNextDlgTabItem(IntPtr dialog,IntPtr control,bool previous);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr parent,EnumCallback cb,IntPtr data);
    [DllImport("user32.dll",EntryPoint="GetWindowLongPtrW",SetLastError=true)] static extern IntPtr GetWindowLongPtr(IntPtr child,int index);
    [DllImport("user32.dll",SetLastError=true)] static extern bool GetGUIThreadInfo(uint thread,ref GUIINFO info);
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr SendMessageTimeoutW(IntPtr window,uint message,UIntPtr count,StringBuilder text,uint flags,uint timeout,out UIntPtr result);
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
    [DllImport("user32.dll")] static extern IntPtr MonitorFromWindow(IntPtr w,uint flags);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern bool GetMonitorInfoW(IntPtr monitor,ref MONITORINFO info);
    [DllImport("user32.dll")] static extern uint GetDpiForWindow(IntPtr w);
    [DllImport("user32.dll",SetLastError=true)] static extern bool MoveWindow(IntPtr w,int x,int y,int width,int height,bool repaint);
    [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint count, INPUT[] inputs, int size);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] struct MONITORINFO { public uint Size;public RECT Monitor,Work;public uint Flags; }
    [StructLayout(LayoutKind.Sequential)] struct GUIINFO { public uint Size,Flags;public IntPtr Active,Focus,Capture,MenuOwner,MoveSize,Caret;public RECT CaretRect; }
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
    public static FileNameEvidence FileName(Process app,long main,Process target,long w,string title,long expectedFocus) {
        Require(app,main,target,w,title,true);
        if(Class(w)!="#32770")throw new InvalidOperationException("Expected actual native file dialog");
        uint owner;uint thread=GetWindowThreadProcessId((IntPtr)w,out owner);
        var info=new GUIINFO { Size=checked((uint)Marshal.SizeOf<GUIINFO>()) };
        if(thread==0 || owner!=target.Id || !GetGUIThreadInfo(thread,ref info))throw new InvalidOperationException("Native filename focus unavailable");
        long focus=info.Focus.ToInt64();uint focusOwner;
        var evidence=new FileNameEvidence {Window=w,Focus=focus,ExpectedFocus=expectedFocus,Active=info.Active.ToInt64(),DialogPid=target.Id,FocusPid=Pid(focus),
            Exists=IsWindow(info.Focus),Visible=IsWindowVisible(info.Focus),Enabled=IsWindowEnabled(info.Focus),Descendant=IsChild((IntPtr)w,info.Focus),
            Class=Class(focus),DialogThread=thread,FocusThread=GetWindowThreadProcessId(info.Focus,out focusOwner),
            Ancestors=Array.Empty<FileNameAncestorEvidence>(),FailedPredicates=Array.Empty<string>()};
        try {
            evidence.ObservationStage="ancestor-chain";
            var ancestors=new List<FileNameAncestorEvidence>();var seen=new HashSet<long>();IntPtr child=info.Focus;
            for(;child!=IntPtr.Zero && child!=(IntPtr)w && seen.Count<16 && seen.Add(child.ToInt64());child=GetParent(child)) {
                var ancestor=new FileNameAncestorEvidence {Window=child.ToInt64(),Parent=GetParent(child).ToInt64(),ProcessId=Pid(child.ToInt64()),
                    ControlId=GetDlgCtrlID(child),Class=Class(child.ToInt64()),Descendant=IsChild((IntPtr)w,child)};
                ancestors.Add(ancestor);evidence.Ancestors=ancestors.ToArray();
                if(!ancestor.Descendant || ancestor.ProcessId!=target.Id)throw new InvalidOperationException("Filename ancestor left owned dialog");
                // Preserve the established classic filename ID; modern Save is checked after the complete chain.
                if(ancestor.ControlId==1148)evidence.HasFileNameId=true;
            }
            evidence.AncestryReachedDialog=child==(IntPtr)w;
            evidence.AncestryTruncated=child!=IntPtr.Zero && child!=(IntPtr)w && seen.Count>=16;
            evidence.ObservationStage="style";
            evidence.Style=GetWindowLongPtr(info.Focus,-16).ToInt64();
            evidence.ReadOnly=FileNameReadOnly(evidence.Style);
            evidence.HasFileNameId=evidence.HasFileNameId || IsObservedModernSaveFileName(evidence,title) ||
                IsObservedExportFolderName(evidence,title);
            evidence.ObservationStage="filename-validation";
            ValidateFileName(evidence);Require(app,main,target,w,title,true);
            // Re-read focus after ownership/style/ancestry queries. Diagnostics
            // retain this second observation even when it refuses the send.
            evidence.ObservationStage="final-focus-check";
            evidence.FinalFocusObserved=GetGUIThreadInfo(thread,ref info);
            evidence.FinalFocus=info.Focus.ToInt64();evidence.FinalActive=info.Active.ToInt64();
            if(!evidence.FinalFocusObserved || evidence.FinalFocus!=focus || evidence.FinalActive!=w)
                throw new InvalidOperationException("Native filename focus changed during observation");
            evidence.ObservationStage="verified";
        } catch(Exception error) {
            error.Data["PixelQuay.FileNameEvidence"]=evidence;
            throw;
        }
        return evidence;
    }
    public static string FileNameText(Process app,long main,Process target,long w,string title,long focus) {
        FileName(app,main,target,w,title,focus);
        var text=new StringBuilder(4097);UIntPtr result;
        if(SendMessageTimeoutW((IntPtr)focus,0x000D,(UIntPtr)text.Capacity,text,0x22,2000,out result)==IntPtr.Zero || result.ToUInt64()>=4096)
            throw new InvalidOperationException("Bounded native filename readback failed");
        FileName(app,main,target,w,title,focus);return text.ToString();
    }
    static string BoundedControlText(long window,int limit) {
        var text=new StringBuilder(limit+1);UIntPtr result;
        if(SendMessageTimeoutW((IntPtr)window,0x000D,(UIntPtr)text.Capacity,text,0x22,2000,out result)==IntPtr.Zero || result.ToUInt64()>=(ulong)limit)
            throw new InvalidOperationException("Bounded native control text unavailable");
        return text.ToString();
    }
    public static ChooseButtonEvidence ExportChoose(Process app,long main,Process target,long w,string title,long filename,string path,ChooseButtonEvidence retained,bool focused) {
        if(title!="Export destination" || filename==0 || string.IsNullOrEmpty(path) || path.Length>4096 || (focused && retained==null))
            throw new ArgumentException("Retained export folder field and exact Choose route required");
        Require(app,main,target,w,title,true);
        var e=new ChooseButtonEvidence {Window=w,Filename=filename,DialogPid=target.Id,ObservationStage="folder-field",Candidates=Array.Empty<NativeButtonEvidence>()};
        try {
            uint owner; e.DialogThread=GetWindowThreadProcessId((IntPtr)w,out owner);
            if(Class(w)!="#32770" || e.DialogThread==0 || owner!=target.Id)throw new InvalidOperationException("Owned native folder dialog changed");
            if(!focused) {
                var field=FileName(app,main,target,w,title,filename);
                if(!IsObservedExportFolderName(field,title))throw new InvalidOperationException("Choose requires the observed direct folder Edit1152");
            }
            uint fieldOwner;uint fieldThread=GetWindowThreadProcessId((IntPtr)filename,out fieldOwner);
            if(!IsWindow((IntPtr)filename) || !IsWindowVisible((IntPtr)filename) || !IsWindowEnabled((IntPtr)filename) ||
                !IsChild((IntPtr)w,(IntPtr)filename) || GetParent((IntPtr)filename)!=(IntPtr)w || Class(filename)!="Edit" ||
                GetDlgCtrlID((IntPtr)filename)!=1152 || fieldOwner!=target.Id || fieldThread!=e.DialogThread ||
                FileNameReadOnly(GetWindowLongPtr((IntPtr)filename,-16).ToInt64()) || BoundedControlText(filename,4097)!=path)
                throw new InvalidOperationException("Retained owned folder field/path changed before Choose");
            e.ObservationStage="native-buttons";
            var candidates=new List<NativeButtonEvidence>();int observed=0;Exception queryError=null;
            EnumCallback cb=(child,data)=> {
                if(++observed>512)return false;
                try {
                    if(GetParent(child)!=(IntPtr)w || Pid(child.ToInt64())!=target.Id || Class(child.ToInt64())!="Button")return true;
                    if(candidates.Count>=16)throw new InvalidOperationException("Native dialog button inventory exceeded bound");
                    uint childOwner;uint thread=GetWindowThreadProcessId(child,out childOwner);
                    candidates.Add(new NativeButtonEvidence {Window=child.ToInt64(),Parent=GetParent(child).ToInt64(),ProcessId=(int)childOwner,
                        ControlId=GetDlgCtrlID(child),Class=Class(child.ToInt64()),Label=BoundedControlText(child.ToInt64(),128),Thread=thread,
                        Exists=IsWindow(child),Visible=IsWindowVisible(child),Enabled=IsWindowEnabled(child),Descendant=IsChild((IntPtr)w,child),Style=GetWindowLongPtr(child,-16).ToInt64()});
                    return true;
                }catch(Exception error){queryError=error;return false;}
            };
            EnumChildWindows((IntPtr)w,cb,IntPtr.Zero);GC.KeepAlive(cb);e.Candidates=candidates.ToArray();
            if(queryError!=null)throw queryError;
            if(observed>512)throw new InvalidOperationException("Native dialog child inventory exceeded bound");
            foreach(var button in candidates)if(button.Label=="Choose") {
                ++e.CandidateCount;e.Button=button.Window;e.Parent=button.Parent;e.ButtonPid=button.ProcessId;e.ControlId=button.ControlId;
                e.Class=button.Class;e.Label=button.Label;e.ButtonThread=button.Thread;e.Exists=button.Exists;e.Visible=button.Visible;
                e.Enabled=button.Enabled;e.Descendant=button.Descendant;e.Style=button.Style;
            }
            e.DialogItem=GetDlgItem((IntPtr)w,e.ControlId).ToInt64();e.NextTab=GetNextDlgTabItem((IntPtr)w,(IntPtr)filename,false).ToInt64();
            var info=new GUIINFO {Size=checked((uint)Marshal.SizeOf<GUIINFO>())};
            if(!GetGUIThreadInfo(e.DialogThread,ref info))throw new InvalidOperationException("Native Choose focus unavailable");
            e.Focus=info.Focus.ToInt64();e.Active=info.Active.ToInt64();e.ObservationStage="button-validation";
            ValidateChooseButton(e,title,focused,retained);Require(app,main,target,w,title,true);
            e.ObservationStage="final-focus-check";e.FinalFocusObserved=GetGUIThreadInfo(e.DialogThread,ref info);
            e.FinalFocus=info.Focus.ToInt64();e.FinalActive=info.Active.ToInt64();
            if(!e.FinalFocusObserved || e.FinalFocus!=e.Focus || e.FinalActive!=w)throw new InvalidOperationException("Native Choose focus changed during observation");
            e.ObservationStage="verified";return e;
        }catch(Exception error){error.Data["PixelQuay.ChooseButtonEvidence"]=e;throw;}
    }
    public static void ExportChooseSpace(Process app,long main,Process target,long w,string title,long filename,string path,ChooseButtonEvidence retained) {
        if(retained==null || retained.Button==0)throw new ArgumentException("Retained Choose button required");
        var inputs=ChordInputs(new[]{32});
        DeliverInput(()=>Require(app,main,target,w,title,true),()=>ExportChoose(app,main,target,w,title,filename,path,retained,true),
            ()=>SendInput((uint)inputs.Length,inputs,Marshal.SizeOf<INPUT>()),(uint)inputs.Length);
        Thread.Sleep(100);
    }
    static bool Rectangle(int[] r) { return r!=null && r.Length==4 && r[2]>0 && r[3]>0; }
    static bool Inside(int[] inner,int[] outer) {
        return Rectangle(inner) && Rectangle(outer) && inner[0]>=outer[0] && inner[1]>=outer[1] &&
            (long)inner[0]+inner[2]<=(long)outer[0]+outer[2] && (long)inner[1]+inner[3]<=(long)outer[1]+outer[3];
    }
    public static int[] VisibleBounds(ConsumerGeometry g) {
        // CopyFromScreen uses unscaled coordinates. The observed Windows
        // runner is 96 DPI; other coordinate contexts need separate proof.
        if(g==null || g.Dpi!=96 || !Inside(g.Window,g.Desktop) || (long)g.Window[2]*g.Window[3]>16000000)
            throw new InvalidOperationException("Owned window is not fully visible within bounded desktop: window="+
                (g==null || g.Window==null?"unavailable":string.Join(",",g.Window))+" desktop="+
                (g==null || g.Desktop==null?"unavailable":string.Join(",",g.Desktop))+" dpi="+(g==null?0:g.Dpi));
        return new int[]{g.Window[0],g.Window[1],g.Window[2],g.Window[3],g.Desktop[0],g.Desktop[1],g.Desktop[2],g.Desktop[3]};
    }
    public static int[] PlacementPlan(ConsumerGeometry g) {
        if(g==null || g.Dpi!=96 || !Inside(g.WorkArea,g.Desktop) || g.WorkArea[2]<1472 || g.WorkArea[3]<940)
            throw new InvalidOperationException("Actual monitor work area cannot fit the readable native window");
        return new int[]{checked(g.WorkArea[0]+(g.WorkArea[2]-1472)/2),checked(g.WorkArea[1]+(g.WorkArea[3]-940)/2),1472,940};
    }
    public static int[] PlacedBounds(ConsumerGeometry g) {
        var bounds=VisibleBounds(g);
        if(!Inside(g.Window,g.WorkArea) || g.Window[2]<1400 || g.Window[3]<850)
            throw new InvalidOperationException("Actual placed window is too small or outside its monitor work area");
        return bounds;
    }
    public static ConsumerGeometry Geometry(Process app,long main,Process target,long w,string title) {
        Require(app,main,target,w,title,true);RECT r;
        if(!GetWindowRect((IntPtr)w,out r))throw new InvalidOperationException("Window bounds unavailable");
        var info=new MONITORINFO { Size=checked((uint)Marshal.SizeOf<MONITORINFO>()) };
        if(!GetMonitorInfoW(MonitorFromWindow((IntPtr)w,2),ref info))throw new InvalidOperationException("Actual monitor work area unavailable");
        var result=new ConsumerGeometry {
            Window=new int[]{r.Left,r.Top,checked(r.Right-r.Left),checked(r.Bottom-r.Top)},
            Desktop=new int[]{GetSystemMetrics(76),GetSystemMetrics(77),GetSystemMetrics(78),GetSystemMetrics(79)},
            WorkArea=new int[]{info.Work.Left,info.Work.Top,checked(info.Work.Right-info.Work.Left),checked(info.Work.Bottom-info.Work.Top)},Dpi=GetDpiForWindow((IntPtr)w)
        };
        Require(app,main,target,w,title,true);return result;
    }
    public static int[] Bounds(Process app,long main,Process target,long w,string title) {
        return VisibleBounds(Geometry(app,main,target,w,title));
    }
    public static void DeliverPlacement(Action requireRoot,Func<bool> place) {
        requireRoot();
        if(!place())throw new InvalidOperationException("Native owned window placement failed");
    }
    public static void ValidatePlacementTarget(long main,long w,bool sameRetainedProcess,string windowClass) {
        if(main==0 || w!=main || !sameRetainedProcess || windowClass!="gdkSurfaceToplevel")
            throw new InvalidOperationException("Only the exact retained GTK root window may be placed");
    }
    public static void Place(Process app,long main,Process target,long w,string title) {
        Action requireRoot=()=> {
            Require(app,main,target,w,title,true);
            ValidatePlacementTarget(main,w,app==target,Class(w));
        };
        requireRoot();
        var plan=PlacementPlan(Geometry(app,main,target,w,title));
        DeliverPlacement(requireRoot,()=>MoveWindow((IntPtr)w,plan[0],plan[1],plan[2],plan[3],true));
    }
    static INPUT Key(ushort vk,ushort scan,uint flags) { return new INPUT { Type=1, Value=new UNION { Key=new KEY { Vk=vk,Scan=scan,Flags=flags } } }; }
    public static void DeliverInput(Action requireTarget,Action requireFocus,Func<uint> deliver,uint count) {
        requireTarget();
        if(requireFocus!=null)requireFocus();
        if(deliver()!=count)throw new InvalidOperationException("Partial native input delivery");
    }
    static void Send(Process app,long main,Process target,long w,string title,INPUT[] inputs,long expectedFocus=0) {
        Action requireFocus=expectedFocus==0 ? (Action)null : () => FileName(app,main,target,w,title,expectedFocus);
        DeliverInput(() => Require(app,main,target,w,title,true),requireFocus,
            () => SendInput((uint)inputs.Length,inputs,Marshal.SizeOf<INPUT>()),(uint)inputs.Length);
        Thread.Sleep(100);
    }
    static INPUT[] ChordInputs(int[] keys) {
        if(keys.Length<1 || keys.Length>3)throw new ArgumentException("Unbounded chord");
        var inputs=new INPUT[keys.Length*2];
        for(int i=0;i<keys.Length;i++) { if(keys[i]<1 || keys[i]>255)throw new ArgumentException("Invalid key"); inputs[i]=Key((ushort)keys[i],0,0); inputs[inputs.Length-1-i]=Key((ushort)keys[i],0,2); }
        return inputs;
    }
    static INPUT[] TextInputs(string text) {
        if(text.Length==0 || text.Length>4096 || text.IndexOf('\0')>=0)throw new ArgumentException("Unbounded text");
        var inputs=new INPUT[text.Length*2];
        for(int i=0;i<text.Length;i++) { inputs[2*i]=Key(0,text[i],4); inputs[2*i+1]=Key(0,text[i],6); }
        return inputs;
    }
    public static void Chord(Process app,long main,Process target,long w,string title,int[] keys) {
        Send(app,main,target,w,title,ChordInputs(keys));
    }
    public static void Text(Process app,long main,Process target,long w,string title,string text) {
        Send(app,main,target,w,title,TextInputs(text));
    }
    public static void FileNameChord(Process app,long main,Process target,long w,string title,long expectedFocus,int[] keys) {
        if(expectedFocus==0)throw new ArgumentException("Retained filename focus required");
        Send(app,main,target,w,title,ChordInputs(keys),expectedFocus);
    }
    public static void FileNameTextInput(Process app,long main,Process target,long w,string title,long expectedFocus,string text) {
        if(expectedFocus==0)throw new ArgumentException("Retained filename focus required");
        Send(app,main,target,w,title,TextInputs(text),expectedFocus);
    }
}
}
