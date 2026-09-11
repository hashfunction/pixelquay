// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Text.Json;

namespace Pinta.Core;

public sealed class ExportRecipeStore (ISettingsService settings)
{
	public const string SettingsKey = "pixelquay.export-recipes.v1";
	private sealed record Envelope (int Version, ExportRecipe[] Recipes);
	public string? LoadError { get; private set; }
	public bool CanSave => LoadError is null;
	private string last_read_json = "";

	public IReadOnlyList<ExportRecipe> Load ()
	{
		string json = last_read_json = settings.GetSetting (SettingsKey, "");
		LoadError = null;
		if (string.IsNullOrEmpty (json)) return [];
		try {
			var envelope = JsonSerializer.Deserialize<Envelope> (json);
			if (envelope is not { Version: 1, Recipes: not null })
				throw new ArgumentException ("Unsupported recipe settings version or structure.");
			return ValidateCollection (envelope.Recipes);
		} catch (Exception e) when (e is JsonException or ArgumentException) {
			LoadError = e.Message;
			Console.Error.WriteLine ($"PixelQuay could not load export recipes: {e.Message}");
			return [];
		}
	}

	public void Save (IEnumerable<ExportRecipe> recipes)
	{
		// Check the actual current setting, even if a different store instance skipped Load.
		Load ();
		if (!CanSave)
			throw new InvalidOperationException ("Saved recipes could not be read. Back up the unreadable recipes and start fresh, or restore valid settings before saving or deleting recipes.");
		settings.PutSetting (SettingsKey, JsonSerializer.Serialize (new Envelope (1, ValidateCollection (recipes))));
	}

	/// <summary>Explicit recovery: preserve the unreadable JSON durably before resetting it.</summary>
	public string BackupUnreadableRecipesAndReset ()
	{
		Load ();
		if (CanSave) throw new InvalidOperationException ("There are no unreadable recipes to recover.");
		string original = last_read_json;
		string backup = Path.Combine (settings.GetUserSettingsDirectory (), $"export-recipes-recovery-{DateTime.UtcNow:yyyyMMdd-HHmmss}-{Guid.NewGuid ():N}.json");
		// CreateNew protects any existing backup. No setting changes on write/flush failure.
		using (var stream = new FileStream (backup, FileMode.CreateNew, FileAccess.Write, FileShare.None)) {
			stream.Write (Encoding.UTF8.GetBytes (original));
			stream.Flush (flushToDisk: true);
		}
		if (settings.GetSetting (SettingsKey, "") != original)
			throw new InvalidOperationException ($"Recipes changed during recovery. A backup is at {backup}; reload before trying again.");
		settings.PutSetting (SettingsKey, JsonSerializer.Serialize (new Envelope (1, [])));
		Load ();
		return backup;
	}

	private static ExportRecipe[] ValidateCollection (IEnumerable<ExportRecipe> recipes)
	{
		var result = recipes.ToArray ();
		if (result.Length > 100) throw new ArgumentException ("A maximum of 100 recipes can be saved.");
		HashSet<string> ids = new (StringComparer.Ordinal);
		HashSet<string> names = new (StringComparer.OrdinalIgnoreCase);
		foreach (var recipe in result) {
			ExportRecipeValidator.ValidateStructure (recipe);
			if (!ids.Add (recipe.Id) || !names.Add (recipe.Name.Trim ()))
				throw new ArgumentException ("Recipe names and IDs must be unique.");
		}
		return result;
	}
}
