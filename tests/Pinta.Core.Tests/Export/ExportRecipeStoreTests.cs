using System;
using System.Collections.Generic;
using NUnit.Framework;

namespace Pinta.Core.Tests;

[TestFixture]
public sealed class ExportRecipeStoreTests
{
	[Test]
	public void RoundTripsUnicodeInVersionedEnvelope ()
	{
		var settings = new RecipeSettings ();
		var store = new ExportRecipeStore (settings);
		var recipe = new ExportRecipe ("thumb", "Résumé 图片", 320, 180, "png", null, "-web", false);
		store.Save ([recipe]);
		Assert.That (store.Load (), Is.EqualTo (new[] { recipe }));
		Assert.That (settings.GetSetting (ExportRecipeStore.SettingsKey, ""), Does.Contain ("\"Version\":1"));
	}

	[TestCase (0, 180, "png", "-web")]
	[TestCase (320, 0, "png", "-web")]
	[TestCase (320, 180, ".", "-web")]
	[TestCase (320, 180, "png", "../escape")]
	[TestCase (320, 180, "png", "\\escape")]
	[TestCase (320, 180, "png", ":stream")]
	public void RejectsUnsafeRecipe (int width, int height, string extension, string suffix)
	{
		Assert.That (() => new ExportRecipeStore (new RecipeSettings ()).Save (
			[new ("x", "X", width, height, extension, null, suffix, false)]), Throws.InstanceOf<ArgumentException> ());
	}

	[Test]
	public void RejectsDuplicateNamesOrIdsWithoutChangingExistingSettings ()
	{
		var settings = new RecipeSettings ();
		var store = new ExportRecipeStore (settings);
		var recipe = new ExportRecipe ("one", "One", 20, 20, "png", null, "", false);
		store.Save ([recipe]);
		Assert.Throws<ArgumentException> (() => store.Save ([recipe, recipe with { Id = "two", Name = "one" }]));
		Assert.Throws<ArgumentException> (() => store.Save ([recipe, recipe with { Name = "Two" }]));
		Assert.That (store.Load (), Is.EqualTo (new[] { recipe }));
	}

	[TestCase ("{broken")]
	[TestCase ("{\"Version\":99,\"Recipes\":[]}")]
	[TestCase ("{\"Version\":1,\"Recipes\":null}")]
	[TestCase ("{\"Version\":1,\"Recipes\":[null]}")]
	public void CorruptionIsRecoverableAndRetained (string json)
	{
		var settings = new RecipeSettings ();
		settings.PutSetting (ExportRecipeStore.SettingsKey, json);
		Assert.That (new ExportRecipeStore (settings).Load (), Is.Empty);
		Assert.That (settings.GetSetting (ExportRecipeStore.SettingsKey, ""), Is.EqualTo (json));
	}

	[Test]
	public void AllocationBudgetIncludesSourceAndWorkingCopies ()
	{
		Assert.DoesNotThrow (() => ExportRecipeValidator.ValidateDimensions (new Size (10000, 10000)));
		Assert.Throws<ArgumentOutOfRangeException> (() => ExportRecipeValidator.ValidateDimensions (new Size (10001, 10000)));
		Assert.Throws<ArgumentOutOfRangeException> (() => ExportRecipeValidator.ValidateDimensions (new Size (int.MaxValue, int.MaxValue)));
		Assert.Throws<ArgumentOutOfRangeException> (() => ExportRecipeValidator.ValidateWorkingSet (new Size (10000, 10000), new Size (10000, 10000)));
	}
}

internal sealed class RecipeSettings (string? directory = null) : ISettingsService
{
	private readonly Dictionary<string, object> values = [];
	public T GetSetting<T> (string key, T fallback) => values.TryGetValue (key, out var value) ? (T) value : fallback;
	public string GetUserSettingsDirectory () => directory ?? throw new NotSupportedException ();
	public void PutSetting (string key, object value) => values[key] = value;
	public event EventHandler? SaveSettingsBeforeQuit { add { } remove { } }
}
