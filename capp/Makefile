# Compiler and Linker
CC          := g++

# The Target Binary Program
TARGET      := capture

# The Directories, Source, Includes, Objects and Resources
SRCDIR      := .
OBJDIR      := obj
BINDIR      := .

SOURCES     := $(wildcard $(SRCDIR)/*.cpp)
OBJECTS     := $(SOURCES:$(SRCDIR)/%.cpp=$(OBJDIR)/%.o)

# OpenCV paths and flags
OPENCV_INCLUDE := -IC:/opencv/build/include
OPENCV_LIBDIR  := -L./lib
OPENCV_LIBS    := -lopencv_world480

# Flags, Libraries and Includes
CFLAGS      := -Wall -O3 -march=native -flto
LIBDIRS		:= $(OPENCV_LIBDIR)
LIBS 		:= -flto -lws2_32 -lGdi32 -luser32 $(OPENCV_LIBS) 
INCLUDE     := -I$(SRCDIR) $(OPENCV_INCLUDE)


$(BINDIR)/$(TARGET): $(OBJECTS)
	@$(CC) $(LIBDIRS) $(OBJECTS) $(LIBS) -o $@
	@echo "Linking complete!"

$(OBJECTS): $(OBJDIR)/%.o : $(SRCDIR)/%.cpp
	@$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@ 
	@echo "Compiled "$<" successfully!"

.PHONY: clean
clean:
	@echo "Cleaning..."
	@echo "$(OBJDIR)/*.o"
	@rm -rf $(OBJDIR)/*.o $(BINDIR)/$(TARGET)
	@echo "Cleaning done!"