// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace Pinta.Core;

public enum ExportRecipeStatus { Succeeded }
public sealed record ExportRecipeResult (ExportRecipeStatus Status, string OutputPath, Size Size, string Extension, long ByteLength);

public interface IExportRecipeRenderer
{
	void Render (ExportRecipePlan plan, string stagingPath, Gtk.Window parent, CancellationToken cancellationToken);
}

public sealed class ExportRecipeExecutor
{
	private readonly IExportRecipeRenderer renderer;
	private readonly IOutputPublisher publisher;
	public ExportRecipeExecutor () : this (new DocumentRecipeRenderer (), new AtomicOutputPublisher ()) { }
	public ExportRecipeExecutor (IExportRecipeRenderer renderer, IOutputPublisher publisher)
	{
		this.renderer = renderer;
		this.publisher = publisher;
	}

	public ExportRecipePlan CreatePlan (IExportRecipeSource source, ValidatedExportRecipe recipe, string destination)
	{
		ArgumentNullException.ThrowIfNull (source);
		ArgumentNullException.ThrowIfNull (recipe);
		ArgumentException.ThrowIfNullOrWhiteSpace (destination);
		ExportRecipeValidator.ValidateWorkingSet (source.ImageSize, recipe.Size);
		string output = Path.GetFullPath (destination);
		if (!Path.GetExtension (output).Equals ("." + recipe.Recipe.Extension, StringComparison.OrdinalIgnoreCase))
			throw new ArgumentException ($"Destination must end in .{recipe.Recipe.Extension}.");
		if (source.FilePath is string input && string.Equals (ExportRecipePlan.ResolveLinks (input), ExportRecipePlan.ResolveLinks (output),
			OperatingSystem.IsWindows () || OperatingSystem.IsMacOS () ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal))
			throw new ArgumentException ("Choose a destination different from the open document's original file.");
		return new (source, recipe, output);
	}

	/// <summary>The caller must keep the source document unavailable for editing until completion.</summary>
	public Task<ExportRecipeResult> ExecuteAsync (ExportRecipePlan plan, Gtk.Window parent, CancellationToken cancellationToken) => Task.Run (() => {
		cancellationToken.ThrowIfCancellationRequested ();
		// Revalidate source size/path in case the document changed after preview.
		_ = CreatePlan (plan.Source, plan.Recipe, plan.OutputPath);
		string directory = Path.GetDirectoryName (plan.OutputPath)!;
		string staged = Path.Combine (directory, $".pixelquay-{Guid.NewGuid ():N}.{plan.Recipe.Recipe.Extension}");
		bool ownsStage = false;
		try {
			using (new FileStream (staged, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { }
			ownsStage = true;
			renderer.Render (plan, staged, parent, cancellationToken);
			cancellationToken.ThrowIfCancellationRequested ();
			long bytes = new FileInfo (staged).Length;
			if (bytes == 0) throw new IOException ("The exporter produced an empty image.");
			// Cancellation is honored up to this commit point. Once the atomic move succeeds,
			// report success even if a concurrent cancellation arrives afterward.
			publisher.Publish (staged, plan.OutputPath, plan.Recipe.Recipe.Overwrite);
			return new ExportRecipeResult (ExportRecipeStatus.Succeeded, plan.OutputPath, plan.Recipe.Size, plan.Recipe.Recipe.Extension, bytes);
		} finally {
			if (ownsStage) File.Delete (staged);
		}
	}, cancellationToken);
}
