from enum import Enum, auto

class TokenType(Enum):
    # Single character tokens
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_SQUARE_BRACKET = auto()
    RIGHT_SQUARE_BRACKET = auto()
    COMMA = auto()
    DOT = auto()
    TILDE = auto()
    MINUS = auto()
    PLUS = auto()
    COLON = auto()
    SLASH = auto()
    STAR = auto()
    PERCENT = auto()
    NEWLINE = auto()
    QUESTION_MARK = auto()
    SEMICOLON = auto()



    BITWISE_AND = auto()
    BITWISE_OR = auto()
    BITWISE_XOR = auto()
    LEFTSHIFT = auto()
    RIGHTSHIFT = auto()

    BANG = auto()
    LOGICAL_NOT = auto()
    LOGICAL_AND = auto()
    LOGICAL_OR = auto()
    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    GREATER = auto()
    LESS = auto()
    GREATER_EQUAL = auto()
    LESS_EQUAL = auto()

    PLUS_EQUALS = auto()
    MINUS_EQUALS = auto()
    STAR_EQUALS = auto()
    SLASH_EQUALS = auto()
    PERCENT_EQUALS = auto()
    AND_EQUALS = auto()
    OR_EQUALS = auto()
    XOR_EQUALS = auto()
    LSH_EQUALS = auto()
    RSH_EQUALS = auto()  

    INCREMENT = auto()
    DECREMENT = auto()

    ARROW = auto()
    EQUAL = auto()
    
    # Literals
    IDENTIFIER = auto()
    STRING = auto()
    INT = auto()
    FLOAT = auto()
    
    # Keywords
    VAR = auto()
    DEF = auto()
    IF = auto()
    ELSE = auto()
    RETURN = auto()

    SET_SPLITTER = auto()
    SPLIT = auto()
    SPLITCOUNT = auto()

    PUSH = auto()
    POP = auto()
    PEEK = auto()

    LENGTH = auto()
    WORLDTIME = auto()

    DO = auto()
    WHILE = auto()
    FOR = auto()
    BREAK = auto()
    CONTINUE = auto()

    ROUND = auto()
    FLOOR = auto()
    CEIL = auto()

    STRING_CAST = auto()
    INT_CAST = auto()
    FLOAT_CAST = auto()

    POLL = auto()
    LISTEN = auto()
    SEND = auto()

    SHUTDOWN = auto()
    ENDTICK = auto()

    NULL = auto()

    # datatypes
    TYPE_INT = auto()
    TYPE_FLOAT = auto()
    TYPE_STRING = auto()
    TYPE_ARRAY = auto()

    # special  
    INDENT = auto()
    DEDENT = auto()  
    EOF = auto()

    ASSEMBLY = auto()

    # preprocessing
    PREPROCESS = auto() # '#'
    BACKSLASH = auto()