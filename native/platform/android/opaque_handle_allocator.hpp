#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <vector>

namespace claritylink::android {

// Process-lifetime, monotonic JNI ID allocator. IDs are never recycled, so a
// stale Java long can never alias a later live receiver or surface.
class OpaqueHandleAllocator final {
 public:
  explicit OpaqueHandleAllocator(uint64_t first = 1) noexcept : next_(first) {}

  int64_t allocate() {
    uint64_t current = next_.load(std::memory_order_relaxed);
    for (;;) {
      if (current == 0 || current > static_cast<uint64_t>(std::numeric_limits<int64_t>::max()))
        throw std::overflow_error("native handle space exhausted");
      if (next_.compare_exchange_weak(current, current + 1,
                                      std::memory_order_relaxed,
                                      std::memory_order_relaxed))
        return static_cast<int64_t>(current);
    }
  }

 private:
  std::atomic<uint64_t> next_;
};

template <typename T>
class OpaqueHandleTable final {
 public:
  explicit OpaqueHandleTable(OpaqueHandleAllocator& allocator) : allocator_(allocator) {}
  OpaqueHandleTable(const OpaqueHandleTable&) = delete;
  OpaqueHandleTable& operator=(const OpaqueHandleTable&) = delete;

  int64_t insert(std::shared_ptr<T> value) {
    if (!value) throw std::invalid_argument("cannot register null native owner");
    const int64_t id = allocator_.allocate();
    std::lock_guard<std::mutex> lock(mutex_);
    const bool inserted = entries_.emplace(id, std::move(value)).second;
    if (!inserted) throw std::logic_error("monotonic native handle collision");
    return id;
  }

  std::shared_ptr<T> get(int64_t id) const {
    if (id <= 0) return {};
    std::lock_guard<std::mutex> lock(mutex_);
    const auto found = entries_.find(id);
    return found == entries_.end() ? std::shared_ptr<T>{} : found->second;
  }

  std::shared_ptr<T> erase(int64_t id) {
    if (id <= 0) return {};
    std::lock_guard<std::mutex> lock(mutex_);
    const auto found = entries_.find(id);
    if (found == entries_.end()) return {};
    auto value = std::move(found->second);
    entries_.erase(found);
    return value;
  }

  size_t size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return entries_.size();
  }

  std::vector<std::shared_ptr<T>> values_snapshot() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::shared_ptr<T>> values;
    values.reserve(entries_.size());
    for (const auto& entry : entries_) values.push_back(entry.second);
    return values;
  }

 private:
  OpaqueHandleAllocator& allocator_;
  mutable std::mutex mutex_;
  std::map<int64_t, std::shared_ptr<T>> entries_;
};

}  // namespace claritylink::android
