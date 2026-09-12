// Copyright 2026 Trieflow LLC. MIT. Native filename UI control; capture only.
using System;
using System.Runtime.InteropServices;
namespace TintFableMarketing {
 public static class Filename {
  [DllImport("user32.dll",EntryPoint="SendMessageTimeoutW",CharSet=CharSet.Unicode,SetLastError=true)]
  private static extern IntPtr SendMessageTimeout(IntPtr window,uint message,UIntPtr wParam,string text,uint flags,uint timeout,out UIntPtr result);
  public static void Validate(long window,string text) {
   if(window<=0 || window==0xffff || String.IsNullOrEmpty(text) || text.Length>4096 || text.IndexOf('\0')>=0)
    throw new ArgumentException("Invalid bounded native filename target/text");
  }
  public static void Set(long window,string text) {
   Validate(window,text);
   // The caller freshly proves this exact focused Edit's process, dialog,
   // filename ID ancestry and writable state, and rechecks them after sending.
   // SMTO_BLOCK|SMTO_ABORTIFHUNG|SMTO_ERRORONEXIT; never HWND_BROADCAST.
   UIntPtr result;
   if(SendMessageTimeout((IntPtr)window,0x000c,UIntPtr.Zero,text,0x23,1000,out result)==IntPtr.Zero || result.ToUInt64()!=1)
    throw new InvalidOperationException("Native filename WM_SETTEXT failed or timed out; not replayed");
  }
 }
}
