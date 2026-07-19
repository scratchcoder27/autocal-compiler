from token_types import TokenType


class Token:
    def __init__(self, type: TokenType, lexeme: str, literal: object, line_no: int, file_no : int):
        self.type = type
        self.lexeme = lexeme
        self.literal = literal
        self.line_no = line_no
        self.file_no = file_no

    def __str__(self):
        return f"[{str(self.type).replace("TokenType.", "")} ('{self.lexeme if ("\n" not in self.lexeme) else '<newline>'}')]"
