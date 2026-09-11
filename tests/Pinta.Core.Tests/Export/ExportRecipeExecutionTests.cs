using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Cairo;
using NUnit.Framework;
using Path = System.IO.Path;

namespace Pinta.Core.Tests;

[TestFixture]
public sealed class ExportRecipeExecutionTests
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
	}

	private static FormatDescriptor Format (string extension, IImageExporter? exporter = null) => new (
		extension, [extension], [], null, exporter ?? new GdkPixbufFormat (extension));
	private static ValidatedExportRecipe Recipe (int width = 32, int height = 18, bool overwrite = false) =>
		ExportRecipeValidator.Validate (new ("web", "Web", width, height, "png", null, "-web", overwrite), [Format ("png")]);

	[Test]
	public void RuntimeExporterAndJpegCapabilityAreAuthoritative ()
	{
		var recipe = new ExportRecipe ("x", "X", 10, 10, " .PNG ", null, "", false);
		Assert.That (ExportRecipeValidator.Validate (recipe, [Format ("png")]).Recipe.Extension, Is.EqualTo ("png"));
		Assert.Throws<ArgumentException> (() => ExportRecipeValidator.Validate (recipe with { Extension = "raw" }, [Format ("png")]));
		Assert.Throws<ArgumentException> (() => ExportRecipeValidator.Validate (recipe, [new ("PNG", ["png"], [], new GdkPixbufFormat ("png"), null)]));
		foreach (var ext in new[] { "png", "webp" })
			Assert.Throws<ArgumentException> (() => ExportRecipeValidator.Validate (recipe with { Extension = ext, Quality = 85 }, [Format (ext)]));
		var jpeg = Format ("jpeg", new JpegFormat ());
		Assert.Throws<ArgumentException> (() => ExportRecipeValidator.Validate (recipe with { Extension = "jpeg" }, [jpeg]));
		Assert.That (ExportRecipeValidator.Validate (recipe with { Extension = "jpeg", Quality = 85 }, [jpeg]).Options.JpegQuality, Is.EqualTo (85));
	}

	[TestCase ("C:/图片/cat.photo.ora", "-web", "png", "C:/图片/cat.photo-web.png")]
	[TestCase ("C:/图片/untitled", "", "jpg", "C:/图片/untitled.jpg")]
	[TestCase ("C:\\图片\\cat.ora", "-web", "png", "C:\\图片\\cat-web.png")]
	public void OutputPreviewPreservesUnicodeAndPathSeparators (string source, string suffix, string extension, string expected) =>
		Assert.That (ExportRecipePlan.ResolveOutputPath (source, suffix, extension), Is.EqualTo (expected));

	[TestCase (false)]
	[TestCase (true)]
	public async Task RealLayeredDocumentRemainsUnchangedAndPngHasRequestedDimensions (bool dirty)
	{
		using var temp = new RecipeDirectory ();
		Document doc = MakeDocument (dirty, temp.Path);
		try {
			var before = Snapshot (doc);
			var executor = new ExportRecipeExecutor ();
			string output = Path.Combine (temp.Path, "图片-web.png");
			var result = await executor.ExecuteAsync (executor.CreatePlan (new DocumentRecipeSource (doc), Recipe (), output), null!, CancellationToken.None);
			Assert.That (result.Status, Is.EqualTo (ExportRecipeStatus.Succeeded));
			Assert.That (result.ByteLength, Is.GreaterThan (0));
			using var pixbuf = GdkPixbuf.Pixbuf.NewFromFile (output)!;
			Assert.That (new Size (pixbuf.Width, pixbuf.Height), Is.EqualTo (new Size (32, 18)));
			Assert.That (Snapshot (doc), Is.EqualTo (before));
			Assert.That (Directory.GetFiles (temp.Path, ".pixelquay-*"), Is.Empty);
		} finally { doc.DisposeExportDocument (); }
	}

	[Test]
	public async Task RealJpegUsesSuppliedQualityWithoutEditorOrPrompt ()
	{
		using var temp = new RecipeDirectory ();
		var doc = MakeDocument (true, temp.Path);
		try {
			var before = Snapshot (doc);
			var executor = new ExportRecipeExecutor ();
			foreach (int quality in new[] { 10, 95 }) {
				var recipe = ExportRecipeValidator.Validate (new ("jpeg", "JPEG", 160, 90, "jpeg", quality, "", false), [Format ("jpeg", new JpegFormat ())]);
				await executor.ExecuteAsync (executor.CreatePlan (new DocumentRecipeSource (doc), recipe, Path.Combine (temp.Path, $"{quality}.jpeg")), null!, CancellationToken.None);
			}
			Assert.That (File.ReadAllBytes (Path.Combine (temp.Path, "10.jpeg")), Is.Not.EqualTo (File.ReadAllBytes (Path.Combine (temp.Path, "95.jpeg"))));
			Assert.That (Snapshot (doc), Is.EqualTo (before));
		} finally { doc.DisposeExportDocument (); }
	}

	[TestCase (false)]
	[TestCase (true)]
	public async Task PublishDecisionIsAtomicWhenDestinationAppearsAfterRendering (bool overwrite)
	{
		using var temp = new RecipeDirectory ();
		string output = Path.Combine (temp.Path, "race.png");
		var publisher = new RacePublisher ();
		var executor = new ExportRecipeExecutor (new ByteRenderer (), publisher);
		var plan = executor.CreatePlan (new ByteSource (), Recipe (overwrite: overwrite), output);
		if (overwrite) {
			await executor.ExecuteAsync (plan, null!, CancellationToken.None);
			Assert.That (File.ReadAllBytes (output), Is.EqualTo (new byte[] { 1, 2, 3 }));
		} else {
			Assert.ThrowsAsync<IOException> (() => executor.ExecuteAsync (plan, null!, CancellationToken.None));
			Assert.That (File.ReadAllBytes (output), Is.EqualTo (new byte[] { 9, 8, 7 }));
		}
		Assert.That (Directory.GetFiles (temp.Path, ".pixelquay-*"), Is.Empty);
	}

	[TestCase (false)]
	[TestCase (true)]
	public void CancellationNeverPublishesAndRemovesOnlyOwnStagingFile (bool duringRender)
	{
		using var temp = new RecipeDirectory ();
		using var cancellation = new CancellationTokenSource ();
		string output = Path.Combine (temp.Path, "original.png");
		File.WriteAllBytes (output, [9]);
		File.WriteAllText (Path.Combine (temp.Path, ".pixelquay-unrelated.png"), "other operation");
		if (!duringRender) cancellation.Cancel ();
		var executor = new ExportRecipeExecutor (new ByteRenderer (() => cancellation.Cancel ()), new AtomicOutputPublisher ());
		var plan = executor.CreatePlan (new ByteSource (), Recipe (overwrite: true), output);
		Assert.That (async () => await executor.ExecuteAsync (plan, null!, cancellation.Token), Throws.InstanceOf<OperationCanceledException> ());
		Assert.That (File.ReadAllBytes (output), Is.EqualTo (new byte[] { 9 }));
		Assert.That (Directory.GetFiles (temp.Path, ".pixelquay-*"), Has.Length.EqualTo (1));
	}

	[Test]
	public void ExporterFailureCleansStagingAndPreservesExistingOutput ()
	{
		using var temp = new RecipeDirectory ();
		string output = Path.Combine (temp.Path, "existing.png");
		File.WriteAllBytes (output, [9]);
		var executor = new ExportRecipeExecutor (new ByteRenderer (() => throw new IOException ("encoder failure")), new AtomicOutputPublisher ());
		Assert.ThrowsAsync<IOException> (() => executor.ExecuteAsync (executor.CreatePlan (new ByteSource (), Recipe (overwrite: true), output), null!, CancellationToken.None));
		Assert.That (File.ReadAllBytes (output), Is.EqualTo (new byte[] { 9 }));
		Assert.That (Directory.GetFiles (temp.Path, ".pixelquay-*"), Is.Empty);
	}

	[Test]
	public void RejectsSourcePathEvenWhenOverwriteExplicitAndWrongExtension ()
	{
		using var temp = new RecipeDirectory ();
		string input = Path.Combine (temp.Path, "input.png");
		var executor = new ExportRecipeExecutor ();
		Assert.Throws<ArgumentException> (() => executor.CreatePlan (new ByteSource (input), Recipe (overwrite: true), input));
		Assert.Throws<ArgumentException> (() => executor.CreatePlan (new ByteSource (), Recipe (), Path.Combine (temp.Path, "wrong.jpg")));
	}

	private static Document MakeDocument (bool dirty, string directory)
	{
		var doc = Document.CreateExportDocument (new Size (160, 90));
		string original = Path.Combine (directory, "pixelquay-layered-original.ora");
		File.WriteAllText (original, "original file contents");
		doc.File = Gio.FileHelper.NewForPath (original);
		doc.FileType = "ora";
		doc.HasBeenSavedInSession = true;
		var bottom = doc.Layers.AddNewLayer ("Background");
		using (var context = new Context (bottom.Surface)) { context.SetSourceRgb (0.15, 0.4, 0.8); context.Paint (); }
		var top = doc.Layers.AddNewLayer ("Transparent foreground");
		top.Opacity = 0.7;
		using (var context = new Context (top.Surface)) { context.SetSourceRgba (1, 0.3, 0.1, 0.6); context.Rectangle (10, 10, 70, 40); context.Fill (); }
		doc.Selection.CreateRectangleSelection (new RectangleD (5, 6, 30, 20));
		doc.Selection.Visible = true;
		doc.IsDirty = dirty;
		return doc;
	}

	private static string Snapshot (Document doc) => string.Join ("|", doc.ImageSize, doc.IsDirty, doc.File?.GetPath (), doc.FileType,
		doc.DisplayName, doc.HasBeenSavedInSession, doc.History.Pointer, doc.History.Items.Count (), doc.Selection.GetBounds (), doc.Selection.Visible,
		doc.Layers.CurrentUserLayerIndex, string.Join (";", doc.Layers.UserLayers.Select (l =>
			$"{l.Name}/{l.Hidden}/{l.Opacity}/{l.BlendMode}/{Convert.ToHexString (System.Runtime.InteropServices.MemoryMarshal.AsBytes (l.Surface.GetReadOnlyPixelData ()).ToArray ())}")));
}

internal sealed class RecipeDirectory : IDisposable
{
	public string Path { get; } = System.IO.Path.Combine (System.IO.Path.GetTempPath (), "pixelquay-tests-" + Guid.NewGuid ().ToString ("N"));
	public RecipeDirectory () => Directory.CreateDirectory (Path);
	public void Dispose () => Directory.Delete (Path, true);
}
internal sealed class ByteSource (string? path = null) : IExportRecipeSource
{
	public Size ImageSize => new (160, 90);
	public string? FilePath => path;
}
internal sealed class ByteRenderer (Action? afterWrite = null) : IExportRecipeRenderer
{
	public void Render (ExportRecipePlan plan, string stagingPath, Gtk.Window parent, CancellationToken token)
	{
		File.WriteAllBytes (stagingPath, [1, 2, 3]);
		afterWrite?.Invoke ();
	}
}
internal sealed class RacePublisher : IOutputPublisher
{
	public void Publish (string stagingPath, string destination, bool overwrite)
	{
		File.WriteAllBytes (destination, [9, 8, 7]);
		new AtomicOutputPublisher ().Publish (stagingPath, destination, overwrite);
	}
}
