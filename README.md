A complete compiler targeting the AUTOCAL, which is a "computer" in HBMs Nuclear Tech mod

DOCS HERE: https://gist.github.com/scratchcoder27/7d35fc28921b2a89f3f537623cdaef97

# Usage:
 - Install python3 if it isn't already installed, and make sure to tick the `ADD TO PATH` option
 - Clone the repository to the directory of your choice with `git clone https://github.com/scratchcoder27/autocal-compiler.git` if git is installed, or simply download the zip and extract it
 - You can run the compiler by invoking src/main with python like so: `py src/main.py` on windows, or `python3 src/main.py` on linux systems.
 - The compiler needs the following arguments `python3 src/main.py <input_file_name> [-o <output_file_name>] [some debug options]` (more details can be shown by `python3 src/main.py --help`)

 # The language


 A program in the language, looks like this:
The autocal compiler uses a language, which is statically (locally) typed, and is procedural in nature. It uses significant whitespace for indentation by default. It has been inspired by several popular languages, including python (particularly the syntax), C, and lua.
(again, see the docs for more explanation)

```cpp
#pragma clockspeed 20

#define TEXT_PORT "control"
#include <io>

var n = 10

var n1 = 0
var n2 = 1

PRINT("Fibonacci series:")
for (var i = 0; i < n; i++):
    PRINT(n1)
    var sum = n1 + n2
    n1 = n2
    n2 = sum
```
 
