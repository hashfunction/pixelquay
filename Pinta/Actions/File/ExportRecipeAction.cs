// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System;
using System.Threading;
using Pinta.Core;

namespace Pinta.Actions;

internal sealed class ExportRecipeAction (FileActions file, ChromeManager chrome, WorkspaceManager workspace,
	ImageConverterManager formats, ISettingsService settings) : IActionHandler
{
	private bool running;
	void IActionHandler.Initialize () => file.ExportRecipes.Activated += Activated;
	void IActionHandler.Uninitialize () => file.ExportRecipes.Activated -= Activated;

	private async void Activated (object sender, EventArgs args)
	{
		if (running || !workspace.HasOpenDocuments) return;
		running = true;
		Document document = workspace.ActiveDocument;
		string destination = "the selected destination";
		try {
			ExportRecipeDialogResult? choice;
			using (var dialog = new ExportRecipeDialog (chrome.MainWindow, document, new ExportRecipeStore (settings), formats.Formats)) {
				try { choice = await dialog.RunAsync (); }
				finally { dialog.Destroy (); }
			}
			if (choice is null) return;
			destination = choice.Destination;
			var executor = new ExportRecipeExecutor ();
			var plan = executor.CreatePlan (new DocumentRecipeSource (document), choice.Recipe, destination);
			using var cancellation = new CancellationTokenSource ();
			using var progress = new ProgressDialog (chrome) {
				Title = "Exporting image",
				Text = "Rendering a copy and writing the selected format…",
			};
			var spinner = Gtk.Spinner.New ();
			spinner.Start ();
			progress.GetContentAreaBox ().Append (spinner);
			progress.Canceled += (_, _) => { cancellation.Cancel (); progress.Text = "Canceling after the current image operation…"; };
			progress.OnCloseRequest += (_, _) => { cancellation.Cancel (); return true; };
			// Keep all source-editing UI disabled until the worker and its cleanup finish.
			chrome.MainWindow.Sensitive = false;
			progress.Present ();
			try {
				await executor.ExecuteAsync (plan, progress, cancellation.Token);
			} finally {
				progress.Destroy ();
				chrome.MainWindow.Sensitive = true;
			}
			await chrome.ShowMessageDialog (chrome.MainWindow, "Image exported", destination);
		} catch (OperationCanceledException) {
			// The executor has removed its own staging output; the original remains open.
		} catch (Exception error) {
			await chrome.ShowMessageDialog (chrome.MainWindow, "Export failed",
				$"Input: {document.DisplayName}\nDestination: {destination}\n\n{error.Message}\n\nYour open document is unchanged. Choose a writable folder or another filename suffix, then try again.");
		} finally { running = false; }
	}
}
