// Copyright (c) 2026 Trieflow LLC. Licensed under the MIT License.
using System.IO;

namespace Pinta.Core;

public interface IOutputPublisher
{
	void Publish (string stagedPath, string destination, bool overwrite);
}

public sealed class AtomicOutputPublisher : IOutputPublisher
{
	public void Publish (string stagedPath, string destination, bool overwrite) =>
		// Authoritative no-replace decision at publication, including destination races.
		File.Move (stagedPath, destination, overwrite);
}
