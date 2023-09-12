capp.exe: main.o
		gcc -o $@ $^ -L../lib -lhello
		# '-o $@'    => output file => $@ = the target file (app.exe)
		# '   $^'    => no options => Link all depended files 
		#            => $^ = main.o and other if any
		# '-L../lib' => look for libraries in directory ../lib
		# '-lhello   => use shared library hello (libhello.so or hello.dll)

%.o: %.cpp
		gcc -o $@ -c $< -I ../lib
		# '-o $@'     => output file => $@ = the target file (main.o)
		# '-c $<'     => COMPILE the first depended file (main.cpp)
		# '-I ../lib' => look for headers (*.h) in directory ../lib

clean:
        rm -f *.o *.so *.dll *.exe
