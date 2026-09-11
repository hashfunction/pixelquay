// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.Threading;
using System.Collections.Generic;
using Cairo;

namespace Pinta.Core;

public sealed class DocumentRecipeRenderer : IExportRecipeRenderer
{
	public static Document CreateFlattenedExportCopy (Document source, Size outputSize, ResamplingMode mode)
	{
		ExportRecipeValidator.ValidateWorkingSet (source.ImageSize, outputSize);
		using ImageSurface flattened = FlattenContent (source);
		var copy = Document.CreateExportDocument (source.ImageSize);
		try {
			var layer = copy.Layers.AddNewLayer ("Export");
			using (var context = new Context (layer.Surface)) {
				context.SetSourceSurface (flattened, 0, 0);
				context.Paint ();
			}
			copy.ResizeImage (outputSize, mode);
			return copy;
		} catch {
			copy.DisposeExportDocument ();
			throw;
		}
	}

	private static ImageSurface FlattenContent (Document source)
	{
		// Clean stopped text surfaces may already have been resized/transformed. Keep
		// them; regenerate only uncommitted text or caches carrying editing overlays.
		Dictionary<Layer, TextEngine> pending = [];
		foreach (var userLayer in source.Layers.UserLayers) {
			if (userLayer.TextLayer.IsLayerSetup &&
				(userLayer.TextEngine.State == TextMode.Uncommitted || userLayer.TextEngine.RenderOptions.HasEditingDecorations))
				pending.Add (userLayer.TextLayer.Layer, userLayer.TextEngine);
		}
		var flattened = CairoExtensions.CreateImageSurface (Format.Argb32, source.ImageSize.Width, source.ImageSize.Height);
		try {
			using var context = new Context (flattened);
			foreach (var layer in source.Layers.GetLayersToPaint (includeToolLayer: false)) {
				if (pending.TryGetValue (layer, out var engine)) {
					using var content = TextContentRenderer.CreateSurface (engine, layer.Surface.GetSize ());
					layer.Draw (context, content, layer.Opacity);
				} else layer.Draw (context);
			}
			flattened.MarkDirty ();
			return flattened;
		} catch { flattened.Dispose (); throw; }
	}

	public void Render (ExportRecipePlan plan, string stagingPath, Gtk.Window parent, CancellationToken cancellationToken)
	{
		if (plan.Source is not DocumentRecipeSource source)
			throw new ArgumentException ("The document renderer requires a document source.");
		cancellationToken.ThrowIfCancellationRequested ();
		Document copy = CreateFlattenedExportCopy (source.Document, plan.Recipe.Size, ResamplingMode.Bilinear);
		try {
			cancellationToken.ThrowIfCancellationRequested ();
			var file = Gio.FileHelper.NewForPath (stagingPath);
			var exporter = plan.Recipe.Format.Exporter ?? throw new InvalidOperationException ("Exporter is unavailable.");
			if (plan.Recipe.Options.JpegQuality is not null) {
				if (exporter is not IImageExporterWithOptions { SupportsJpegQuality: true } optionsExporter)
					throw new ArgumentException ("This exporter does not support JPEG quality.");
				optionsExporter.Export (copy, file, parent, plan.Recipe.Options);
			} else exporter.Export (copy, file, parent);
		} finally { copy.DisposeExportDocument (); }
	}
}
