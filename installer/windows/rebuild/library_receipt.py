"""Native libdatrie proof acceptance. Copyright 2026 Trieflow LLC; MIT."""
from pathlib import Path
import re
import struct

from libdatrie_source import COPYING_SHA

UPSTREAM_TESTS = ['test_walk', 'test_iterator', 'test_store-retrieve', 'test_file', 'test_serialization', 'test_nonalpha', 'test_null_trie', 'test_term_state', 'test_byte_alpha', 'test_byte_list']
SELECTED_PACKAGES = {
    'mingw-w64-clang-x86_64-clang': '22.1.8-2',
    'mingw-w64-clang-x86_64-libiconv': '1.19-1',
    'mingw-w64-clang-x86_64-autotools': '2026.08.04-1',
    'mingw-w64-clang-x86_64-doxygen': '1.18.0-3',
}
SELECTED_ARCHIVE_HASHES = {
    'mingw-w64-clang-x86_64-clang': '4eb99c39d1ade53dc55362c7c334265e629b84270dbe474377900330e0b81a5d',
    'mingw-w64-clang-x86_64-libiconv': '26c4ac9f2023eecdfffb291cab40c60585a0cd0f72539ca03c5558f3ecd309ec',
    'mingw-w64-clang-x86_64-autotools': '81d35b1dd9da5266e9d31de2e519839b8d3f0b420afa60366f0864d2177cb78c',
    'mingw-w64-clang-x86_64-doxygen': '8e8ffda50e7929920285d8d1f8eca5c64ec2a7149b2bcd9b54c19c658c441724',
}
SHIPPED_DLL_SHA = 'f2f133c99ce5eedfd7785e66d45d7ced2e01481d49678f7d1ecd27927b4cd561'


def pe_inventory(data):
    """Read bounded PE32+ name tables directly, independent of compiler output."""
    def take(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('PE range outside file')
        return data[offset:offset + size]

    def u32(offset): return struct.unpack('<I', take(offset, 4))[0]
    def u16(offset): return struct.unpack('<H', take(offset, 2))[0]
    if take(0, 2) != b'MZ': raise ValueError('Not a PE file')
    pe = u32(0x3c)
    if take(pe, 4) != b'PE\0\0' or u16(pe + 4) != 0x8664:
        raise ValueError('Expected x64 PE architecture')
    count, optional_size = u16(pe + 6), u16(pe + 20)
    optional = pe + 24
    if not 1 <= count <= 96 or optional_size < 128 or u16(optional) != 0x20b or u32(optional + 108) < 2:
        raise ValueError('Invalid PE32+ headers')
    take(optional, optional_size)
    sections = []
    for index in range(count):
        offset = optional + optional_size + index * 40
        take(offset, 40)
        virtual_size, address, size, raw = struct.unpack('<IIII', take(offset + 8, 16))
        take(raw, size)
        sections.append((address, size, raw))

    def rva(address, size):
        matches = [(raw + address - start) for start, length, raw in sections if start <= address and address + size <= start + length]
        if len(matches) != 1: raise ValueError('PE RVA unmapped or ambiguous')
        take(matches[0], size)
        return matches[0]

    def name(address):
        result = bytearray()
        for index in range(512):
            char = take(rva(address + index, 1), 1)
            if char == b'\0':
                try: value = result.decode('ascii')
                except UnicodeDecodeError as error: raise ValueError('Non-ASCII PE name') from error
                if not value: raise ValueError('Empty PE name')
                return value
            result.extend(char)
        raise ValueError('Unterminated PE name')

    export_rva, export_size, import_rva, import_size = struct.unpack('<IIII', take(optional + 112, 16))
    if not export_rva or export_size < 40: raise ValueError('Missing export directory')
    directory = rva(export_rva, 40)
    number = u32(directory + 24)
    if not 1 <= number <= 4096: raise ValueError('Invalid export count')
    table = rva(u32(directory + 32), number * 4)
    exports = [name(u32(table + index * 4)) for index in range(number)]
    if len(set(exports)) != len(exports): raise ValueError('Duplicate export names')
    imports = []
    if import_rva:
        if not 20 <= import_size <= 512 * 20: raise ValueError('Invalid import directory size')
        for index in range(import_size // 20):
            item = take(rva(import_rva + index * 20, 20), 20)
            if item == bytes(20): break
            imports.append(name(struct.unpack_from('<I', item, 12)[0]).casefold())
        else: raise ValueError('Unterminated import table')
    return {'machine': 'x64', 'exports': sorted(exports), 'imports': sorted(set(imports))}


def read_upstream_tests(root):
    root = Path(root)
    actual = {p.stem for p in root.glob('*.trs')}
    if actual != set(UPSTREAM_TESTS):
        raise ValueError('Expected exactly ten upstream test result files')
    result = {}
    for name in UPSTREAM_TESTS:
        text = (root / (name + '.trs')).read_text()
        if re.findall(r'^:test-result: (\S+)\s*$', text, re.M) != ['PASS'] or re.findall(r'^:global-test-result: (\S+)\s*$', text, re.M) != ['PASS']:
            raise ValueError(f'Upstream test did not pass: {name}')
        result[name] = 'PASS'
    return result


def validate_environment(before, after):
    for name, version in SELECTED_PACKAGES.items():
        if before.get('packages', {}).get(name) != version:
            raise ValueError(f'Wrong selected CLANG64 package: {name}; expected {version}')
    for field in ('packages', 'tools', 'configs'):
        if not before.get(field) or before[field] != after.get(field):
            raise ValueError(f'Build environment changed or missing: {field}')
    if before != after:
        raise ValueError('Compiler search/configured environment changed between builds')
    return True


def validate_pair(original, modified, expected_exports):
    marker = 'pixelquay_rebuild_marker'
    expected = set(expected_exports)
    if not {'trie_free', 'trie_new'} <= expected or marker in expected:
        raise ValueError('Invalid verified original export list')
    for mode, record in [('original', original), ('modified', modified)]:
        if record.get('machine') != 'x64' or not re.fullmatch('[0-9a-f]{64}', record.get('sha256', '')):
            raise ValueError('Missing x64 binary/hash evidence')
        if record.get('copyingSha256') != COPYING_SHA:
            raise ValueError('Original COPYING was not preserved')
        if record.get('upstreamTests') != {name: 'PASS' for name in UPSTREAM_TESTS}:
            raise ValueError('All ten upstream tests must pass')
        probe = record.get('probe', {})
        if probe.get('mode') != mode or probe.get('apiChecks') != 21 or probe.get('libraryPathMatched') is not True or probe.get('markerPresent') is not (mode == 'modified'):
            raise ValueError('Actual library/API probe did not match variant')
        wanted = expected | ({marker} if mode == 'modified' else set())
        if record.get('exports') != sorted(wanted):
            raise ValueError(f'{mode} exports do not match the verified source ABI')
    if original.get('imports') != modified.get('imports'):
        raise ValueError('Modified library gained/lost imported dependencies')
    if modified['sha256'] in (original['sha256'], SHIPPED_DLL_SHA):
        raise ValueError('Modified library must differ from original and shipped DLL')
    return True
