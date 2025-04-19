/*
  tqdm.h
  - header file for tqdm library's implementation in c
  - functions & logic implementation are similar to that of ``tqdm`` by TinyGrad
  url: https://github.com/tinygrad/tinygrad/blob/master/tinygrad/helpers.py
  - for compilation:
    -- ".so": g++ -shared -fPIC -o libtqdm.so tqdm.cpp / for linux
    -- ".dll": g++ -shared -o libtqdm.dll tqdm.cpp / for windows
*/

#ifndef __TQDM__H__
#define __TQDM__H__

#include <stdbool.h>
#include <stddef.h>
#include <time.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  const char* desc;       // description (e.g. "Loading...")
  bool disable;           // progress bar is disabled or not?
  const char* unit;       // unit of measurement (iters/sec or sec/iters)
  bool unit_scale;        // scale the units or not (K/M/G/T, etc)?
  int total;              // total iters
  int current;            // current step/iters
  int skip;               // skipping steps
  double start_time;      // start time in secs
  int rate;               // rate of updation in hertz
} tqdm;   // struct that represents the progress bar

typedef struct {
  int id;            // Unique ID for the cached object
  int count;         // Reference count
  bool visited;      // Flag to indicate whether the object is being visited
} PrettyCacheEntry;

void init_tqdm(tqdm* bar, const char* desc, bool disable, const char* unit, bool unit_scale, int total, int rate);
void update_tqdm(tqdm* bar, int increments, bool close);
void print_tqdm(tqdm* bar, bool close);
void HMS(double seconds, char* output, size_t buffer_size);
void SI(double value, char* output, size_t buffer_size);
void close_tqdm(tqdm* bar);

void init_trange(tqdm* bar, int n, const char* desc, bool disable, const char* unit, bool unit_scale, int rate);
char* pretty_print(
  void* x,
  char* (*rep)(void*),
  void** (*srcfn)(void*),
  PrettyCacheEntry* cache,
  size_t cache_size,
  int depth
);
void dfs(void* x, PrettyCacheEntry* cache, size_t cache_size, void** (*srcfn)(void*));

static double get_time() {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec + ts.tv_nsec * 1e-9;
}

void HMS(double seconds, char* output, size_t buffer_size) {
  int hrs = (int)seconds / 3600;
  int mins = ((int)seconds % 3600) / 60;
  int secs = (int)seconds % 60;
  snprintf(output, buffer_size, "%02d:%02d:%02d", hrs, mins, secs);
}

void SI(double value, char* output, size_t buffer_size) {
  const char* units = " kMGTPEZY";
  int idx = 0;
  while (value >= 1000.0 && idx < 8) {
    value /= 1000.0;
    idx++;
  }
  snprintf(output, buffer_size, "%.2f%c", value, units[idx]);
}

void init_tqdm(tqdm* bar, const char* desc, bool disable, const char* unit, bool unit_scale, int total, int rate) {
  if (!bar) return;
  bar->desc = desc;
  bar->disable = disable;
  bar->unit = unit;
  bar->unit_scale = unit_scale;
  bar->total = total > 0 ? total : 0;
  bar->current = 0;
  bar->skip = 1;
  bar->rate = rate > 0 ? rate : 1;
  bar->start_time = get_time();
}

void print_tqdm(tqdm* bar, bool close) {
  if (!bar || bar->disable) return;

  double elapsed = get_time() - bar->start_time;
  double progress = (bar->total > 0) ? (double)bar->current / bar->total : 0.0;
  char elapsed_text[16], remaining_text[16], rate_text[16];

  HMS(elapsed, elapsed_text, sizeof(elapsed_text));
  if (bar->total > 0 && bar->current > 0) {
    double remaining = elapsed / progress - elapsed;
    HMS(remaining, remaining_text, sizeof(remaining_text));
  } else {
    snprintf(remaining_text, sizeof(remaining_text), "?");
  }

  if (bar->current > 0) {
    double rate = (double)bar->current / elapsed;
    if (bar->unit_scale) {
      SI(rate, rate_text, sizeof(rate_text));
    } else {
      snprintf(rate_text, sizeof(rate_text), "%.2f", rate);
    }
  } else {
    snprintf(rate_text, sizeof(rate_text), "?");
  }

  int bar_width = 20;
  int filled = (int)(bar_width * progress);
  char progress_bar[bar_width + 1];
  memset(progress_bar, '=', filled);
  memset(progress_bar + filled, '-', bar_width - filled);
  progress_bar[bar_width] = '\0';

  printf("\r%s [%s] %.1f%% %d/%d [%s<%s, %s%s/s]", bar->desc, progress_bar, progress * 100, bar->current, bar->total, elapsed_text, remaining_text, rate_text, bar->unit);
  if (close) {
    printf("\n");
  }
}

void close_tqdm(tqdm* bar) {
  if (bar) {
    bar->disable = true;
  }
}

void update_tqdm(tqdm* bar, int increments, bool close) {
  if (!bar || bar->disable) return;
  bar->current += increments;
  if (bar->current > bar->total) {
    bar->current = bar->total;
  }
  print_tqdm(bar, close);
}

void dfs(void* x, PrettyCacheEntry* cache, size_t cache_size, void** (*srcfn)(void*)) {
  if (!x || !cache || !srcfn) return;

  for (void** srcs = srcfn(x); srcs && *srcs; ++srcs) {
    PrettyCacheEntry* entry = &cache[(size_t)*srcs % cache_size];
    if (++entry->count == 1) {
      dfs(*srcs, cache, cache_size, srcfn);
    }
  }
}

void init_trange(tqdm* bar, int n, const char* desc, bool disable, const char* unit, bool unit_scale, int rate) {
  init_tqdm(bar, desc, disable, unit, unit_scale, n, rate);
}

char* pretty_print(void* x, char* (*rep)(void*), void** (*srcfn)(void*), PrettyCacheEntry* cache, size_t cache_size, int depth) {
  if (!x || !rep || !srcfn || !cache) return NULL;

  size_t index = (size_t)x % cache_size;
  PrettyCacheEntry* entry = &cache[index];

  if (!entry->visited) {
    entry->visited = true;
    entry->id = (int)index;
  }

  if (entry->count++ > 0) {
    char* visited_buffer = (char*)malloc(128);
    if (!visited_buffer) return NULL;
    snprintf(visited_buffer, 128, "%*s<visited x%d>", depth * 2, "", entry->id);
    return visited_buffer;
  }

  char* rep_str = rep(x);
  if (!rep_str) return NULL;

  char* result_buffer = (char*)malloc(1024);
  if (!result_buffer) return NULL;

  snprintf(result_buffer, 1024, "%*s x%d: %s", depth * 2, "", entry->id, rep_str);

  for (void** srcs = srcfn(x); srcs && *srcs; ++srcs) {
    char* child_str = pretty_print(*srcs, rep, srcfn, cache, cache_size, depth + 1);
    if (child_str) {
      strncat(result_buffer, "\n", 1024 - strlen(result_buffer) - 1);
      strncat(result_buffer, child_str, 1024 - strlen(result_buffer) - 1);
      free(child_str);
    }
  }
  return result_buffer;
}

#ifdef __cplusplus
}
#endif

#endif
