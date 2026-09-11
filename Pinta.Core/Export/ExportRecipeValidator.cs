// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.Collections.Generic;
using System.Linq;

namespace Pinta.Core;

public static class ExportRecipeValidator
{
	public const long MaximumPixels = 100_000_000;
	public const long MaximumWorkingBytes = 400_000_000;
	// Cairo image surfaces have a per-axis limit in addition to their total byte limit.
	public const int MaximumDimension = 32767;

	public static long ValidateDimensions (Size size)
	{
		long pixels = checked ((long) size.Width * size.Height);
		if (size.Width < 1 || size.Height < 1 || size.Width > MaximumDimension || size.Height > MaximumDimension || pixels > MaximumPixels)
			throw new ArgumentOutOfRangeException (nameof (size), "Use positive dimensions up to 32,767 per side and 100 million pixels.");
		return checked (pixels * 4);
	}

	public static void ValidateWorkingSet (Size source, Size output)
	{
		long sourceBytes = ValidateDimensions (source);
		long outputBytes = ValidateDimensions (output);
		// Flattened input, independent input copy, resized output, export flatten/pixbuf,
		// and encoder scratch allowance. This is an estimate, not an OS memory guarantee.
		if (checked (2 * sourceBytes + 4 * outputBytes) > MaximumWorkingBytes)
			throw new ArgumentOutOfRangeException (nameof (output), "This export exceeds the 400 MB estimated working-image budget. Choose a smaller output or source image.");
	}

	public static ValidatedExportRecipe Validate (ExportRecipe recipe, IEnumerable<FormatDescriptor> formats)
	{
		ValidateStructure (recipe);
		string extension = NormalizeExtension (recipe.Extension);
		FormatDescriptor format = formats.FirstOrDefault (f => f.IsExportAvailable () &&
			f.Extensions.Any (e => string.Equals (e, extension, StringComparison.OrdinalIgnoreCase)))
			?? throw new ArgumentException ($"No available exporter supports .{extension}.");
		bool quality = SupportsQuality (format);
		if (quality && recipe.Quality is not (>= 1 and <= 100))
			throw new ArgumentException ("JPEG quality must be explicitly set from 1 to 100.");
		if (!quality && recipe.Quality is not null)
			throw new ArgumentException ("Quality is only supported by the JPEG exporter.");
		return new (recipe with { Extension = extension }, format);
	}

	public static bool SupportsQuality (FormatDescriptor format) =>
		format.Exporter is IImageExporterWithOptions { SupportsJpegQuality: true } &&
		format.Extensions.Any (e => e.Equals ("jpg", StringComparison.OrdinalIgnoreCase) || e.Equals ("jpeg", StringComparison.OrdinalIgnoreCase));

	internal static void ValidateStructure (ExportRecipe recipe)
	{
		ArgumentNullException.ThrowIfNull (recipe);
		if (string.IsNullOrWhiteSpace (recipe.Id) || string.IsNullOrWhiteSpace (recipe.Name))
			throw new ArgumentException ("Every recipe needs an ID and name.");
		if (recipe.Id.Length > 128 || recipe.Name.Length > 120)
			throw new ArgumentException ("Recipe ID or name is too long.");
		ValidateDimensions (new Size (recipe.Width, recipe.Height));
		_ = NormalizeExtension (recipe.Extension);
		if (recipe.Suffix is null || recipe.Suffix.Length > 100 || recipe.Suffix.Any (c => c < 32 || "<>:\"/\\|?*".Contains (c)))
			throw new ArgumentException ("Suffix must contain filename characters only, without paths or control characters.");
		if (recipe.Quality is not null && recipe.Quality is not (>= 1 and <= 100))
			throw new ArgumentException ("Quality must be from 1 to 100.");
	}

	internal static string NormalizeExtension (string extension)
	{
		ArgumentNullException.ThrowIfNull (extension);
		string result = extension.Trim ().TrimStart ('.').ToLowerInvariant ();
		if (result.Length is < 1 or > 16 || result.Any (c => !char.IsAsciiLetterOrDigit (c)))
			throw new ArgumentException ("Choose a valid image extension.");
		return result;
	}
}
