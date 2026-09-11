// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
// Content drawing extracted from TextTool's Paint.NET/Pinta-derived drawing path.
// Copyright (C) dotPDN LLC, Rick Brewster, Tom Jackson, and contributors.
// Portions Copyright (C) Microsoft Corporation. All Rights Reserved.
// Ported to Pinta by Olivier Dufour and Jonathan Pobst.
// See license-pdn.txt for full licensing and attribution details.
using Cairo;

namespace Pinta.Core;

/// <summary>Content style and the selection captured when text editing began.</summary>
public sealed record TextRenderOptions (
	bool Antialias = true, bool Fill = true, bool Stroke = false,
	bool BackgroundFill = false, int OutlineWidth = 1, double Resolution = -1,
	DocumentSelection? Clip = null, bool HasEditingDecorations = false)
{
	public TextRenderOptions Copy () => this with { Clip = Clip?.Clone () };
}

public static class TextContentRenderer
{
	/// <summary>Draw glyph content only; caret, selected-text highlight and edit frame are UI overlays.</summary>
	public static void Draw (Context context, TextLayout layout, TextRenderOptions options)
	{
		TextEngine engine = layout.Engine;
		if (engine.IsEmpty ()) return;
		context.Save ();
		try {
			context.Antialias = options.Antialias ? Antialias.Gray : Antialias.None;
			options.Clip?.Clip (context);
			if (options.BackgroundFill)
				context.FillRectangle (layout.GetLayoutBounds ().ToDouble (), engine.SecondaryColor);
			context.MoveTo (engine.Origin.X, engine.Origin.Y);
			context.SetSourceColor (engine.PrimaryColor);
			if (options.Stroke) {
				context.SetSourceColor (options.Fill ? engine.SecondaryColor : engine.PrimaryColor);
				context.LineWidth = options.OutlineWidth;
				PangoCairo.Functions.LayoutPath (context, layout.Layout);
				context.Stroke ();
				if (options.Fill) {
					context.MoveTo (engine.Origin.X, engine.Origin.Y);
					context.SetSourceColor (engine.PrimaryColor);
				}
			}
			if (options.Fill) PangoCairo.Functions.ShowLayout (context, layout.Layout);
		} finally { context.Restore (); }
	}

	/// <summary>Render a cloned text model with an independent Pango/Cairo context, without GTK.</summary>
	public static ImageSurface CreateSurface (TextEngine source, Size size)
	{
		var engine = source.Clone ();
		var surface = CairoExtensions.CreateImageSurface (Format.Argb32, size.Width, size.Height);
		try {
			using var context = new Context (surface);
			using var layout = new TextLayout (PangoCairo.Functions.CreateLayout (context));
			var pangoContext = layout.Layout.GetContext ();
			PangoCairo.Functions.ContextSetResolution (pangoContext, engine.RenderOptions.Resolution);
			var fontOptions = new FontOptions { Antialias = engine.RenderOptions.Antialias ? Antialias.Gray : Antialias.None };
			PangoCairo.Functions.ContextSetFontOptions (pangoContext, fontOptions);
			layout.Engine = engine;
			Draw (context, layout, engine.RenderOptions);
			return surface;
		} catch { surface.Dispose (); throw; }
	}
}
