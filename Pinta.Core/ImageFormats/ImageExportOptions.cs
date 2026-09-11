// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
namespace Pinta.Core;

public sealed record ImageExportOptions (int? JpegQuality);

/// <summary>Explicit recipe options. The implementation must not prompt or change saved defaults.</summary>
public interface IImageExporterWithOptions : IImageExporter
{
	bool SupportsJpegQuality { get; }
	void Export (Document document, Gio.File file, Gtk.Window parent, ImageExportOptions options);
}
