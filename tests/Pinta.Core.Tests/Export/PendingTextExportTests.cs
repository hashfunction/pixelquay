using System;
using System.Linq;
using System.Runtime.InteropServices;
using Cairo;
using NUnit.Framework;

namespace Pinta.Core.Tests;

public sealed class PendingTextExportTests
{
	[OneTimeSetUp]
	public void InitializeNativeLibraries ()
	{
		Gio.Module.Initialize ();
		GdkPixbuf.Module.Initialize ();
		Cairo.Module.Initialize ();
		Gdk.Module.Initialize ();
		Gtk.Module.Initialize ();
		Pango.Module.Initialize ();
		PangoCairo.Module.Initialize ();
	}

	[TestCase (0, TextMode.Uncommitted)]
	[TestCase (1, TextMode.Uncommitted)]
	[TestCase (2, TextMode.Uncommitted)]
	[TestCase (0, TextMode.NotFinalized)]
	[TestCase (1, TextMode.NotFinalized)]
	[TestCase (2, TextMode.NotFinalized)]
	public void ExportRendersPendingGlyphsButNeverCaretSelectionOrEditFrame (int decoration, TextMode state)
	{
		var source = Document.CreateExportDocument (new Size (128, 80));
		try {
			var layer = source.Layers.AddNewLayer ("Pending text");
			using (var g = new Context (layer.Surface)) { g.SetSourceRgb (1, 1, 1); g.Paint (); }
			var engine = layer.TextEngine;
			engine.SetFont (Pango.FontDescription.FromString ("Sans 20"), TextAlignment.Left, false);
			engine.Origin = new PointI (40, 30);
			engine.InsertText ("A");
			engine.State = state;
			engine.RenderOptions = new (HasEditingDecorations: true);
			engine.SetCursorPosition (new TextPosition (0, 0), true);
			engine.SetCursorPosition (new TextPosition (0, 1), false);
			var text = layer.TextLayer.Layer.Surface;
			using (var g = new Context (text)) {
				// The live tool's cache combines glyph content and these transient overlays.
				g.SetSourceRgb (0, 0, 0);
				g.Rectangle (48, 38, 6, 12); g.Fill ();
				g.SetSourceRgba (1, 0, 0, 0.5);
				if (decoration == 0) { g.Rectangle (4, 2, 1, 12); g.Fill (); }
				if (decoration == 1) { g.Rectangle (4, 2, 15, 12); g.Fill (); }
				if (decoration == 2) { g.Rectangle (4.5, 2.5, 20, 12); g.LineWidth = 1; g.Stroke (); }
			}
			source.IsDirty = true;
			source.Selection.CreateRectangleSelection (new RectangleD (1, 1, 100, 70));
			string before = Snapshot (source, layer);
			int modifications = 0;
			engine.Modified += (_, _) => ++modifications;
			var copy = DocumentRecipeRenderer.CreateFlattenedExportCopy (source, source.ImageSize, ResamplingMode.Bilinear);
			try {
				var exported = copy.Layers.UserLayers[0].Surface;
				Assert.Multiple (() => {
					Assert.That (exported.GetColorBgra (new PointI (4, 6)), Is.EqualTo (ColorBgra.White), "Editing decoration must not enter output.");
					Assert.That (exported.GetReadOnlyPixelData ().ToArray ().Skip (30 * 128).Any (p => p.R < 200), Is.True, "Pending text must remain visible.");
					Assert.That (Snapshot (source, layer), Is.EqualTo (before));
					Assert.That (modifications, Is.Zero, "Export must not notify or mutate the live text model.");
				});
			} finally { copy.DisposeExportDocument (); }
		} finally { source.DisposeExportDocument (); }
	}

