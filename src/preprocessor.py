from token_types import TokenType
from tokens import Token

class PreprocessError(Exception):
    pass

class Preprocessor:
    def __init__(self):
        self.defines: dict[tuple[str, TokenType], tuple[list[str] | None, list[Token]]] = {}
        self.preprocessed: list[Token] = []
        self.position = 0
        self.input_code: list[Token] = []
        self.options: dict[str, str] = dict()
        self.condition_stack: list[bool] = []
    
    @property
    def is_active(self) -> bool:
        return all(self.condition_stack)

    def preprocess_all(self, input_code: list[Token]) -> list[Token]:
        self.reset()
        return self.preprocess(input_code)

    def reset(self):
        self.defines = {}
        self.preprocessed = []
        self.position = 0
        self.input_code = []
        self.condition_stack = []

    def preprocess(self, input_code: list[Token]) -> list[Token]:
        self.input_code = input_code
        self.position = 0
        self.preprocessed = []

        while True:
            current = self.peek()
            
            if current.type == TokenType.EOF:
                if self.condition_stack:
                    raise PreprocessError("Unterminated conditional directive (missing #endif)")
                self.accept(current)
                break

            if current.type != TokenType.PREPROCESS:
                if not self.is_active:
                    self.advance()
                    continue

                macro_key = (current.lexeme, current.type)
                if macro_key in self.defines:
                    args, body = self.defines[macro_key]
                    
                    if args is None:
                        self.input_code = self.input_code[:self.position] + body + self.input_code[self.position + 1:]
                        continue
                    else:
                        if self.next().type == TokenType.LEFT_PAREN:
                            start_pos = self.position
                            self.advance()
                            self.advance()
                            
                            actual_args = []
                            current_arg = []
                            paren_depth = 0
                            
                            while True:
                                tok = self.peek()
                                if tok.type == TokenType.EOF:
                                    raise PreprocessError(f"Unterminated argument list for macro '{macro_key[0]}'")
                                
                                if tok.type == TokenType.LEFT_PAREN:
                                    paren_depth += 1
                                elif tok.type == TokenType.RIGHT_PAREN:
                                    if paren_depth == 0:
                                        actual_args.append(current_arg)
                                        self.advance()
                                        break
                                    paren_depth -= 1
                                elif tok.type == TokenType.COMMA and paren_depth == 0:
                                    actual_args.append(current_arg)
                                    current_arg = []
                                    self.advance()
                                    continue
                                
                                current_arg.append(tok)
                                self.advance()
                            
                            if len(args) == 0 and len(actual_args) == 1 and len(actual_args[0]) == 0:
                                actual_args = []
                                
                            if len(actual_args) != len(args):
                                raise PreprocessError(f"Macro '{macro_key[0]}' expected {len(args)} arguments, got {len(actual_args)}")
                            
                            arg_map = dict(zip(args, actual_args))
                            
                            expanded_body = []
                            for token in body:
                                if token.type == TokenType.IDENTIFIER and token.lexeme in arg_map:
                                    expanded_body.extend(arg_map[token.lexeme])
                                else:
                                    expanded_body.append(token)
                            
                            self.input_code = self.input_code[:start_pos] + expanded_body + self.input_code[self.position:]
                            self.position = start_pos
                            continue
                        else:
                            self.accept(current)
                            self.advance()
                else:
                    self.accept(current)
                    self.advance()
                continue
            
            self.advance()  # consume '#'
            directive_tok = self.advance()
            directive = directive_tok.lexeme

            if directive in {"ifdef", "ifndef", "ifequal", "endif"}:
                match directive:
                    case "ifdef":
                        name_tok = self.advance()
                        name_key = (name_tok.lexeme, name_tok.type)
                        self.condition_stack.append(name_key in self.defines if self.is_active else False)
                    case "ifndef":
                        name_tok = self.advance()
                        name_key = (name_tok.lexeme, name_tok.type)
                        self.condition_stack.append(name_key not in self.defines if self.is_active else False)
                    case "ifequal":
                        val1 = self.advance()
                        val2 = self.advance()
                        self.condition_stack.append(val1.lexeme == val2.lexeme if self.is_active else False)
                    case "endif":
                        if not self.condition_stack:
                            raise PreprocessError("Unexpected #endif without matching #if")
                        self.condition_stack.pop()
                continue

            if not self.is_active:
                while self.peek().type not in {TokenType.NEWLINE, TokenType.EOF}:
                    self.advance()
                continue
            
            match directive:
                case "define":
                    name_tok = self.advance()
                    name_key = (name_tok.lexeme, name_tok.type)
                    
                    args = None
                    if self.peek().type == TokenType.LEFT_PAREN:
                        self.advance()
                        args = []
                        if self.peek().type != TokenType.RIGHT_PAREN:
                            while True:
                                arg_token = self.advance()
                                if arg_token.type != TokenType.IDENTIFIER:
                                    raise PreprocessError("Macro arguments must be valid identifiers")
                                args.append(arg_token.lexeme)
                                
                                if self.peek().type == TokenType.COMMA:
                                    self.advance()
                                elif self.peek().type == TokenType.RIGHT_PAREN:
                                    break
                                else:
                                    raise PreprocessError("Expected ',' or ')' in macro parameter list")
                        self.advance()
                    
                    to_replace = []
                    while True:
                        val = self.advance()
                        if val.type in {TokenType.NEWLINE, TokenType.EOF}:
                            break
                        if val.type == TokenType.BACKSLASH:
                            next_tok = self.peek()
                            if next_tok.type == TokenType.NEWLINE:
                                self.advance()
                                continue
                                
                            if next_tok.lexeme == "n":
                                self.advance()
                                to_replace.append(Token(TokenType.NEWLINE, "", None, val.line_no, val.file_no))
                                
                                if self.peek().type == TokenType.NEWLINE:
                                    self.advance()
                                continue
                        
                        to_replace.append(val)
                    self.defines[name_key] = (args, to_replace)
                
                case "undef":
                    name_tok = self.advance()
                    name_key = (name_tok.lexeme, name_tok.type)
                    self.defines.pop(name_key, None)

                case "error":
                    msg_tokens = []
                    while self.peek().type not in {TokenType.NEWLINE, TokenType.EOF}:
                        msg_tokens.append(self.advance().lexeme)
                    raise PreprocessError(" ".join(msg_tokens).strip() or "Error directive encountered")
                
                case "message":
                    msg_tokens = []
                    while self.peek().type not in {TokenType.NEWLINE, TokenType.EOF}:
                        msg_tokens.append(self.advance().lexeme)
                    print(" ".join(msg_tokens).strip())
                
                case "pragma":
                    if self.peek().type is TokenType.IDENTIFIER:
                        option = self.advance().lexeme
                    else:
                        raise PreprocessError(f"Invalid pragma instruction, found {self.peek()}")
                    if self.peek().type in {TokenType.IDENTIFIER, TokenType.INT, TokenType.FLOAT}:
                        value = self.advance().lexeme
                    else:
                        raise PreprocessError(f"Invalid pragma instruction, found {self.peek()}")
                    self.options[option] = value
                    
                case _:
                    raise PreprocessError(f"Invalid preprocessor instruction: '{directive}'")
            
        return self.preprocessed

    def next(self) -> Token:
        next_position = self.position + 1
        if next_position >= len(self.input_code):
            return Token(TokenType.EOF, "", None, -1)
        return self.input_code[next_position]

    def peek(self) -> Token:
        if self.position >= len(self.input_code):
            return Token(TokenType.EOF, "", None, -1)
        return self.input_code[self.position]

    def advance(self) -> Token:
        current = self.peek()
        if self.position < len(self.input_code):
            self.position += 1
        return current

    def accept(self, token) -> None:
        self.preprocessed.append(token)