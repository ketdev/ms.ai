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

# Flags, Libraries and Includes
CFLAGS      := -Wall
LIBS 		:= -lws2_32 -lgdi32 
INCLUDE     := -I$(SRCDIR)


$(BINDIR)/$(TARGET): $(OBJECTS)
	@$(CC) $(OBJECTS) $(LIBS) -o $@
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
