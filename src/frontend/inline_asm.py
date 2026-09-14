from token_types import TokenType
from tokens import Token


class InlineAsmError(Exception):
    def __init__(self, message: str, line_no: int = None, file_no: int = None):
        self.line_no = line_no
        self.file_no = file_no
        super().__init__(message)


class AssemblyBlock:
    def __init__(self, lines: list[str], substitutions: dict[str, str], line_no: int, file_no: int):
        self.lines = lines
        self.substitutions = substitutions
        self.line_no = line_no
        self.file_no = file_no

    def __repr__(self):
        return f"AssemblyBlock(lines={self.lines!r}, substitutions={self.substitutions!r})"


# Tokens that shouldn't get a space inserted after/before them when we
# flatten a line's tokens back into raw asm text, so `<< x >>` renders
# as the placeholder syntax `<<x>>` instead.
_NO_SPACE_AFTER = {TokenType.LEFTSHIFT} #idk why tuples arent working
_NO_SPACE_BEFORE = {TokenType.RIGHTSHIFT}


def _render_asm_line(tokens: list[Token]) -> str:
    parts = []
    for i, tok in enumerate(tokens):
        if i == 0:
            parts.append(tok.lexeme)
            continue
        prev = tokens[i - 1]
        if prev.type in _NO_SPACE_AFTER or tok.type in _NO_SPACE_BEFORE:
            parts.append(tok.lexeme)
        else:
            parts.append(" " + tok.lexeme)
    return "".join(parts)


def fix_inline_asm(input_code: list[Token]) -> list[Token]:
    output_code: list[Token] = []
    idx = 0

    def expect(token_type: TokenType, message: str) -> Token:
        nonlocal idx
        tok = input_code[idx]
        if tok.type is not token_type:
            raise InlineAsmError(message, tok.line_no, tok.file_no)
        idx += 1
        return tok

    while True:
        tok = input_code[idx]

        if tok.type is TokenType.EOF:
            output_code.append(tok)
            break

        if tok.type is TokenType.IDENTIFIER and tok.lexeme == "__asm__":
            asm_line, asm_file = tok.line_no, tok.file_no
            idx += 1

            expect(TokenType.COLON, "Assembly Error: Missing colon after `__asm__`")
            expect(TokenType.NEWLINE, "Assembly Error: Missing newline after `__asm__:`")
            expect(TokenType.INDENT, "Assembly Error: Missing indent after `__asm__:`")

            lines: list[str] = []
            current_line: list[Token] = []

            while input_code[idx].type is not TokenType.DEDENT:
                if input_code[idx].type is TokenType.EOF:
                    raise InlineAsmError(
                        "Assembly Error: Reached EOF while parsing inline assembly",
                        input_code[idx].line_no, input_code[idx].file_no,
                    )

                if input_code[idx].type is TokenType.NEWLINE:
                    if current_line:
                        lines.append(_render_asm_line(current_line))
                        current_line = []
                    idx += 1
                    continue

                current_line.append(input_code[idx])
                idx += 1

            if current_line:
                lines.append(_render_asm_line(current_line))

            idx += 1  # consume DEDENT

            substitutions: dict[str, str] = {}
            if input_code[idx].type is TokenType.LEFT_SQUARE_BRACKET:
                idx += 1
                if input_code[idx].type is not TokenType.RIGHT_SQUARE_BRACKET:
                    while True:
                        key_tok = expect(TokenType.IDENTIFIER, "Assembly Error: Expected identifier as substitution key")
                        expect(TokenType.COLON, "Assembly Error: Expected ':' in substitution mapping")
                        value_tok = expect(TokenType.IDENTIFIER, "Assembly Error: Expected identifier as substitution value")
                        substitutions[key_tok.lexeme] = value_tok.lexeme

                        if input_code[idx].type is TokenType.COMMA:
                            idx += 1
                            continue
                        break
                expect(TokenType.RIGHT_SQUARE_BRACKET, "Assembly Error: Expected closing ']' in substitution mapping")

                if input_code[idx].type is TokenType.NEWLINE:
                    idx += 1

            block = AssemblyBlock(lines, substitutions, asm_line, asm_file)
            output_code.append(Token(TokenType.ASSEMBLY, "__asm__", block, asm_line, asm_file))
            continue

        output_code.append(tok)
        idx += 1

    return output_code