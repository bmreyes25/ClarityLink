#include "../platform/android/opaque_handle_allocator.hpp"

#include <algorithm>
#include <atomic>
#include <iostream>
#include <limits>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

using namespace claritylink::android;
void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }

int main() {
  try {
    OpaqueHandleAllocator ids;
    OpaqueHandleTable<int> table(ids);
    constexpr int kThreads = 8, kPerThread = 250;
    std::mutex output_mutex;
    std::vector<int64_t> handles;
    std::vector<std::thread> workers;
    for (int t = 0; t < kThreads; ++t) workers.emplace_back([&, t] {
      std::vector<int64_t> local;
      for (int i = 0; i < kPerThread; ++i)
        local.push_back(table.insert(std::make_shared<int>(t * kPerThread + i)));
      std::lock_guard<std::mutex> lock(output_mutex);
      handles.insert(handles.end(), local.begin(), local.end());
    });
    for (auto& worker : workers) worker.join();
    std::sort(handles.begin(), handles.end());
    require(handles.size() == static_cast<size_t>(kThreads * kPerThread), "wrong concurrent allocation count");
    require(std::adjacent_find(handles.begin(), handles.end()) == handles.end(), "concurrent handles collided");
    require(table.size() == handles.size(), "registry size mismatch");
    const int64_t stale = handles.at(100);
    auto retained = table.erase(stale);
    require(retained && *retained >= 0 && !table.get(stale), "erase did not invalidate stale handle");
    require(!table.erase(stale), "double release was not rejected");
    const int64_t replacement = table.insert(std::make_shared<int>(42));
    require(replacement > handles.back() && replacement != stale && !table.get(stale), "stale handle ABA reuse");
    require(*retained >= 0, "in-flight shared owner invalidated by registry erase");
    for (int64_t handle : handles) table.erase(handle);
    table.erase(replacement);
    require(table.size() == 0, "registry retained entries after release");
    require(!table.get(-1) && !table.erase(-1), "negative handle accepted");

    const int64_t racing_id = table.insert(std::make_shared<int>(99));
    std::atomic<bool> reader_started{false};
    std::atomic<bool> reader_safe{true};
    std::thread reader([&] {
      reader_started.store(true, std::memory_order_release);
      for (int i = 0; i < 10000; ++i) {
        auto value = table.get(racing_id);
        if (value && *value != 99) reader_safe.store(false, std::memory_order_relaxed);
      }
    });
    while (!reader_started.load(std::memory_order_acquire)) std::this_thread::yield();
    auto racing_owner = table.erase(racing_id);
    reader.join();
    require(reader_safe.load() && racing_owner && *racing_owner == 99 && !table.get(racing_id),
            "close racing with lookup lost owner safety");

    OpaqueHandleAllocator near_limit(static_cast<uint64_t>(std::numeric_limits<int64_t>::max()));
    require(near_limit.allocate() == std::numeric_limits<int64_t>::max(), "last positive JNI ID unavailable");
    bool exhausted = false; try { (void)near_limit.allocate(); } catch (const std::overflow_error&) { exhausted = true; }
    require(exhausted, "handle exhaustion did not fail closed");
    std::cout << "R7C1_HANDLE_TABLE_PASS threads=8 allocations=2000 stale_aba=REJECTED concurrent_release=PASS\n";
  } catch (const std::exception& e) {
    std::cerr << "R7C1_HANDLE_TABLE_FAIL " << e.what() << "\n"; return 1;
  }
  return 0;
}
