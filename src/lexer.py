from token_types import *
from tokens import Token
import os

class LexingError(Exception):
    def __init__(self, message: str, line_no: int = None, file_no: int = None):
        self.line_no = line_no
        self.file_no = file_no

        super().__init__(message)

class Lexer:
    def __init__(self, source: str, parsed_files: list[str] = None, file_no: int = 0, file_path: str = None) -> None:
        self.source: str = source
        self.tokens: list[Token] = []

        self.parsed_files: list[str] = parsed_files if parsed_files is not None else []
        self.file_no: int = file_no

        self.file_path: str | None = file_path

        self.start: int = 0
        self.current: int = 0
        self.line: int = 1

        self.current_indent: int = 0
        self.in_bracket: list[int, int] = [0, 0]  # parentheses, square brackets

        self.use_scoping_braces: bool = False

        # MARK: KEYWORD MAP
        self.keyword_map: dict[str, TokenType] = {
            "int": TokenType.TYPE_INT,
            "float": TokenType.TYPE_FLOAT,
            "str": TokenType.TYPE_STRING,
            "list": TokenType.TYPE_ARRAY,

            "var": TokenType.VAR,
            "def": TokenType.DEF,
            "if": TokenType.IF,
            "else": TokenType.ELSE,

            "do": TokenType.DO,
            "while": TokenType.WHILE,
            "for": TokenType.FOR,
            "break": TokenType.BREAK,
            "continue": TokenType.CONTINUE,            
            "return": TokenType.RETURN,

            "set_splitter" : TokenType.SET_SPLITTER,
            "split" : TokenType.SPLIT,
            "splitlen" : TokenType.SPLITCOUNT,

            "push" : TokenType.PUSH,
            "pop" : TokenType.POP,
            "peek": TokenType.PEEK,

            "len" : TokenType.LENGTH,
            "worldtime": TokenType.WORLDTIME,

            "round": TokenType.ROUND,
            "ceil": TokenType.CEIL,
            "floor": TokenType.FLOOR,

            "toStr" : TokenType.STRING_CAST,
            "toFloat": TokenType.FLOAT_CAST,
            "toInt": TokenType.INT_CAST,

            "poll": TokenType.POLL,
            "listen": TokenType.LISTEN,
            "send": TokenType.SEND,

            "shutdown": TokenType.SHUTDOWN,
            "endtick": TokenType.ENDTICK,

            "not": TokenType.LOGICAL_NOT,
            "and": TokenType.LOGICAL_AND,
            "or": TokenType.LOGICAL_OR,

            "null": TokenType.NULL
        }

    # MARK: IMPORTS / FILE MANAGEMENT
    def paste_code(self, location: str) -> None:
        if self.file_path:
            base_dir = os.path.dirname(self.file_path)
            resolved = os.path.normpath(os.path.join(base_dir, location))
        else:
            resolved = location

        if resolved in self.parsed_files:
            raise LexingError(f"Recursive/Cyclic imports for {resolved}", line_no=self.line, file_no=self.file_no)
        self.parsed_files.append(resolved)

        try:
            with open(resolved, 'r') as f:
                data = f.read()
                tokeniser = Lexer(
                    data,
                    self.parsed_files,
                    len(self.parsed_files) - 1,
                    file_path=resolved,
                )
                new_tokens = tokeniser.scan_tokens()
                new_tokens.pop()  # Remove EOF

                self.tokens += new_tokens
        except (OSError, LexingError) as e:
            if isinstance(e, OSError):
                raise LexingError(f"File {resolved} could not be opened.", line_no=self.line, file_no=self.file_no)
            else:
                raise e

    # MARK: PRAGMAS
    def handle_pragma(self, directive: str) -> None:
        parts = directive.split()

        if len(parts) != 2 or parts[1] not in ("true", "false"):
            raise LexingError(
                f"#pragma useScopingBraces expects 'true' or 'false' (line {self.line})",
                line_no=self.line, file_no=self.file_no
            )
        self.use_scoping_braces = parts[1] == "true"

    # MARK: SCANNING
    def scan_tokens(self) -> list[Token]:
        while not self.is_at_end():
            self.start = self.current
            self.scan_token()

        self.tokens.append(Token(TokenType.NEWLINE, "", None, self.line, self.file_no))
        for i in range(self.current_indent):
            self.tokens.append(Token(TokenType.DEDENT, "", None, self.line, self.file_no))
        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.file_no))
        return self.tokens

    def scan_token(self) -> None:
        c = self.advance()

        match c:
            case "(":
                self.add_token(TokenType.LEFT_PAREN)
                self.in_bracket[0] += 1
            case ")":
                self.add_token(TokenType.RIGHT_PAREN)
                self.in_bracket[0] -= 1
            case "[":
                self.add_token(TokenType.LEFT_SQUARE_BRACKET)
                self.in_bracket[1] +=  1
            case "]":
                self.add_token(TokenType.RIGHT_SQUARE_BRACKET)
                self.in_bracket[1] -= 1
            case "{":
                if self.use_scoping_braces:
                    self.tokens.append(Token(TokenType.COLON, ':', None, self.line, self.file_no))
                    self.tokens.append(Token(TokenType.NEWLINE, '', None, self.line, self.file_no))
                    self.current_indent += 1
                    self.tokens.append(Token(TokenType.INDENT, '', None, self.line, self.file_no))
                else:
                    self.add_token(TokenType.BRACE_LEFT) # these aren't used in the code itself, only for managing indents
            case "}":
                if self.use_scoping_braces:
                    if self.current_indent == 0:
                        raise LexingError(
                            f"Unexpected '}}': no matching scope to close (line {self.line})",
                            line_no=self.line, file_no=self.file_no
                        )
                    self.tokens.append(Token(TokenType.NEWLINE, '', None, self.line, self.file_no))
                    self.current_indent -= 1
                    self.tokens.append(Token(TokenType.DEDENT, '', None, self.line, self.file_no))
                else:
                    self.add_token(TokenType.BRACE_RIGHT)
            case ",":
                self.add_token(TokenType.COMMA)
            case ";":
                self.add_token(TokenType.SEMICOLON)
            case ".":
                self.add_token(TokenType.DOT)
            case "?":
                self.add_token(TokenType.QUESTION_MARK)
            case "#":
                self.add_token(TokenType.PREPROCESS)
            case "\\":
                self.add_token(TokenType.BACKSLASH)
            case "+":
                if self.match_char("+"):
                    self.add_token(TokenType.INCREMENT)
                elif self.match_char("="):
                    self.add_token(TokenType.PLUS_EQUALS)
                else:
                    self.add_token(TokenType.PLUS)
            case "*":
                self.add_token(
                    TokenType.STAR_EQUALS if self.match_char("=") else TokenType.STAR
                )
            case "~":
                self.add_token(TokenType.TILDE)
            case ":":
                self.add_token(TokenType.COLON)
            case "%":
                self.add_token(
                    TokenType.PERCENT_EQUALS if self.match_char("=") else TokenType.PERCENT
                )

            case "&":
                self.add_token(
                    TokenType.AND_EQUALS if self.match_char("=") else TokenType.BITWISE_AND
                )
            case "|":
                self.add_token(
                    TokenType.OR_EQUALS if self.match_char("=") else TokenType.BITWISE_OR
                )
            case "^":
                self.add_token(
                    TokenType.XOR_EQUALS if self.match_char("=") else TokenType.BITWISE_XOR
                )

            # two character tokens
            case "!":
                self.add_token(
                    TokenType.BANG_EQUAL if self.match_char("=") else TokenType.BANG
                )

            case "=":
                self.add_token(
                    TokenType.EQUAL_EQUAL if self.match_char("=") else TokenType.EQUAL
                )

            case "<":
                if self.match_char("<"):
                    self.add_token(
                        TokenType.LSH_EQUALS if self.match_char("=") else TokenType.LEFTSHIFT
                    )
                elif self.match_char("="):
                    self.add_token(TokenType.LESS_EQUAL)
                else:
                    self.add_token(TokenType.LESS)

            case ">":
                if self.match_char(">"):
                    self.add_token(
                        TokenType.RSH_EQUALS if self.match_char("=") else TokenType.RIGHTSHIFT
                    )
                elif self.match_char("="):
                    self.add_token(TokenType.GREATER_EQUAL)
                else:
                    self.add_token(TokenType.GREATER)


            case "-":
                if self.match_char(">"):
                    self.add_token(TokenType.ARROW)
                elif self.match_char("-"):
                    self.add_token(TokenType.DECREMENT)
                elif self.match_char("="):
                    self.add_token(TokenType.MINUS_EQUALS)
                else:
                    self.add_token(TokenType.MINUS)
            
            # slash and comments
            case '/':
                if (self.match_char('/')):
                    # A comment goes until the end of the line.
                    while (self.peek() != '\n' and  not self.is_at_end()):
                        self.advance()
                elif self.match_char('='):
                    self.add_token(TokenType.SLASH_EQUALS)
                else:
                    self.add_token(TokenType.SLASH)

            # special tokens
            case '\r' | '\t' | ' ' | '\t':
                pass
            

            case '\\':
                if self.peek() == '\n':
                    self.advance()
                    self.line += 1
                else:
                    raise LexingError(f"Unexpected character: '\\' in line {self.line}", line_no=self.line, file_no=self.file_no)

            case '\n':
                self.line += 1
                
                if not self.in_bracket[0] and not self.in_bracket[1]:
                    if not self.peek() == "\n":
                        self.add_token(TokenType.NEWLINE)
                        if not self.use_scoping_braces:
                            spaces = 0
                            while self.peek_next(spaces) in {" ", "\t"}:
                                spaces += 1
                            if not self.peek_next(spaces) == "\n":
                                self.handle_indentation()

            # strings            
            case '"':
                self.string()

            case _:
                if c.isdigit():
                    self.number()
                elif c.isalpha() or (c == '_'):
                    self.identifier()
                else:
                    raise LexingError(f"Unexpected character: '{c}' in line {self.line}", line_no=self.line, file_no=self.file_no)

    def add_token(self, type: TokenType, literal: object = None) -> None:
        text = self.source[self.start : self.current]
        self.tokens.append(Token(type, text, literal, self.line, self.file_no))
    
    # MARK: INDENTATION
    def handle_indentation(self) -> None:
        di = 0
        while (char := self.peek()) in (' ', '\t'):
            if char == ' ':
                di += 1
            elif char == '\t':
                di += 4  # Assuming a tab is equal to 4 spaces
            self.advance()
        
        if di % 4 == 0:
            indent_level = di // 4
            if indent_level > self.current_indent:
                if len(self.tokens) < 2 or self.tokens[-2].type is not TokenType.COLON:
                    newline_tok = self.tokens.pop()
                    self.tokens.append(Token(TokenType.COLON, ':', None, self.line, self.file_no))
                    self.tokens.append(newline_tok)
                for _ in range(indent_level - self.current_indent):
                    self.add_token(TokenType.INDENT, '')
            elif indent_level < self.current_indent:
                for _ in range(self.current_indent - indent_level):
                    self.add_token(TokenType.DEDENT, '')
            self.current_indent = indent_level
        else:
            raise LexingError(f"Indentation error: Indentation must be a multiple of 4 spaces (line {self.line})", line_no=self.line, file_no=self.file_no)
    
    # MARK: IDENTIFIERS
    def identifier(self) -> None:
        while self.peek().isalnum() or self.peek() == '_':
            self.advance()
        
        text = self.source[self.start : self.current]
        if text in self.keyword_map:
            token_type = self.keyword_map.get(text)
        else:
            if text == "include":
                if self.tokens[-1].type is TokenType.PREPROCESS:
                    self.tokens.pop()
                    loc = ""
                    while (not self.is_at_end()) and self.peek() != "\n":
                        loc += self.advance()
                    if self.peek() == "\n":
                        self.advance()
                        self.line += 1
                    loc = loc.strip()
                    if loc.startswith('<') and loc.endswith('>'):
                        module_name = loc[1:-1].strip()
                        compiler_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        loc = os.path.join(compiler_dir, "stdlib", f"{module_name}.autoc")

                    else:
                        loc = loc.replace("\"", "")
                    self.paste_code(loc)
                    return
                
            elif text == "pragma":
                if self.tokens[-1].type is TokenType.PREPROCESS:
                    peek_pos = self.current
                    while peek_pos < len(self.source) and self.source[peek_pos] in (' ', '\t'):
                        peek_pos += 1
                    word_start = peek_pos
                    while peek_pos < len(self.source) and (self.source[peek_pos].isalnum() or self.source[peek_pos] == '_'):
                        peek_pos += 1
                    pragma_name = self.source[word_start:peek_pos]

                    if pragma_name == "useScopingBraces":
                        self.tokens.pop()
                        directive = ""
                        while (not self.is_at_end()) and self.peek() != "\n":
                            directive += self.advance()
                        if self.peek() == "\n":
                            self.advance()
                            self.line += 1
                        self.handle_pragma(directive.strip())
                        return
            token_type = TokenType.IDENTIFIER
        self.add_token(token_type)

    # MARK: NUMBERS
    def number(self) -> None:
        is_float = False
        
        if self.source[self.start] == '0':
            if self.peek() in 'xX':
                # Hex number
                self.advance()
                while self.peek() in '0123456789abcdefABCDEF':
                    self.advance()
                value = int(self.source[self.start:self.current], 16)
                self.add_token(TokenType.INT, value)
                return
            
            elif self.peek() in 'bB':
                # Binary number
                self.advance()
                while self.peek() in '01':
                    self.advance()
                value = int(self.source[self.start:self.current], 2)
                self.add_token(TokenType.INT, value)
                return
        
        # Regular decimal number
        while self.peek().isdigit():
            self.advance()

        if self.peek() == "." and self.peek_next().isdigit():
            is_float = True
            self.advance()

            while self.peek().isdigit():
                self.advance()
        
        if is_float:
            value = float(self.source[self.start : self.current])
            self.add_token(TokenType.FLOAT, value)
        else:
            value = int(self.source[self.start : self.current])
            self.add_token(TokenType.INT, value)

    
    # MARK: STRINGS
    def string(self) -> None:
        while self.peek() != '"' and not self.is_at_end() and not self.peek() == '\n':
            self.advance()

        if self.is_at_end():
            raise LexingError(f"Unterminated string at line {self.line}", line_no=self.line, file_no=self.file_no)

        # The closing quote
        self.advance()

        # Trim the surrounding quotes
        value = self.source[self.start + 1 : self.current - 1]
        value = self.escape_string(value)
        self.add_token(TokenType.STRING, value)
    
    def escape_string(self, value: str) -> str:
        result = []
        i = 0
        while i < len(value):
            if value[i] == '\\' and i + 1 < len(value):
                next_char = value[i + 1]
                escape_map = {
                    'n': '\n',
                    't': '\t',
                    'r': '\r',
                    'b': '\b',
                    'f': '\f',
                    'v': '\v',
                    '0': '\0',
                    '\\': '\\',
                    '"': '"',
                    "'": "'",
                }
                if next_char in escape_map:
                    result.append(escape_map[next_char])
                    i += 2
                else:
                    # Unknown escape sequence, keep the backslash
                    result.append(value[i])
                    i += 1
            else:
                result.append(value[i])
                i += 1
        return ''.join(result)

    # MARK: HELPERS
    def advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        return char

    def match_char(self, expected: str) -> bool:
        if self.is_at_end():
            return False
        if self.source[self.current] != expected:
            return False

        self.current += 1
        return True

    def is_at_end(self) -> bool:
        return self.current >= len(self.source)
    
    def peek(self) -> str:
        if self.is_at_end():
            return "\0"
        return self.source[self.current]

    def peek_next(self, num = 1) -> str:
        if self.current + num >= len(self.source):
            return "\0"
        return self.source[self.current + num]