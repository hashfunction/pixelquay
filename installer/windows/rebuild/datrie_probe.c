/* Copyright 2026 Trieflow LLC. MIT licensed.
 * Standalone build proof; never compiled into PixelQuay or its runtime. */
#ifndef _WIN32
#define _DARWIN_C_SOURCE
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <datrie/trie.h>
#ifdef _WIN32
#include <windows.h>
#include <direct.h>
typedef HMODULE Library;
static void *symbol(Library h, const char *name) { return (void *)GetProcAddress(h, name); }
#else
#include <dlfcn.h>
#include <limits.h>
#include <unistd.h>
typedef void *Library;
static void *symbol(Library h, const char *name) { return dlsym(h, name); }
#endif

typedef AlphaMap *(*MapNew)(void);
typedef int (*MapRange)(AlphaMap *, AlphaChar, AlphaChar);
typedef void (*MapFree)(AlphaMap *);
typedef Trie *(*TrieNew)(const AlphaMap *);
typedef void (*TrieFree)(Trie *);
typedef Bool (*Store)(Trie *, const AlphaChar *, TrieData);
typedef Bool (*Retrieve)(const Trie *, const AlphaChar *, TrieData *);
typedef Bool (*Delete)(Trie *, const AlphaChar *);
typedef int (*Save)(Trie *, const char *);
typedef Trie *(*Open)(const char *);
typedef TrieState *(*Root)(const Trie *);
typedef Bool (*Walk)(TrieState *, AlphaChar);
typedef TrieData (*StateData)(const TrieState *);
typedef void (*StateFree)(TrieState *);
typedef const char *(*Marker)(void);
#define LOAD(type, variable, name) \
    type variable = (type)symbol(library, name); \
    if (!variable) { fprintf(stderr, "Missing required export: %s\n", name); return 2; }
#define CHECK(expression) do { \
    if (!(expression)) { fprintf(stderr, "API check failed: %s\n", #expression); status = 3; goto done; } \
    ++checks; \
} while (0)

static int exercise(Library library, const char *mode)
{
    LOAD(MapNew, map_new, "alpha_map_new");
    LOAD(MapRange, map_range, "alpha_map_add_range");
    LOAD(MapFree, map_free, "alpha_map_free");
    LOAD(TrieNew, trie_create, "trie_new");
    LOAD(TrieFree, trie_release, "trie_free");
    LOAD(Store, store, "trie_store");
    LOAD(Store, store_absent, "trie_store_if_absent");
    LOAD(Retrieve, retrieve, "trie_retrieve");
    LOAD(Delete, remove_key, "trie_delete");
    LOAD(Save, save, "trie_save");
    LOAD(Open, open_trie, "trie_new_from_file");
    LOAD(Root, root, "trie_root");
    LOAD(Walk, walk, "trie_state_walk");
    LOAD(StateData, state_data, "trie_state_get_data");
    LOAD(StateFree, state_free, "trie_state_free");
    Marker marker = (Marker)symbol(library, "pixelquay_rebuild_marker");
    if ((!strcmp(mode, "original") && marker) ||
        (!strcmp(mode, "modified") && (!marker || strcmp(marker(), "PixelQuay libdatrie source rebuild v1")))) {
        fputs("Marker expectation failed\n", stderr);
        return 4;
    }
    /* Exclusive claim before trie_save uses its path-based writer. The caller
     * supplies an otherwise empty owned working directory; leave evidence. */
    FILE *claim = fopen("probe.trie", "wx");
    if (!claim) { fputs("Probe output already exists or cannot be created\n", stderr); return 5; }
    if (fclose(claim)) return 5;
    int status = 0, checks = 0;
    AlphaMap *map = NULL;
    Trie *trie = NULL, *loaded = NULL;
    TrieState *state = NULL;
    const AlphaChar key[] = {'b', 'a', 's', 's', 0};
    const AlphaChar absent[] = {'d', 'r', 'u', 'm', 0};
    const AlphaChar invalid[] = {0x1000, 0};
    TrieData value = 0;
    CHECK((map = map_new()) != NULL);
    CHECK(map_range(map, 'a', 'z') == 0);
    CHECK((trie = trie_create(map)) != NULL);
    CHECK(!retrieve(trie, key, &value));
    CHECK(store(trie, key, 73));
    CHECK(retrieve(trie, key, &value) && value == 73);
    CHECK(!store_absent(trie, key, 99));
    CHECK(retrieve(trie, key, &value) && value == 73);
    CHECK(store(trie, key, 81));
    CHECK(retrieve(trie, key, &value) && value == 81);
    CHECK(!store(trie, invalid, 1));
    CHECK(!retrieve(trie, absent, &value));
    CHECK((state = root(trie)) != NULL);
    CHECK(walk(state, 'b') && walk(state, 'a') && walk(state, 's') && walk(state, 's') && walk(state, 0));
    CHECK(state_data(state) == 81);
    CHECK(save(trie, "probe.trie") == 0);
    CHECK((loaded = open_trie("probe.trie")) != NULL);
    CHECK(retrieve(loaded, key, &value) && value == 81);
    CHECK(remove_key(loaded, key));
    CHECK(!retrieve(loaded, key, &value));
    CHECK(retrieve(trie, key, &value) && value == 81);
done:
    if (state) state_free(state);
    if (loaded) trie_release(loaded);
    if (trie) trie_release(trie);
    if (map) map_free(map);
    if (!status) printf("{\"schemaVersion\":1,\"mode\":\"%s\",\"apiChecks\":%d,\"libraryPathMatched\":true,\"markerPresent\":%s}\n", mode, checks, marker ? "true" : "false");
    return status;
}

#ifdef _WIN32
int wmain(int argc, wchar_t **argv)
{
    if (argc != 4 || (wcscmp(argv[2], L"original") && wcscmp(argv[2], L"modified"))) return 64;
    wchar_t expected[32768], actual[32768];
    DWORD length = GetFullPathNameW(argv[1], 32768, expected, NULL);
    if (!length || length >= 32768 || _wcsicmp(expected, argv[1])) return 65;
    Library library = LoadLibraryExW(expected, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!library) { fprintf(stderr, "LoadLibraryExW failed: %lu\n", GetLastError()); return 66; }
    length = GetModuleFileNameW(library, actual, 32768);
    if (!length || length >= 32768 || _wcsicmp(expected, actual) || _wchdir(argv[3])) { FreeLibrary(library); return 67; }
    int status = exercise(library, !wcscmp(argv[2], L"original") ? "original" : "modified");
    if (!FreeLibrary(library) && !status) status = 68;
    return status;
}
#else
int main(int argc, char **argv)
{
    if (argc != 4 || (strcmp(argv[2], "original") && strcmp(argv[2], "modified"))) return 64;
    char expected[PATH_MAX], actual[PATH_MAX];
    if (!realpath(argv[1], expected) || strcmp(expected, argv[1])) return 65;
    Library library = dlopen(expected, RTLD_NOW | RTLD_LOCAL);
    if (!library) { fprintf(stderr, "dlopen failed: %s\n", dlerror()); return 66; }
    Dl_info info;
    if (!dladdr(symbol(library, "trie_new"), &info) || !realpath(info.dli_fname, actual) || strcmp(expected, actual) || chdir(argv[3])) { dlclose(library); return 67; }
    int status = exercise(library, argv[2]);
    if (dlclose(library) && !status) status = 68;
    return status;
}
#endif