	[Test]
	public void PendingTextKeepsFillStrokeBackgroundAndCapturedClipWithoutMutatingModel ()
	{
		var source = Document.CreateExportDocument (new Size (128, 80));
		try {
			var layer = source.Layers.AddNewLayer ("Styled pending text");
			var engine = layer.TextEngine;
			engine.SetFont (Pango.FontDescription.FromString ("Sans Bold 24"), TextAlignment.Left, true);
			engine.Origin = new PointI (20, 20);
			engine.PrimaryColor = new Color (0, 0, 1);
			engine.SecondaryColor = new Color (0, 1, 0);
			engine.InsertText ("AB");
			var clip = new DocumentSelection ();
			clip.CreateRectangleSelection (new RectangleD (0, 0, 40, 80));
			engine.RenderOptions = new TextRenderOptions (false, true, true, true, 3, 96, clip);
			// Deliberately stale/contaminated edit pixels must not be used as content.
			using (var g = new Context (layer.TextLayer.Layer.Surface)) { g.SetSourceRgb (1, 0, 0); g.Paint (); }
			string before = Snapshot (source, layer);
			var copy = DocumentRecipeRenderer.CreateFlattenedExportCopy (source, source.ImageSize, ResamplingMode.Bilinear);
			try {
				var pixels = copy.Layers.UserLayers[0].Surface.GetReadOnlyPixelData ().ToArray ();
				Assert.Multiple (() => {
					Assert.That (pixels.Any (p => p.B > 200 && p.R < 10 && p.A > 0), Is.True, "Primary text fill must survive.");
					Assert.That (pixels.Any (p => p.G > 200 && p.R < 10 && p.A > 0), Is.True, "Secondary outline/background must survive.");
					Assert.That (pixels.Where ((p, i) => i % 128 >= 40).All (p => p.A == 0), Is.True, "Use captured text clip, not the later live document selection.");
					Assert.That (Snapshot (source, layer), Is.EqualTo (before));
					Assert.That (engine.RenderOptions.Clip!.GetBounds (), Is.EqualTo (clip.GetBounds ()));
				});
			} finally { copy.DisposeExportDocument (); }
		} finally { source.DisposeExportDocument (); }
	}

	[Test]
	public void CleanTransformedTextCacheIsPreservedInsteadOfRerenderingItsOldOrigin ()
	{
		var source = Document.CreateExportDocument (new Size (128, 80));
		try {
			var layer = source.Layers.AddNewLayer ("Transformed clean text");
			layer.TextEngine.Origin = new PointI (10, 10);
			layer.TextEngine.InsertText ("A");
			layer.TextEngine.State = TextMode.NotFinalized;
			// Models retain their old coordinates when existing editing surfaces are resized.
			using (var context = new Context (layer.TextLayer.Layer.Surface)) {
				context.SetSourceRgb (0, 0, 1);
				context.Rectangle (70, 40, 20, 25); context.Fill ();
			}
			using var expected = source.GetFlattenedImage ();
			var copy = DocumentRecipeRenderer.CreateFlattenedExportCopy (source, source.ImageSize, ResamplingMode.Bilinear);
			try {
				Assert.That (copy.Layers.UserLayers[0].Surface.GetReadOnlyPixelData ().ToArray (),
					Is.EqualTo (expected.GetReadOnlyPixelData ().ToArray ()));
			} finally { copy.DisposeExportDocument (); }
		} finally { source.DisposeExportDocument (); }
	}

	private static string Snapshot (Document doc, UserLayer layer) => string.Join ("|",
		doc.ImageSize, doc.IsDirty, doc.HasBeenSavedInSession, doc.File, doc.FileType, doc.History.Pointer,
		doc.History.Items.Count (), doc.Selection.Visible, doc.Selection.GetBounds (), doc.Layers.CurrentUserLayerIndex,
		layer.TextEngine.ToString (), layer.TextEngine.State, layer.TextEngine.CurrentPosition, layer.TextEngine.Origin,
		layer.TextEngine.Font.ToString (), layer.TextEngine.RenderOptions.ToString (), layer.TextEngine.RenderOptions.Clip?.GetBounds (), string.Join (";", layer.TextEngine.SelectionRegions), layer.TextBounds, layer.PreviousTextBounds,
		Convert.ToHexString (MemoryMarshal.AsBytes (layer.Surface.GetReadOnlyPixelData ()).ToArray ()),
		Convert.ToHexString (MemoryMarshal.AsBytes (layer.TextLayer.Layer.Surface.GetReadOnlyPixelData ()).ToArray ()));
}
