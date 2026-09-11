using System;
using System.Text.Json;
using System.IO;
using NUnit.Framework;

namespace Pinta.Core.Tests;

public sealed class ExportRecipeRecoveryTests
{
	private static readonly ExportRecipe recipe = new ("old", "Preserve me", 32, 32, "png", null, "-web", false);
	private static string DamagedCollection () => JsonSerializer.Serialize (new {
		Version = 1, Recipes = new ExportRecipe?[] { recipe, null }
	});

	[TestCase (false)]
	[TestCase (true)]
	public void FailedLoadMustBlockSaveAndDeleteWithoutChangingStoredBytes (bool delete)
	{
		var settings = new RecipeSettings ();
		string original = DamagedCollection ();
		settings.PutSetting (ExportRecipeStore.SettingsKey, original);
		var store = new ExportRecipeStore (settings);
		Assert.That (store.Load (), Is.Empty);
		Assert.Throws<InvalidOperationException> (() => store.Save (delete ? [] : [recipe with { Id = "new", Name = "New" }]));
		Assert.That (settings.GetSetting (ExportRecipeStore.SettingsKey, ""), Is.EqualTo (original));
	}

	[Test]
	public void ANewStoreCannotBypassUnreadableDataProtectionBySavingWithoutLoad ()
	{
		var settings = new RecipeSettings ();
		string original = DamagedCollection ();
		settings.PutSetting (ExportRecipeStore.SettingsKey, original);
		Assert.Throws<InvalidOperationException> (() => new ExportRecipeStore (settings).Save ([recipe]));
		Assert.That (settings.GetSetting (ExportRecipeStore.SettingsKey, ""), Is.EqualTo (original));
	}
	[Test]
	public void ExplicitRecoveryPreservesExactUnreadableJsonBeforeAllowingNewRecipes ()
	{
		using var directory = new RecipeDirectory ();
		var settings = new RecipeSettings (directory.Path);
		string original = DamagedCollection ();
		settings.PutSetting (ExportRecipeStore.SettingsKey, original);
		var store = new ExportRecipeStore (settings);
		store.Load ();
		Assert.That (store.CanSave, Is.False);
		Assert.That (store.LoadError, Is.Not.Null.And.Not.Empty);
		string backup = store.BackupUnreadableRecipesAndReset ();
		Assert.That (File.ReadAllText (backup), Is.EqualTo (original));
		Assert.That (store.CanSave, Is.True);
		Assert.That (store.LoadError, Is.Null);
		store.Save ([recipe]);
		Assert.That (new ExportRecipeStore (settings).Load (), Is.EqualTo (new[] { recipe }));
		Assert.That (File.ReadAllText (backup), Is.EqualTo (original));
	}

	[Test]
	public void FailedBackupLeavesRecipesLockedAndOriginalBytesUntouched ()
	{
		using var directory = new RecipeDirectory ();
		var settings = new RecipeSettings (Path.Combine (directory.Path, "missing-parent", "missing-directory"));
		string original = DamagedCollection ();
		settings.PutSetting (ExportRecipeStore.SettingsKey, original);
		var store = new ExportRecipeStore (settings);
		store.Load ();
		Assert.Throws<DirectoryNotFoundException> (() => store.BackupUnreadableRecipesAndReset ());
		Assert.That (store.CanSave, Is.False);
		Assert.That (settings.GetSetting (ExportRecipeStore.SettingsKey, ""), Is.EqualTo (original));
		Assert.Throws<InvalidOperationException> (() => store.Save ([]));
	}

	[Test]
	public void RetryAfterRestorationAndFreshSettingsAllowOrdinarySave ()
	{
		var settings = new RecipeSettings ();
		var store = new ExportRecipeStore (settings);
		Assert.That (store.Load (), Is.Empty);
		Assert.That (store.CanSave, Is.True);
		store.Save ([recipe]);
		string valid = settings.GetSetting (ExportRecipeStore.SettingsKey, "");
		settings.PutSetting (ExportRecipeStore.SettingsKey, "{broken");
		store.Load ();
		Assert.That (store.CanSave, Is.False);
		settings.PutSetting (ExportRecipeStore.SettingsKey, valid);
		Assert.That (store.Load (), Is.EqualTo (new[] { recipe }));
		Assert.That (store.CanSave, Is.True);
		store.Save ([]);
		Assert.That (store.Load (), Is.Empty);
		Assert.Throws<InvalidOperationException> (() => store.BackupUnreadableRecipesAndReset ());
	}

}
