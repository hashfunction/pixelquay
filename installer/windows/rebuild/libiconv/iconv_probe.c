/* Copyright 2026 Trieflow LLC. MIT. Standalone proof, never product code. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

typedef const char *(*TextFn)(void);
typedef void *(*OpenFn)(const char *, const char *);
typedef size_t (*ConvertFn)(void *, const char **, size_t *, char **, size_t *);
typedef int (*CloseFn)(void *);

static void *required(HMODULE library, const char *name)
{
  void *result = (void *)GetProcAddress(library, name);
  if (!result) fprintf(stderr, "Missing required export: %s\n", name);
  return result;
}

static int exact_module(HMODULE library, const wchar_t *argument)
{
  wchar_t expected[32768], actual[32768];
  DWORD length = GetFullPathNameW(argument, 32768, expected, NULL);
  if (!length || length >= 32768 || _wcsicmp(expected, argument)) return 0;
  length = GetModuleFileNameW(library, actual, 32768);
  return length && length < 32768 && !_wcsicmp(expected, actual);
}

int wmain(int argc, wchar_t **argv)
{
  if (argc != 4 || (wcscmp(argv[3], L"original") && wcscmp(argv[3], L"modified"))) return 64;
  HMODULE charset = LoadLibraryExW(argv[1], NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
  HMODULE iconv = LoadLibraryExW(argv[2], NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
  if (!charset || !iconv) { fprintf(stderr, "LoadLibraryExW failed: %lu\n", GetLastError()); return 65; }
  if (!exact_module(charset, argv[1]) || !exact_module(iconv, argv[2])) return 66;
  TextFn locale_charset = (TextFn)required(charset, "locale_charset");
  OpenFn open_iconv = (OpenFn)required(iconv, "libiconv_open");
  ConvertFn convert = (ConvertFn)required(iconv, "libiconv");
  CloseFn close_iconv = (CloseFn)required(iconv, "libiconv_close");
  if (!locale_charset || !open_iconv || !convert || !close_iconv) return 2;
  TextFn charset_marker = (TextFn)GetProcAddress(charset, "pixelquay_libcharset_rebuild_marker");
  TextFn iconv_marker = (TextFn)GetProcAddress(iconv, "pixelquay_libiconv_rebuild_marker");
  int modified = !wcscmp(argv[3], L"modified");
  if ((!modified && (charset_marker || iconv_marker)) ||
      (modified && (!charset_marker || !iconv_marker ||
       strcmp(charset_marker(), "PixelQuay libcharset source rebuild v1") ||
       strcmp(iconv_marker(), "PixelQuay libiconv source rebuild v1")))) {
    fputs("Marker expectation failed\n", stderr); return 4;
  }
  const char *locale = locale_charset();
  int charset_checks = 0;
  if (!locale) return 3;
  ++charset_checks;
  if (!*locale) return 3;
  ++charset_checks;
  void *descriptor = open_iconv("UTF-8", "ISO-8859-1");
  int iconv_checks = 0;
  if (descriptor == (void *)-1) return 3;
  ++iconv_checks;
  char input_data[] = {(char)0xe9}; const char *input = input_data; size_t input_left = 1;
  char output_data[4] = {0}; char *output = output_data; size_t output_left = sizeof(output_data);
  if (convert(descriptor, &input, &input_left, &output, &output_left) != 0) return 3;
  ++iconv_checks;
  if (input_left != 0) return 3;
  ++iconv_checks;
  if (output_left != 2) return 3;
  ++iconv_checks;
  if ((unsigned char)output_data[0] != 0xc3 || (unsigned char)output_data[1] != 0xa9) return 3;
  ++iconv_checks;
  if (close_iconv(descriptor) != 0) return 3;
  ++iconv_checks;
  printf("{\"schemaVersion\":1,\"mode\":\"%ls\",\"libraryPathMatched\":true,"
         "\"markersPresent\":%s,\"libraries\":{\"libcharset-1.dll\":{\"apiChecks\":%d},"
         "\"libiconv-2.dll\":{\"apiChecks\":%d}}}\n", argv[3], modified ? "true" : "false", charset_checks, iconv_checks);
  FreeLibrary(iconv); FreeLibrary(charset); return 0;
}
