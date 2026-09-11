// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
namespace Pinta.Core;

public sealed record ExportRecipe (
	string Id, string Name, int Width, int Height, string Extension,
	int? Quality, string Suffix, bool Overwrite);

public sealed class ValidatedExportRecipe
{
	internal ValidatedExportRecipe (ExportRecipe recipe, FormatDescriptor format)
	{
		Recipe = recipe;
		Format = format;
		Options = new ImageExportOptions (recipe.Quality);
	}
	public ExportRecipe Recipe { get; }
	public FormatDescriptor Format { get; }
	public ImageExportOptions Options { get; }
	public Size Size => new (Recipe.Width, Recipe.Height);
}
