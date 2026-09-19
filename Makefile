# Compiler
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Iinclude -pthread -g
TEST_FLAGS = -lgtest -lgtest_main -pthread

# Directories
SRC_DIR = src
TEST_DIR = tests
BUILD_DIR = build

# App files
APP_SRCS = $(wildcard $(SRC_DIR)/*.cpp)
APP_OBJS = $(patsubst $(SRC_DIR)/%.cpp,$(BUILD_DIR)/%.o,$(APP_SRCS))
TARGET = $(BUILD_DIR)/app

# Test files
# Exclude src/main.cpp from tests because gtest_main provides main()
LIB_SRCS = $(filter-out $(SRC_DIR)/main.cpp,$(APP_SRCS))
LIB_OBJS = $(patsubst $(SRC_DIR)/%.cpp,$(BUILD_DIR)/%.o,$(LIB_SRCS))

TEST_SRCS = $(wildcard $(TEST_DIR)/*.cpp)
TEST_OBJS = $(patsubst $(TEST_DIR)/%.cpp,$(BUILD_DIR)/%.test.o,$(TEST_SRCS))
TEST_TARGET = $(BUILD_DIR)/tests

# Default target
all: $(TARGET)

# Link app
$(TARGET): $(APP_OBJS)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(APP_OBJS) -o $(TARGET) -pthread

# Compile src/*.cpp
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Compile tests/*.cpp
$(BUILD_DIR)/%.test.o: $(TEST_DIR)/%.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Link tests
$(TEST_TARGET): $(LIB_OBJS) $(TEST_OBJS)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(LIB_OBJS) $(TEST_OBJS) $(TEST_FLAGS) -o $(TEST_TARGET)

# Run tests
test: $(TEST_TARGET)
	./$(TEST_TARGET)

# Clean
clean:
	rm -rf $(BUILD_DIR)

# Run app
run: all
	./$(TARGET)