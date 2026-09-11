// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Pinta.Core;

namespace Pinta;

public sealed record ExportRecipeDialogResult (ValidatedExportRecipe Recipe, string Destination);

public sealed class ExportRecipeDialog : Gtk.Dialog
{
	private readonly ExportRecipeStore store;
	private readonly DocumentRecipeSource source;
	private readonly FormatDescriptor[] formats;
	private readonly List<ExportRecipe> recipes;
	private readonly Gtk.ComboBoxText recipe_choice = new ();
	private readonly Gtk.ComboBoxText format_choice = new ();
	private readonly Gtk.Entry name = new ();
	private readonly Gtk.Entry suffix = new ();
	private readonly Gtk.SpinButton width = Gtk.SpinButton.NewWithRange (1, ExportRecipeValidator.MaximumDimension, 1);
	private readonly Gtk.SpinButton height = Gtk.SpinButton.NewWithRange (1, ExportRecipeValidator.MaximumDimension, 1);
	private readonly Gtk.SpinButton quality = Gtk.SpinButton.NewWithRange (1, 100, 1);
	private readonly Gtk.CheckButton overwrite = Gtk.CheckButton.NewWithLabel (Translations.GetString ("Replace an existing output"));
	private readonly Gtk.Label preview = new () { Xalign = 0, Wrap = true, Selectable = true };
	private readonly Gtk.Label status = new () { Xalign = 0, Wrap = true };
	private readonly Gtk.Label quality_label;
	private readonly Gtk.Box recovery = Gtk.Box.New (Gtk.Orientation.Vertical, 6);
	private readonly Gtk.Label recovery_message = new () { Xalign = 0, Wrap = true };
	private readonly Gtk.Button save = Gtk.Button.NewWithLabel (Translations.GetString ("Save recipe"));
	private readonly Gtk.Button delete = Gtk.Button.NewWithLabel (Translations.GetString ("Delete"));
	private string current_id = Guid.NewGuid ().ToString ("N");
	private string? directory;
	private bool loading;
	private ExportRecipeDialogResult? result;

	public ExportRecipeDialog (Gtk.Window parent, Document document, ExportRecipeStore store, IEnumerable<FormatDescriptor> availableFormats)
	{
		this.store = store;
		source = new (document);
		formats = availableFormats.Where (f => f.IsExportAvailable ()).ToArray ();
		recipes = store.Load ().ToList ();
		Title = Translations.GetString ("Export with Recipe");
		TransientFor = parent;
		Modal = true;
		DefaultWidth = 600;
		this.AddButton (Translations.GetString ("_Cancel"), (int) Gtk.ResponseType.Cancel);
		this.AddButton (Translations.GetString ("_Export image"), (int) Gtk.ResponseType.Ok);
		SetDefaultResponse ((int) Gtk.ResponseType.Ok);

		var content = this.GetContentAreaBox ();
		content.SetAllMargins (18);
		content.Spacing = 12;
		content.Append (Gtk.Label.New (Translations.GetString ("Create a resized, flattened image. Your layered document stays open.")));
		var chooser_row = Gtk.Box.New (Gtk.Orientation.Horizontal, 6);
		recipe_choice.Hexpand = true;
		var create = Gtk.Button.NewWithLabel (Translations.GetString ("New"));
		chooser_row.AppendMultiple ([recipe_choice, create, delete]);
		content.Append (chooser_row);
		var retry = Gtk.Button.NewWithLabel ("Retry loading recipes");
		var reset = Gtk.Button.NewWithLabel ("Back up unreadable recipes and start fresh");
		recovery.AppendMultiple ([recovery_message, retry, reset]);
		content.Append (recovery);
		retry.OnClicked += (_, _) => ReloadRecipes ();
		reset.OnClicked += (_, _) => RecoverRecipes ();
		var grid = new Gtk.Grid { ColumnSpacing = 12, RowSpacing = 10 };
		AddRow (grid, 0, "Recipe _name", name);
		AddRow (grid, 1, "_Width (pixels)", width);
		AddRow (grid, 2, "_Height (pixels)", height);
		AddRow (grid, 3, "_Format", format_choice);
		quality_label = AddRow (grid, 4, "JPEG _quality", quality);
		AddRow (grid, 5, "Filename _suffix", suffix);
		grid.Attach (overwrite, 1, 6, 1, 1);
		grid.Attach (save, 1, 7, 1, 1);
		content.Append (grid);
		var destination = Gtk.Button.NewWithLabel (Translations.GetString ("Choose destination folder…"));
		content.AppendMultiple ([destination, preview, status]);
		foreach (var format in formats)
			format_choice.AppendText (format.Extensions[0].ToUpperInvariant ());
		quality.Value = 85;

		create.OnClicked += (_, _) => NewRecipe ();
		delete.OnClicked += (_, _) => DeleteRecipe ();
		save.OnClicked += (_, _) => SaveRecipe ();
		destination.OnClicked += async (_, _) => await ChooseDestination ();
		recipe_choice.OnChanged += (_, _) => {
			if (!loading && recipe_choice.Active >= 0 && recipe_choice.Active < recipes.Count)
				LoadRecipe (recipes[recipe_choice.Active]);
		};
		format_choice.OnChanged += (_, _) => ValidateInput ();
		name.OnChanged += (_, _) => ValidateInput ();
		suffix.OnChanged += (_, _) => ValidateInput ();
		width.OnValueChanged += (_, _) => ValidateInput ();
		height.OnValueChanged += (_, _) => ValidateInput ();
		quality.OnValueChanged += (_, _) => ValidateInput ();
		overwrite.OnToggled += (_, _) => ValidateInput ();
		RefreshChoices ();
		if (recipes.Count > 0) { recipe_choice.Active = 0; LoadRecipe (recipes[0]); }
		else NewRecipe ();
		name.GrabFocus ();
	}

