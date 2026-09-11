// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.IO;

namespace Pinta.Core;

public interface IExportRecipeSource
{
	Size ImageSize { get; }
	string? FilePath { get; }
}

public sealed class DocumentRecipeSource (Document document) : IExportRecipeSource
{
	public Document Document { get; } = document;
	public Size ImageSize => Document.ImageSize;
	public string? FilePath => Document.File?.GetPath ();
}

public sealed class ExportRecipePlan
{
	internal ExportRecipePlan (IExportRecipeSource source, ValidatedExportRecipe recipe, string outputPath)
	{
		Source = source;
		Recipe = recipe;
		OutputPath = outputPath;
	}
	public IExportRecipeSource Source { get; }
	public ValidatedExportRecipe Recipe { get; }
	public string OutputPath { get; }

	public static string ResolveOutputPath (string sourcePath, string suffix, string extension)
	{
		ExportRecipeValidator.ValidateStructure (new ("preview", "Preview", 1, 1, extension, null, suffix, false));
		// Preserve both Windows and POSIX spelling in previews, including Unicode.
		int separator = Math.Max (sourcePath.LastIndexOf ('/'), sourcePath.LastIndexOf ('\\'));
		int dot = sourcePath.LastIndexOf ('.');
		string stem = dot > separator + 1 ? sourcePath[..dot] : sourcePath;
		return stem + suffix + "." + ExportRecipeValidator.NormalizeExtension (extension);
	}

	internal static string ResolveLinks (string path)
	{
		string full = Path.GetFullPath (path);
		string current = Path.GetPathRoot (full)!;
		foreach (string part in full[current.Length..].Split (Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries)) {
			current = Path.Combine (current, part);
			FileSystemInfo info = Directory.Exists (current) ? new DirectoryInfo (current) : new FileInfo (current);
			if (info.LinkTarget is not null) current = info.ResolveLinkTarget (true)?.FullName ?? current;
		}
		return current;
	}
}
