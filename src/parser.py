from __future__ import annotations
from ast_nodes import *
from stmt import *
from expr import *
from tokens import Token
from token_types import TokenType
from datatypes import Datatypes


class ParseError(Exception):
    def __init__(self, message: str, line_no: int | None = None, file_no: int | None = None):
        super().__init__(message)
        self.line_no = line_no
        self.file_no = file_no


class Parser:
    def __init__(self):
        self.tokens = []
        self.position = -1

        self.VALID_DATATYPES = {
            TokenType.TYPE_INT,
            TokenType.TYPE_FLOAT,
            TokenType.TYPE_STRING,
            TokenType.TYPE_ARRAY
        }

        self.DATATYPES = {
            TokenType.TYPE_INT : Datatypes.INT,
            TokenType.TYPE_FLOAT : Datatypes.FLOAT,
            TokenType.TYPE_STRING : Datatypes.STRING,
            TokenType.TYPE_ARRAY : Null
        }

        self.INBUILT_FUNCTIONS_ARG_1 = {
            TokenType.ROUND,
            TokenType.FLOOR,
            TokenType.CEIL,
            TokenType.STRING_CAST,
            TokenType.FLOAT_CAST,
            TokenType.INT_CAST,

            TokenType.LISTEN,
            TokenType.POLL,
            TokenType.LENGTH,

            TokenType.SPLITCOUNT
        }

        self.INBUILT_FUNCTIONS_ARG_2 = {
            TokenType.SPLIT
        }

        self.INBUILT_FUNCTIONS_ARG_0 = {
            TokenType.POP,
            TokenType.PEEK,
            TokenType.WORLDTIME
        }

        self.INBUILT_STATEMENTS = {
            TokenType.ENDTICK,
            TokenType.SHUTDOWN
        }

        self.INBUILT_PROCEDURES_ARG_1 = {
            TokenType.PUSH,
            TokenType.SET_SPLITTER
        }

        self.UNARY_OPERATORS = {
            TokenType.MINUS, TokenType.LOGICAL_NOT,
            TokenType.INCREMENT, TokenType.DECREMENT
        }

        self.BINARY_OPERATORS = {
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
            TokenType.LOGICAL_AND, TokenType.LOGICAL_OR, TokenType.EQUAL_EQUAL,
            TokenType.BANG_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER,
            TokenType.GREATER_EQUAL, TokenType.EQUAL,
            TokenType.PLUS_EQUALS, TokenType.MINUS_EQUALS, TokenType.STAR_EQUALS,
            TokenType.SLASH_EQUALS, TokenType.PERCENT_EQUALS, TokenType.AND_EQUALS,
            TokenType.OR_EQUALS, TokenType.XOR_EQUALS, TokenType.LSH_EQUALS, TokenType.RSH_EQUALS,
            TokenType.QUESTION_MARK
        }

        self.PRECEDENCE_TABLE = {
            TokenType.STAR:        60,
            TokenType.SLASH:       60,
            TokenType.PERCENT:     60,

            TokenType.PLUS:        50,
            TokenType.MINUS:       50,

            TokenType.LEFTSHIFT:   40,
            TokenType.RIGHTSHIFT:  40,

            TokenType.GREATER:       35,
            TokenType.GREATER_EQUAL: 35,
            TokenType.LESS:          35,
            TokenType.LESS_EQUAL:    35,

            TokenType.EQUAL_EQUAL:   32,
            TokenType.BANG_EQUAL:    32,

            TokenType.BITWISE_AND: 30,
            TokenType.BITWISE_XOR: 25,
            TokenType.BITWISE_OR:  20,

            TokenType.LOGICAL_AND: 15,
            TokenType.LOGICAL_OR:  10,

            TokenType.QUESTION_MARK: 5,

            TokenType.EQUAL:          1,
            TokenType.PLUS_EQUALS:    1,
            TokenType.MINUS_EQUALS:   1,
            TokenType.STAR_EQUALS:    1,
            TokenType.SLASH_EQUALS:   1,
            TokenType.PERCENT_EQUALS: 1,
            TokenType.AND_EQUALS:     1,
            TokenType.OR_EQUALS:      1,
            TokenType.XOR_EQUALS:     1,
            TokenType.LSH_EQUALS:     1,
            TokenType.RSH_EQUALS:     1
        }

    def parse(self, tokens):
        self.tokens = tokens
        return self.program()

    # MARK: PARSE

    def program(self):
        if self.peek().type == TokenType.NEWLINE:
            self.advance()
        stmts = []
        while not self.peek().type == TokenType.EOF:
            stmts.append(self.statement())
        return Program(stmts)  # Program has no location, per spec

    def parse_block_statement(self):
        loc = self.peek_loc()
        block_stmts = []
        while self.peek().type not in {TokenType.DEDENT, TokenType.EOF}:
            if self.peek().type == TokenType.NEWLINE:
                self.advance()
                continue
            block_stmts.append(self.parse_block_item())
        self.advance()
        return Block(block_stmts, location=loc)

    def parse_block_item(self):
        match self.peek().type:
            case TokenType.VAR:
                return self.variable_declaration()
            case _:
                return self.statement()

    def identifier(self):
        return self.consume(TokenType.IDENTIFIER, "Expected valid identifier")

    # MARK: statements

    def variable_declaration(self, use_semicolon=False):
        loc = self.peek_loc()
        self.advance()
        name = self.consume(
            TokenType.IDENTIFIER,
            "Expected valid Identifier in variable name declaration "
            "(Must start with letter, only alphanumeric characters or `_`)"
        )

        if self.peek().type == TokenType.COLON:
            self.advance()
            self.consume(TokenType.TYPE_INT, " as only ints are accepted yet")

        if self.peek().type == TokenType.EQUAL:
            self.advance()
            expr = self.expression()
            expr = Assign(Var(name, location=loc), expr, location=loc)
        else:
            expr = None

        if use_semicolon:
            self.consume(TokenType.SEMICOLON)
        else:
            self.consume(TokenType.NEWLINE)

        return VariableDeclaration(name, expr, location=loc)

    def statement(self):
        match self.peek().type:
            case TokenType.VAR:
                return self.variable_declaration()
            
            case TokenType.DEF:
                return self.function()

            case TokenType.RETURN:
                loc = self.peek_loc()
                self.advance()
                if self.peek().type not in {TokenType.NEWLINE, TokenType.EOF}:
                    exp = self.expression()
                else:
                    exp = None
                self.advance()
                return Return(exp, location=loc)

            case TokenType.NULL:
                loc = self.peek_loc()
                self.advance()
                return Null(None, location=loc)

            case TokenType.NEWLINE:
                pass
                loc = self.peek_loc()
                self.advance()
                return Null(None, location=loc)

            case TokenType.BREAK:
                loc = self.peek_loc()
                self.advance()
                return Break(None, location=loc)

            case TokenType.CONTINUE:
                loc = self.peek_loc()
                self.advance()
                return Continue(None, location=loc)

            case TokenType.FOR:
                loc = self.peek_loc()
                self.advance()

                self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses in for statement")

                if self.peek().type == TokenType.VAR:
                    init_expr = self.variable_declaration(True)
                else:
                    init_expr = self.expression()
                    self.consume(TokenType.SEMICOLON)

                test_expr = self.expression()
                self.consume(TokenType.SEMICOLON)

                update_expr = self.expression()
                self.consume(TokenType.RIGHT_PAREN, "Expected closing parentheses in for statement")

                self.consume(TokenType.COLON)
                for_body = self.parse_block_or_stmt()

                return Block(
                    [
                        init_expr,
                        While(
                            test_expr,
                            Block([for_body, update_expr], location=loc),
                            None,
                            location=loc,
                        )
                    ],
                    location=loc,
                )

            case TokenType.WHILE:
                loc = self.peek_loc()
                self.advance()
                test = self.expression()
                self.consume(TokenType.COLON, "Expected ':' after while condition")
                body = self.parse_block_or_stmt()
                return While(test, body, None, location=loc)

            case TokenType.DO:
                loc = self.peek_loc()
                self.advance()
                self.consume(TokenType.COLON, "Expected ':' after `do`")
                body = self.parse_block_or_stmt()
                self.consume(TokenType.WHILE)
                test = self.expression()
                return DoWhile(test, body, None, location=loc)

            case TokenType.IF:
                loc = self.peek_loc()
                self.advance()
                condition = self.expression()
                self.consume(TokenType.COLON, "Expected ':' after if condition")
                then_branch = self.parse_block_or_stmt()
                else_branch = None

                if self.peek().type == TokenType.ELSE:
                    self.advance()
                    if self.peek().type == TokenType.IF:
                        else_branch = self.statement()
                    else:
                        self.consume(TokenType.COLON)
                        else_branch = self.parse_block_or_stmt()

                return IfStmt(condition, then_branch, else_branch, location=loc)

            case TokenType.SEND:
                loc = self.peek_loc()
                self.advance()
                self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses")
                data = self.expression()
                self.consume(TokenType.COMMA, "Expected comma separating value and channel name")
                name = self.expression()
                self.consume(TokenType.RIGHT_PAREN, "Expected closing parantheses")
                return SendStatement(name, data, location=loc)

            case _:
                loc = self.peek_loc()
                if self.peek().type in self.INBUILT_STATEMENTS:
                    func_type = self.peek().type
                    self.advance()
                    return InbuiltStatementNoarg(func_type, location=loc)
                elif self.peek().type in self.INBUILT_PROCEDURES_ARG_1:
                    func_type = self.peek().type
                    self.advance()
                    self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses on function call")
                    value = self.expression()
                    self.consume(TokenType.RIGHT_PAREN, "Expected right parentheses on function call")
                    return InbuiltProcedureArg1(func_type, value, location=loc)

                return self.expression()
    
    def function(self):
        loc = self.peek_loc()
        self.advance()

        name = self.consume(TokenType.IDENTIFIER, "Expected function name")
        self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses for param list")

        params = []
        while (not self.peek().type in {TokenType.RIGHT_PAREN, TokenType.NEWLINE}) and (not self.is_at_end()):
            param_name = self.identifier()
            self.consume(TokenType.COLON, "Expected type hint in params")
            param_type = self.DATATYPES.get(self.consume(*self.VALID_DATATYPES).type)
            params.append((param_name, param_type))
            if self.peek().type is TokenType.COMMA:
                self.advance()
        
        self.consume(TokenType.RIGHT_PAREN, "Expected closing parentheses for param list")

        if self.peek().type is TokenType.ARROW:
            self.consume(TokenType.ARROW, "Expected type hint for function")
            datatype = self.DATATYPES[self.consume(*self.VALID_DATATYPES, error="Expected type hint").type]
        else:
            datatype = None # could have made a datatype, but it'll just be used here so didnt bother
        
        self.consume(TokenType.COLON, "Expected ':' after function prototype")

        body = self.parse_block_or_stmt()
        
        return Function(name, params, datatype, body, location=loc)

    # MARK: expressions

    def expression(self, min_precedence=0):
        loc = self.peek_loc()
        left = self.factor()
        next_token = self.peek()

        while (next_token.type in self.BINARY_OPERATORS) and (self.precedence(next_token) >= min_precedence):
            if next_token.type in [
                TokenType.EQUAL, TokenType.PLUS_EQUALS, TokenType.MINUS_EQUALS,
                TokenType.STAR_EQUALS, TokenType.SLASH_EQUALS, TokenType.PERCENT_EQUALS,
                TokenType.AND_EQUALS, TokenType.OR_EQUALS, TokenType.XOR_EQUALS,
                TokenType.LSH_EQUALS, TokenType.RSH_EQUALS
            ]:
                operator = next_token
                self.advance()
                right = self.expression(self.precedence(operator))

                if not isinstance(left, Var):
                    raise self.error(
                        "Left hand side of an assignment must be a variable.", operator
                    )

                if operator.type == TokenType.EQUAL:
                    left = Assign(left, right, location=loc)
                else:
                    left = AssignCompound(left, operator, right, location=loc)

            elif next_token.type == TokenType.QUESTION_MARK:
                middle = self.parse_cond_middle()
                right = self.expression(self.precedence(next_token))
                left = Conditional(left, middle, right, location=loc)

            else:
                operator = next_token
                self.advance()
                left = BinaryExpr(
                    operator, left, self.expression(self.precedence(next_token) + 1), location=loc
                )

            next_token = self.peek()

        return left

    def factor(self):
        loc = self.peek_loc()
        next_token = self.peek()

        if next_token.type in self.UNARY_OPERATORS:
            operator = self.peek()
            if operator.type in [TokenType.INCREMENT, TokenType.DECREMENT]:
                self.advance()
                argument = self.factor()
                if not isinstance(argument, Var):
                    raise self.error("Prefix operator target must be a variable.", operator)
                left = UpdateExpr(operator, argument, isPrefix=True, location=loc)
            else:
                left = self.unary_expression(operator, loc)

        elif next_token.type == TokenType.IDENTIFIER:
            val = self.consume(TokenType.IDENTIFIER)
            if self.peek().type is TokenType.LEFT_PAREN:
                params = []
                self.advance()
                while not self.peek().type in {TokenType.EOF, TokenType.RIGHT_PAREN}:
                    params.append(self.expression())
                    if not self.peek().type is TokenType.RIGHT_PAREN:
                        self.consume(TokenType.COMMA)
                self.consume(TokenType.RIGHT_PAREN, error="Expected Ending parentheses after function call")

                left = FunctionCall(val.lexeme, params, location=loc)

            else:
                left = Var(val, location=loc)

        # MARK: inbuilt funcs
        elif (function_name := self.peek().type) in self.INBUILT_FUNCTIONS_ARG_0:
            self.advance()
            self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses on function call")
            self.consume(TokenType.RIGHT_PAREN, "Expected right parentheses on function call")
            return InbuiltFunctionArg0(function_name, location=loc)     
           
        elif (function_name := self.peek().type) in self.INBUILT_FUNCTIONS_ARG_1:
            self.advance()
            self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses on function call")
            value = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected right parentheses on function call")
            return InbuiltFunctionArg1(function_name, value, location=loc)
        
        elif (function_name := self.peek().type) in self.INBUILT_FUNCTIONS_ARG_2:
            self.advance()
            self.consume(TokenType.LEFT_PAREN, "Expected opening parentheses on function call")
            value1 = self.expression()
            self.consume(TokenType.COMMA, "Expected seperating comma")
            value2 = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected right parentheses on function call")
            return InbuiltFunctionArg2(function_name, value1, value2, location=loc)

        # MARK: parens and types
        elif next_token.type == TokenType.LEFT_PAREN:
            self.consume(TokenType.LEFT_PAREN)
            left = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after expression end")

        else:
            if self.peek().type == TokenType.INT:
                left = Constant(self.consume(TokenType.INT), location=loc)
            elif self.peek().type == TokenType.FLOAT:
                left = Constant(self.consume(TokenType.FLOAT), location=loc)
            elif self.peek().type == TokenType.STRING:
                left = Constant(self.consume(TokenType.STRING), location=loc)
            else:
                raise self.error(
                    f"Statement, Expression, or operator {self.peek()} could not be found."
                )

        post_token = self.peek()
        if post_token.type in [TokenType.INCREMENT, TokenType.DECREMENT]:
            if not isinstance(left, Var):
                raise self.error("Postfix operator target must be a variable.", post_token)
            operator = post_token
            self.advance()
            left = UpdateExpr(operator, left, isPrefix=False, location=loc)

        elif post_token.type is TokenType.LEFT_SQUARE_BRACKET:
            self.advance()

            start = None
            end = None

            if self.peek().type not in (TokenType.COLON, TokenType.RIGHT_SQUARE_BRACKET):
                start = self.expression()

            if self.peek().type is TokenType.COLON:
                self.advance()

                if self.peek().type is not TokenType.RIGHT_SQUARE_BRACKET:
                    end = self.expression()

                self.consume(TokenType.RIGHT_SQUARE_BRACKET)
                left = StringSlice(left, start, end, location=loc)

            else:
                self.consume(TokenType.RIGHT_SQUARE_BRACKET)
                left = StringIndex(left, start, location=loc)

        return left
    

    def unary_expression(self, operator, loc=None):
        if loc is None:
            loc = self.peek_loc()
        self.advance()
        operand = self.factor()
        return UnaryExpr(operator, operand, location=loc)

    # MARK: HELPER

    def is_at_end(self, num=0):
        return (self.position + num) >= len(self.tokens)

    def consume(self, *token_types, error=None):
        token = self.peek()
        error_msg = error if error else (
            f"Expected token of type(s) "
            f"{', '.join(str(t) for t in token_types).replace('TokenType.', '')}"
        )
        if isinstance(token, Token) and token.type in token_types:
            self.advance()
            return token
        else:
            blame = token if isinstance(token, Token) else None
            raise self.error(error_msg + ", found: " + str(token), blame)

    def advance(self):
        if not self.is_at_end():
            self.position += 1
        return self.tokens[self.position - 1]

    def peek(self, num=1):
        if self.is_at_end(num - 1):
            return TokenType.EOF
        return self.tokens[self.position + num]

    def peek_loc(self, num=1):
        """(file_no, line_no) of the upcoming token, for stamping AST nodes."""
        tok = self.peek(num)
        if isinstance(tok, Token):
            return (tok.file_no, tok.line_no)
        if self.tokens:
            last = self.tokens[-1]
            return (last.file_no, last.line_no)
        return (0, 0)

    def error(self, message: str, token: Token | None = None) -> ParseError:
        if token is None:
            candidate = self.peek()
            token = candidate if isinstance(candidate, Token) else None

        if token is None and self.tokens:
            token = self.tokens[-1]

        if token is not None:
            return ParseError(message, line_no=token.line_no, file_no=token.file_no)
        return ParseError(message)

    def precedence(self, operator):
        if operator.type in self.PRECEDENCE_TABLE:
            return self.PRECEDENCE_TABLE[operator.type]
        else:
            raise self.error(f"Unknown operator {operator.lexeme}", operator)

    def parse_block_or_stmt(self):
        if self.peek().type == TokenType.NEWLINE:
            self.consume(TokenType.NEWLINE)
            self.consume(TokenType.INDENT)
            return self.parse_block_statement()
        return self.statement()

    def parse_cond_middle(self):
        self.consume(TokenType.QUESTION_MARK)
        exp = self.expression(0)
        self.consume(TokenType.COLON)
        return exp