	private static Gtk.Label AddRow (Gtk.Grid grid, int row, string text, Gtk.Widget control)
	{
		var label = Gtk.Label.NewWithMnemonic (Translations.GetString (text));
		label.Xalign = 0;
		label.MnemonicWidget = control;
		control.Hexpand = true;
		grid.Attach (label, 0, row, 1, 1);
		grid.Attach (control, 1, row, 1, 1);
		return label;
	}

	public async Task<ExportRecipeDialogResult?> RunAsync ()
	{
		var response = await GtkExtensions.RunAsync (this);
		return response == Gtk.ResponseType.Ok ? result : null;
	}

	private void NewRecipe ()
	{
		int index = 1;
		while (recipes.Any (r => r.Name == $"Recipe {index}")) ++index;
		loading = true;
		recipe_choice.Active = -1;
		loading = false;
		LoadRecipe (new (Guid.NewGuid ().ToString ("N"), $"Recipe {index}",
			Math.Min (source.ImageSize.Width, 1920), Math.Min (source.ImageSize.Height, 1080), "png", null, "-export", false));
	}

	private void LoadRecipe (ExportRecipe recipe)
	{
		loading = true;
		current_id = recipe.Id;
		name.SetText (recipe.Name);
		width.Value = recipe.Width;
		height.Value = recipe.Height;
		suffix.SetText (recipe.Suffix);
		overwrite.Active = recipe.Overwrite;
		quality.Value = recipe.Quality ?? 85;
		format_choice.Active = Array.FindIndex (formats, f => f.Extensions.Any (e => e.Equals (recipe.Extension, StringComparison.OrdinalIgnoreCase)));
		loading = false;
		ValidateInput ();
	}

	private ValidatedExportRecipe ReadRecipe ()
	{
		if (format_choice.Active < 0) throw new ArgumentException ("Select an available export format.");
		var format = formats[format_choice.Active];
		var recipe = new ExportRecipe (current_id, name.GetText ().Trim (), width.GetValueAsInt (), height.GetValueAsInt (),
			format.Extensions[0], ExportRecipeValidator.SupportsQuality (format) ? quality.GetValueAsInt () : null, suffix.GetText (), overwrite.Active);
		if (recipes.Any (r => r.Id != current_id && r.Name.Equals (recipe.Name, StringComparison.OrdinalIgnoreCase)))
			throw new ArgumentException ("Choose a unique recipe name.");
		return ExportRecipeValidator.Validate (recipe, formats);
	}

