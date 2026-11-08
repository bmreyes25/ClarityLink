cmake_minimum_required(VERSION 3.20)
project(claritylink_native_info_test C)

enable_testing()

if(APPLE)
  add_executable(test_info_augmentation
    test_info_augmentation.c
    ../../../src/claritylink-jmcs/native/info_augmentation.c)
  target_compile_options(test_info_augmentation PRIVATE
    -Wall -Wextra -Werror -UNDEBUG -std=c11)
  target_link_libraries(test_info_augmentation PRIVATE
    "-framework CoreFoundation")
  add_test(NAME native_info_augmentation COMMAND test_info_augmentation)
else()
  add_test(NAME native_info_augmentation_requires_host_cf
    COMMAND ${CMAKE_COMMAND} -E echo "SKIP: host CoreFoundation harness requires macOS")
  set_tests_properties(native_info_augmentation_requires_host_cf PROPERTIES
    SKIP_REGULAR_EXPRESSION "SKIP: host CoreFoundation")
endif()
