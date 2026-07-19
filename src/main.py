#!/usr/bin/env python3

"""
Copyright 2026 scratchcoder27

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files
(the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE 
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import argparse
from os import getcwd
from subprocess import run

from codegen import CodeGenException, CodeGenerator
import lexer
from optimiser import Optimiser
import parser
import loop_labelling
from preprocessor import Preprocessor, PreprocessError
from typechecker import TypeCheckingPass, TypeError
from deadcodeelimination import DeadFunctionEliminationPass
from constantfolding import ConstantFoldingPass, SemanticError

import colors

from token_types import TokenType
from ast_nodes import *
from stmt import *
from expr import *

import traceback

OPTIMISATION_LEVEL = 3

class CompileError(Exception):
    def __init__(self, error: str, line_no: int, file_no: int = 0):
        self.line_no = line_no
        self.file_no = file_no
        super().__init__(error)

# MARK: ARGS
def parse_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("input_file", help="Input file name")
    arg_parser.add_argument("-o", "--output_file", help="Output file name", default="output.txt")
    arg_parser.add_argument("--debug-output", help="Prints the llvm generated", action="store_true")
    arg_parser.add_argument("--debug-lexing", help="Prints the lexing output", action="store_true")
    arg_parser.add_argument("--debug-parsing", help="Pretty prints the AST", action="store_true")
    arg_parser.add_argument("--debug-analysis", help="Performs the analysis, and prints the AST", action="store_true")
    arg_parser.add_argument("--skip-optimisation", help="Skips the optimisation pass", action="store_true")
    args = arg_parser.parse_args()
    return args

def read_file(filename: str) -> str:
    with open(filename, "r") as f:
        input_code = f.read()
    return input_code

# MARK: LEX
def lex(input_code: str, parsed_files: list[str], input_file_path: str) -> list[lexer.Token]:
    curr_lexer: lexer.Lexer = lexer.Lexer(input_code, parsed_files, 0, file_path=input_file_path)

    try:
        lexed_tokens = curr_lexer.scan_tokens()
    except (lexer.LexingError) as e:
        raise CompileError(
            f"{colors.BRIGHT_RED}Lexing error: {colors.BRIGHT_BLUE}{e}{colors.RESET}",
            line_no=e.line_no if e.line_no is not None else curr_lexer.line,
            file_no=e.file_no if e.file_no is not None else curr_lexer.file_no,
        )

    return lexed_tokens

def preprocess(input_code : list[lexer.Token]) -> tuple[list[lexer.Token], dict]:
    preprocessor = Preprocessor()
    try:
        val = (preprocessor.preprocess_all(input_code), preprocessor.options)
    except PreprocessError as e:
        print(f"{colors.BRIGHT_RED}Preprocessor Error: {e}{colors.RESET}")
        exit()

    return val

def fix_inline_asm(input_code : list[lexer.Token]) -> list[lexer.Token]:
    return input_code

# MARK: PARSE
def parsing(lexed_tokens : list[lexer.Token]) -> Program:
    curr_parser = parser.Parser()

    try:
        parsed = curr_parser.parse(lexed_tokens)
    except parser.ParseError as e:
        raise CompileError(f"{colors.BRIGHT_RED}Syntax Error: {colors.BRIGHT_BLUE}{e}{colors.RESET}", line_no=e.line_no, file_no=e.file_no)
    
    return parsed

# MARK: SEMANTIC ANALYSIS
def semantic_analysis(program: Program, options) -> Program:
    try:
        analyzed_program = loop_labelling.LoopLabellingPass().label(program)

        typechecker = TypeCheckingPass()
        analyzed_program = typechecker.check(program, options)

        # print(typechecker.call_graph)

        dce = DeadFunctionEliminationPass(typechecker.call_graph)
        analyzed_program = dce.eliminate(analyzed_program)

        analyzed_program = ConstantFoldingPass().fold(analyzed_program)

    except (loop_labelling.SemanticError, SemanticError, TypeError) as e:
        if isinstance(e, TypeError):
            raise CompileError(f"{colors.BRIGHT_RED}Type error: {colors.BRIGHT_BLUE}{e}{colors.RESET}", line_no=e.line_no, file_no=e.file_no)
        else:
            raise CompileError(f"{colors.BRIGHT_RED}Semantic error: {colors.BRIGHT_BLUE}{e}{colors.RESET}", line_no=e.line_no, file_no=e.file_no)

    return analyzed_program

# MARK: CODEGEN
def code_generation(program: Program, options : dict = {}, file_nos = []) -> list:
    generator = CodeGenerator(file_nos)

    try:
        generator.generate_code(program, options=options)
    except CodeGenException as e:
        raise CompileError(f"{colors.BRIGHT_RED}Code Generation Error: {colors.BRIGHT_BLUE}{e}{colors.RESET}", line_no=e.line_no, file_no=e.file_no)

    return generator.program

# MARK: OPTIMISATION
def optimise_program(program: list[tuple[str, list]]) -> list[tuple[str, list]]:
    return Optimiser().optimise_program(program)
    
# MARK: ERRORS
def error_with_filename(line_no: int, line: str = "<unimplemented>"):
    print(f"{colors.BRIGHT_MAGENTA}[{line_no}] {colors.BLUE}{line}{colors.RESET}")


def get_source_lines(parsed_files: list[str], file_no: int, main_source: str) -> list[str]:
    if file_no == 0:
        return main_source.splitlines()

    try:
        with open(parsed_files[file_no], 'r') as f:
            return f.read().splitlines()
    except (OSError, IndexError):
        return main_source.splitlines() # fallback to main

# MARK: MAIN
if __name__ == "__main__":
    args = parse_args()
    input_code = read_file(args.input_file)

    parsed_files: list[str] = [args.input_file]

    try:
        parsed_files: list[str] = [args.input_file]
        lexed_tokens = lex(input_code, parsed_files, args.input_file)
        
        lexed_tokens = fix_inline_asm(lexed_tokens)
        lexed_tokens, options = preprocess(lexed_tokens)

        if args.debug_lexing:
            print(f"{colors.BRIGHT_MAGENTA}Lexing output:{colors.RESET}")
            for token in lexed_tokens:
                print(f"{colors.BRIGHT_CYAN}{token.type.name}: {colors.BRIGHT_YELLOW}`{token.lexeme.replace("\n", "<newline>")}`{colors.RESET}")
            exit()


        parsed = parsing(lexed_tokens)
        
        if args.debug_parsing:
            from astpprinter import AstPrinter
            printer = AstPrinter()
            print(f"{colors.BRIGHT_MAGENTA}Parsed AST:{colors.RESET}")
            print(printer.print(parsed))
            exit()

        parsed = semantic_analysis(parsed, options)
        
        if args.debug_analysis:
            try:
                printer = AstPrinter()
            except NameError:
                from astpprinter import AstPrinter
                printer = AstPrinter()
            print(f"{colors.BRIGHT_MAGENTA}Parsed AST:{colors.RESET}")
            print(printer.print(parsed, show_types=True))
            exit()
            
        program = code_generation(parsed, options=options, file_nos=parsed_files)
        if not args.skip_optimisation:
            program = optimise_program(program)
        
        if args.debug_output:
            print(f"{colors.BRIGHT_MAGENTA}Generated Program:{colors.RESET}")
            for i, item in enumerate(program):
                print(f"{colors.YELLOW}{i+1:0>3} {colors.RESET}{colors.BRIGHT_GREEN}{item[0]}{colors.RESET} {colors.BRIGHT_CYAN}{" ".join([str(x) for x in item[1]])}{colors.RESET}")
        
        with open(args.output_file, 'w') as f:
                for item in program:
                    line = item[0]
                    if item[1] is not []:
                        for i in item[1]:
                            line += " " + str(i)
                    if item[0] != "buffer":
                        f.write(f"{line.strip()}\n")
                    else:
                        f.write(f"{line}\n")
    
        
    except CompileError as e:
        # traceback.print_exception(e)
        file_no = e.file_no if e.file_no is not None else 0
        try:
            raw_path = parsed_files[file_no]
        except IndexError:
            raw_path = args.input_file
        file_path = raw_path if raw_path.startswith("/") else getcwd() + "/" + raw_path

        print(f"{colors.BRIGHT_MAGENTA}Compilation failed with error:{colors.RESET}")
        print(f"{colors.BRIGHT_YELLOW}File: ", end="")
        print(f"\033]8;;file://{file_path}\033\\{file_path}\033]8;;\033\\", end="")
        
        if e.line_no is not None:
            print(f", in line no. {e.line_no}:{colors.RESET}")
            source_lines = get_source_lines(parsed_files, file_no, input_code)

            if e.line_no - 2 >= 0 and e.line_no - 2 < len(source_lines):
                error_with_filename(e.line_no - 1, source_lines[e.line_no - 2])

            error_with_filename(e.line_no, source_lines[e.line_no - 1])

            if e.line_no < len(source_lines):
                error_with_filename(e.line_no + 1, source_lines[e.line_no])

        else:
            print(f"{colors.RESET}\n")
        print(e)
        exit(1)