	private void ValidateInput ()
	{
		if (loading) return;
		bool show_quality = format_choice.Active >= 0 && ExportRecipeValidator.SupportsQuality (formats[format_choice.Active]);
		quality.Visible = quality_label.Visible = show_quality;
		recovery.Visible = !store.CanSave;
		recovery_message.SetText ($"Saved recipes could not be read. Saving and deleting are locked to preserve them. {store.LoadError}");
		delete.Sensitive = store.CanSave && recipes.Any (r => r.Id == current_id);
		save.Sensitive = false;
		SetResponseSensitive ((int) Gtk.ResponseType.Ok, false);
		result = null;
		try {
			var recipe = ReadRecipe ();
			save.Sensitive = store.CanSave;
			if (directory is null) {
				preview.SetText ("Choose a destination folder to preview the output path.");
				status.SetText ("Save the recipe to reuse these settings later.");
				return;
			}
			string basename = Path.GetFileName (source.FilePath ?? source.Document.DisplayName);
			string output = ExportRecipePlan.ResolveOutputPath (Path.Combine (directory, basename), recipe.Recipe.Suffix, recipe.Recipe.Extension);
			preview.SetText (output);
			var plan = new ExportRecipeExecutor ().CreatePlan (source, recipe, output);
			result = new (recipe, plan.OutputPath);
			status.SetText (File.Exists (output)
				? recipe.Recipe.Overwrite ? "The existing output will be replaced." : "An output already exists. Choose another folder or suffix, or explicitly enable replacement."
				: $"{recipe.Recipe.Width} × {recipe.Recipe.Height} pixels · {recipe.Recipe.Extension.ToUpperInvariant ()}");
			SetResponseSensitive ((int) Gtk.ResponseType.Ok, !File.Exists (output) || recipe.Recipe.Overwrite);
		} catch (Exception e) when (e is ArgumentException or IOException or UnauthorizedAccessException) {
			status.SetText (e.Message);
		}
	}

	private void RefreshChoices ()
	{
		loading = true;
		recipe_choice.RemoveAll ();
		foreach (var recipe in recipes) recipe_choice.AppendText (recipe.Name);
		recipe_choice.Active = recipes.FindIndex (r => r.Id == current_id);
		loading = false;
	}

	private void SaveRecipe ()
	{
		try {
			var recipe = ReadRecipe ().Recipe;
			var next = recipes.Where (r => r.Id != recipe.Id).Append (recipe).ToList ();
			store.Save (next);
			recipes.Clear ();
			recipes.AddRange (next);
			RefreshChoices ();
			ValidateInput ();
			status.SetText ("Recipe saved.");
		} catch (Exception e) when (e is ArgumentException or IOException or UnauthorizedAccessException or InvalidOperationException) { ValidateInput (); status.SetText (e.Message); }
	}

	private void DeleteRecipe ()
	{
		try {
			var next = recipes.Where (r => r.Id != current_id).ToList ();
			store.Save (next);
			ReloadRecipes ();
		} catch (Exception e) when (e is ArgumentException or IOException or UnauthorizedAccessException or InvalidOperationException) {
			ValidateInput ();
			status.SetText (e.Message);
		}
	}

	private void ReloadRecipes ()
	{
		recipes.Clear ();
		recipes.AddRange (store.Load ());
		RefreshChoices ();
		if (recipes.Count == 0) NewRecipe ();
		else { recipe_choice.Active = 0; LoadRecipe (recipes[0]); }
	}

	private void RecoverRecipes ()
	{
		try {
			string backup = store.BackupUnreadableRecipesAndReset ();
			ReloadRecipes ();
			status.SetText ($"Unreadable recipes are preserved at {backup}. You can now save new recipes.");
		} catch (Exception e) when (e is IOException or UnauthorizedAccessException or InvalidOperationException) {
			ValidateInput ();
			status.SetText ($"Recovery failed: {e.Message} Your saved recipes have not been replaced.");
		}
	}

	private async Task ChooseDestination ()
	{
		using var chooser = Gtk.FileChooserNative.New ("Export destination", this, Gtk.FileChooserAction.SelectFolder, "Choose", "Cancel");
		if (directory is not null) chooser.SetCurrentFolder (Gio.FileHelper.NewForPath (directory));
		try {
			if (await chooser.RunAsync () != Gtk.ResponseType.Accept) return;
			directory = chooser.GetFile ()?.GetPath ();
			ValidateInput ();
		} finally { chooser.Destroy (); }
	}
}
