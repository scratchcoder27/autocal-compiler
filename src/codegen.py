import colors
from expr import *
from stmt import *
from ast_nodes import *
from token_types import TokenType
from tokens import Token
from scope import Scope
from variable import Variable

class CodeGenException(Exception):
    def __init__(
        self,
        message: str,
        file_no: int | None = None,
        line_no: int | None = None,
    ):
        super().__init__(message)
        self.file_no = file_no
        self.line_no = line_no

class CodeGenerator(ExprVisitor, StmtVisitor):
    def __init__(self, file_nos):
        self.builder = None
        self.scopes = Scope(None)
        
        self.loops: list[dict[str, str]] = [] 
        
        self.temp_var = 0
        self.label_count = 0
        self.program : list[tuple[str, list[str | int]]] = []

        self.pending_protect: list[str] = []

        self.return_label_count = 0

        self.MAX_FUNCTION_LABEL_SIZE = 3 # digits (not counting the "f" prefix)

        self.explicit_conversions = True
        self.use_native_callstack = False
        self.use_call_frame_protection = False

        self.warnings = {
            "stackCorruption": False
        }

        self.file_nos = file_nos

    def warn(self, message : str, location : tuple):
        try:
            file_name = self.file_nos[location[1]-1]
        except IndexError:
            file_name = "<could not be located>"

        print(f"{colors.BRIGHT_YELLOW}WARNING: {colors.YELLOW}{message} {colors.BLUE}[in line {location[0]}, file '{file_name}']{colors.RESET}")

    # MARK: HELPERS
    def _live_variable_names(self) -> list[str]:
        names = []
        scope = self.scopes
        while scope is not None and scope.parent is not None:
            names.extend(
                [f"{name}_{var.modifier}" for name, var in scope.variables.items()]
            )
            scope = scope.parent
        return names

    def _eval_expr(self, expr: Expr) -> str:
        if isinstance(expr, (Constant)):
            return str(expr.value.lexeme.replace("\"", ""))
        return str(expr.accept(self))

    def _operand_name(self, expr: Expr) -> tuple[bool, str]: # returns the name too
        val = self._eval_expr(expr)
        return (isinstance(expr, Constant), val)

    def _resolve_operand(self, expr: Expr) -> str:
        is_const, val = self._operand_name(expr)
        return val if is_const else f"${val}$"
    
    def _wrap(self, is_const: bool, val: str) -> str:
        return val if is_const else f"${val}$" # yet another helper for basically the same thing

    def _next_modifier(self, name) -> int:
        if self.scopes.parent is not None and self.scopes.parent.check_exists(name):
            outer_variable = self.scopes.parent.resolve(name)
            return outer_variable.modifier + 1
        return 0

    def _mangled_name(self, name) -> str:
        variable = self.scopes.resolve(name)
        return f"{name}_{variable.modifier}"

    def _arith_opcode(self, datatype) -> str:
        return "evalr" if datatype is Datatypes.INT else "eval"
    
    def _emit_logical_not(self, expr: Expr) -> str:
        result_var = self.next_tmp()
        lbl_false = self.next_label("not_false")
        lbl_end = self.next_label("not_end")

        self.generate_truthiness(expr)
        self.add_stmt("jmpif", lbl_false) 
        self.add_stmt("buffer", 1)
        self.add_stmt("save", result_var)
        self.add_stmt("jmp", lbl_end)
        self.add_stmt("dest", lbl_false)
        self.add_stmt("buffer", 0)
        self.add_stmt("save", result_var)
        self.add_stmt("dest", lbl_end)
        return result_var

    def emit_native_comparison(self, expr: BinaryExpr):
        v1 = expr.left.accept(self)
        v2 = expr.right.accept(self)
        
        op = expr.operator.lexeme
        
        # eq compares the buffer directly to the argument
        if op == "==":
            self.add_stmt("load", v1)
            self.add_stmt("eq", f"${v2}$")
            
        elif op == "!=":
            self.add_stmt("load", v1)
            self.add_stmt("eq", f"${v2}$")
            # Invert the buffer logic
            lbl_not_eq = self.next_label("not_eq")
            lbl_end_eq = self.next_label("end_eq")
            self.add_stmt("jmpnot", lbl_not_eq)
            self.add_stmt("buffer", "false")
            self.add_stmt("jmp", lbl_end_eq)
            self.add_stmt("dest", lbl_not_eq)
            self.add_stmt("buffer", "true")
            self.add_stmt("dest", lbl_end_eq)

        elif op == ">":
            self.add_stmt("load", v2)
            self.add_stmt("gtb", f"${v1}$")
        elif op == "<":
            self.add_stmt("load", v2)
            self.add_stmt("ltb", f"${v1}$")
        elif op == ">=":
            self.add_stmt("load", v2)
            self.add_stmt("geb", f"${v1}$")
        elif op == "<=":
            self.add_stmt("load", v2)
            self.add_stmt("leb", f"${v1}$")

    def convert_buffer_to_bool_int(self) -> str:
        var = self.next_tmp()
        lbl_false = self.next_label("bool_false")
        lbl_end = self.next_label("bool_end")
        
        self.add_stmt("jmpnot", lbl_false)
        self.add_stmt("buffer", 1)
        self.add_stmt("save", var)
        self.add_stmt("jmp", lbl_end)
        
        self.add_stmt("dest", lbl_false)
        self.add_stmt("buffer", 0)
        self.add_stmt("save", var)
        
        self.add_stmt("dest", lbl_end)
        return var

    def generate_truthiness(self, expr: Expr):
        if isinstance(expr, BinaryExpr) and expr.operator.lexeme in ["==", "!=", ">", "<", ">=", "<="]:
            self.emit_native_comparison(expr)
        else:
            var = self._eval_expr(expr)
            self.add_stmt("load", var)
            self.add_stmt("eq", 0)
            
            # Invert it so any non-zero value evaluates to "true"
            lbl_truthy = self.next_label("truthy")
            lbl_end = self.next_label("truthy_end")
            self.add_stmt("jmpnot", lbl_truthy)
            self.add_stmt("buffer", "false")
            self.add_stmt("jmp", lbl_end)
            self.add_stmt("dest", lbl_truthy)
            self.add_stmt("buffer", "true")
            self.add_stmt("dest", lbl_end)

    
    def add_stmt(self, name, *args):
        self.program.append((name, args))
    
    def next_tmp(self) -> str:
        temp = f"t_{self.temp_var}"
        self.temp_var += 1
        return temp

    def next_label(self, prefix="L") -> str:
        lbl = f"{prefix}_{self.label_count}"
        self.label_count += 1
        return lbl
    
    # MARK: some more const folding stuff
    def _eval_protected_sequence(self, exprs: list[Expr]) -> list[tuple[bool, str]]: 
        # wanted to fold stuff without actual folding passes [while implementing string slicing] (safely because of the functions)
        results = []
        protected_count = 0
        try:
            for expr in exprs:
                is_const, val = self._operand_name(expr)
                results.append((is_const, val))
                if not is_const:
                    self.pending_protect.append(val)
                    protected_count += 1
        finally:
            for _ in range(protected_count):
                self.pending_protect.pop()
        return results


    def _diff_operand(self, minuend: tuple[bool, str], subtrahend: tuple[bool, str]) -> tuple[bool, str]: # ill just use this once and then never use it again
        m_const, m_val = minuend
        s_const, s_val = subtrahend
        if m_const and s_const:
            return True, str(int(m_val) - int(s_val))
        var = self.next_tmp()
        self.add_stmt("evalr", f"{self._wrap(m_const, m_val)} - {self._wrap(s_const, s_val)}")
        self.add_stmt("save", var)
        return False, var

    def _plus_one_operand(self, operand: tuple[bool, str]) -> tuple[bool, str]:
        is_const, val = operand
        if is_const:
            return True, str(int(val) + 1)
        var = self.next_tmp()
        self.add_stmt("evalr", f"{self._wrap(is_const, val)} + 1")
        self.add_stmt("save", var)
        return False, var

    # MARK: program
    def generate_code(self, program: Program, options : dict = {}):
        try:
            self.descoping: bool = options.get("explicit_descoping", "false").lower() == "true"
            self.use_native_callstack: bool = options.get("native_callstack", "true").lower() == "true"
            self.use_call_frame_protection: bool = options.get("use_call_frames", "false").lower() == "true"
        except ValueError:
            raise CodeGenException("Invalid value for pragma")
        
        if self.use_call_frame_protection and not self.use_native_callstack:
            raise CodeGenException(f"Call Frame support must be used with Native Callstack enabled")

        if (speed := options.get("clockspeed", None)):
                try:
                    self.add_stmt("clockspeed", str(int(speed)))
                except ValueError:
                    raise CodeGenException(f"Invalid value for clockspeed ({speed})")
        
        if not self.use_native_callstack:
            self.add_stmt("buffer", 0)
            self.add_stmt("save", "call-stack")
        self.add_stmt("buffer", "0")
        self.add_stmt("save", "return-value")

        for stmt in program.stmts:
            stmt.accept(self)
    
    def visit_functiondeclarationstmt_stmt(self, stmt : FunctionDeclarationStmt):
        pass # only used in the typechecker

    def visit_function_stmt(self, function: Function):
        skip_lbl = self.next_label("skip_fn")
        self.add_stmt("jmp", skip_lbl)

        self.add_stmt("dest", f"f_{function.name}")
        self.scopes = Scope(self.scopes)   # dedicated function scope for params
        for param, param_type in function.params:
            var_name = param.lexeme
            modifier = self._next_modifier(var_name)
            self.scopes.define(var_name, Variable(var_name, param_type, modifier))
            self.add_stmt("pop")
            self.add_stmt("save", f"{var_name}_{modifier}")
        function.body.accept(self)
        self.scopes = self.scopes.parent 

        self.add_stmt("dest", skip_lbl)

    def visit_block_stmts(self, block : Block):
        self.scopes = Scope(self.scopes)
        for item in block.body:
            item.accept(self)
        if self.descoping:
            self.add_stmt("buffer 0")
            for variable in self.scopes.variables.keys():
                self.add_stmt(f"save {variable}")

        self.scopes = self.scopes.parent
    
    # MARK: Statements

    def visit_return_stmt(self, stmt: Return):
        if stmt.expression:
            val = self._eval_expr(stmt.expression)
            if isinstance(stmt.expression, Constant):
                self.add_stmt("buffer", str(val))
            else:
                self.add_stmt("load", str(val))

            self.add_stmt("save", "return-value")

        self.exit_function()

    # MARK: looping
    def visit_while_stmt(self, stmt: While):
        start_lbl = self.next_label("while_start")
        end_lbl = self.next_label("while_end")
        
        self.add_stmt("dest", start_lbl)
        
        self.generate_truthiness(stmt.condition) # Injects 'true'/'false' directly
        self.add_stmt("jmpnot", end_lbl)
        
        self.loops.append({"start": start_lbl, "end": end_lbl})
        stmt.body.accept(self)
        self.add_stmt("jmp", start_lbl)
        
        self.add_stmt("dest", end_lbl)
        self.loops.pop()

    def visit_dowhile_stmt(self, stmt: DoWhile):
        start_lbl = self.next_label("dowhile_start")
        end_lbl = self.next_label("dowhile_end")
        
        self.add_stmt("dest", start_lbl)
        self.loops.append({"start": start_lbl, "end": end_lbl})
        
        stmt.body.accept(self)
        
        self.generate_truthiness(stmt.condition) # Injects 'true'/'false' directly
        self.add_stmt("jmpif", start_lbl)
        
        self.add_stmt("dest", end_lbl)
        self.loops.pop()
    
    def visit_null_stmt(self, stmt : Null):
        # self.add_stmt("nop")
        pass
    
    def visit_break_stmt(self, stmt : Break):
        if not self.loops:
            raise CodeGenException(
                "Break statement outside of a loop.",
                *stmt.location,
            )
        self.add_stmt("jmp", self.loops[-1]["end"])
    
    def visit_continue_stmt(self, stmt : Continue):
        if not self.loops:
            raise CodeGenException(
                "Continue statement outside of a loop.",
                *stmt.location,
            )
        self.add_stmt("jmp", self.loops[-1]["start"])
    
    # MARK: compound    
    def visit_compound_stmt(self, stmt : Compound):
        stmt.block.accept(self)
    
    # MARK: declaration
    def visit_variabledeclaration_stmt(self, stmt : VariableDeclaration):
        name = stmt.name.lexeme
        if self.scopes.check_exists_in_scope(name):
            raise CodeGenException(
                f"Variable {name} is already defined.",
                *stmt.name.location,
            )
        
        modifier = self._next_modifier(name)
        self.scopes.define(name, Variable(name, None, modifier))
        mangled = self._mangled_name(name)

        if stmt.init is not None:
            var = self._eval_expr(stmt.init)
            self.add_stmt("load", var)
            self.add_stmt("save", mangled)
    
    # MARK: if
    def visit_ifstmt_stmt(self, stmt: IfStmt):
        else_lbl = self.next_label("else")
        end_lbl = self.next_label("endif")
        
        self.generate_truthiness(stmt.expression)
        self.add_stmt("jmpnot", else_lbl)
        
        stmt.then.accept(self)
        self.add_stmt("jmp", end_lbl)
        
        self.add_stmt("dest", else_lbl)
        if stmt.Else:
            stmt.Else.accept(self)
            
        self.add_stmt("dest", end_lbl)
    
    # MARK: predefined
    def visit_inbuiltstatementnoarg_stmt(self, expr : InbuiltStatementNoarg):
        match expr.type:
            case TokenType.ENDTICK:
                self.add_stmt("endtick")
            case TokenType.SHUTDOWN:
                self.add_stmt("shutdown")
    
    def visit_inbuiltprocedurearg1_stmt(self, stmt: InbuiltProcedureArg1):
        val = self._resolve_operand(stmt.val)
        
        match stmt.type:
            case TokenType.PUSH:
                if self.use_native_callstack:
                    if not self.warnings["stackCorruption"]:
                        self.warn("Pushing to the stack is dangerous when the native stack is used. Please turn it off with the pragma 'native_callstack'", stmt.location)
                        self.warnings["stackCorruption"] = True
                self.add_stmt("push", val)
            case TokenType.SET_SPLITTER:
                self.add_stmt("splitter", val)
    
    def visit_sendstatement_stmt(self, expr : SendStatement):
        data = self._eval_expr(expr.data)
        if isinstance(expr.data, Constant):
            self.add_stmt("buffer", f"{data}")
        else:
            self.add_stmt("load", f"{data}")

        name = self._resolve_operand(expr.name)
        self.add_stmt("send", name)
    
    def exit_function(self):
        label_len = self.MAX_FUNCTION_LABEL_SIZE + 1

        if self.use_native_callstack:
            jmp_loc = self.next_tmp()
            self.add_stmt("pop")
            self.add_stmt("save", jmp_loc)
        else:
            self.add_stmt("buffer", "call-stack")
            self.add_stmt("end", str(label_len))
            jmp_loc = self.next_tmp()
            self.add_stmt("save", jmp_loc)
            self.add_stmt("buffer", "call-stack")
            self.add_stmt("length")
            self.add_stmt("evalr", f"$buffer$ - {label_len}")
            buff_size = self.next_tmp()
            self.add_stmt("save", buff_size)
            self.add_stmt("buffer", "call-stack")
            self.add_stmt("first", f"${buff_size}$")
            self.add_stmt("save", "call-stack")

        self.add_stmt("jmp", f"${jmp_loc}$")
    
    # MARK: EXPRESSIONS
    def visit_expression_stmt(self, stmt):
        stmt.expression.accept(self)

    # MARK: function
    def visit_functioncall_expr(self, expr : FunctionCall):
        params = []
        protected_count = 0 
        try:
            for param in expr.params:
                if not param:
                    continue
                is_const, name = self._operand_name(param)
                params.append(name if is_const else f"${name}$")
                if not is_const:
                    self.pending_protect.append(name)
                    protected_count += 1
        finally: # might even add synchronising for errors one day
            for _ in range(protected_count):
                self.pending_protect.pop()

        return_label = self.return_label_count
        self.return_label_count += 1
        if self.return_label_count >= (10**self.MAX_FUNCTION_LABEL_SIZE):
            raise CodeGenException("Too many call sites, set pragma MAX_FUNCTION_LABEL_SIZE to a higher value")
        return_label_str = "f" + f"{return_label:0{self.MAX_FUNCTION_LABEL_SIZE}}"

        live = self._live_variable_names() if self.use_call_frame_protection else []
        live += [t for t in self.pending_protect if t not in live]

        for name in live:
            self.add_stmt("push", f"${name}$")

        if self.use_native_callstack:
            self.add_stmt("push", return_label_str)
        else:
            self.add_stmt("concat", f"$call-stack${return_label_str}")
            self.add_stmt("save", "call-stack")

        for param in params.__reversed__():
            self.add_stmt("push", param)

        self.add_stmt("jmp", f"f_{expr.name}")
        self.add_stmt("dest", return_label_str)

        for name in reversed(live): # restore, LIFO
            self.add_stmt("pop")
            self.add_stmt("save", name)

        result = self.next_tmp()
        self.add_stmt("load", "return-value")
        self.add_stmt("save", result)
        return result

    # MARK: expressions
    def visit_constant_expr(self, expr: Constant):
        var = self.next_tmp()
        self.add_stmt("buffer", expr.value.lexeme.replace("\"", ""))
        self.add_stmt("save", var)
        return var
    
    def visit_assign_expr(self, expr : Assign):
        name = expr.name.name.lexeme
        mangled = self._mangled_name(name)
        
        var = expr.value.accept(self)
        self.add_stmt("load", var)
        self.add_stmt("save", mangled)
        return mangled
    
    def visit_var_expr(self, expr : Var):
        name = expr.name.lexeme
        return self._mangled_name(name)
    
    # MARK: operations
    def visit_unaryexpr_expr(self, expr: UnaryExpr):
        if expr.operator.lexeme in ("not", "!"):
            return self._emit_logical_not(expr.expression)

        v1 = self._resolve_operand(expr.expression)
        var = self.next_tmp()
        opcode = self._arith_opcode(expr.datatype)
        self.add_stmt(opcode, f"0 {expr.operator.lexeme} {v1}")
        self.add_stmt("save", var)
        return var
    
    def visit_binaryexpr_expr(self, expr : BinaryExpr):
        op = expr.operator.lexeme
        
        if op == "%":    op = "m"

        if op in ["==", "!=", ">", "<", ">=", "<="]:
            self.emit_native_comparison(expr)
            return self.convert_buffer_to_bool_int()

        left_const, v1_name = self._operand_name(expr.left)
        if not left_const:
            self.pending_protect.append(v1_name)
        v2 = self._resolve_operand(expr.right)
        if not left_const:
            self.pending_protect.pop()
            
        v1 = v1_name if left_const else f"${v1_name}$"

        var = self.next_tmp()
        if expr.datatype is Datatypes.STRING:
            self.add_stmt("concat", f"{v1}{v2}")
        else:
            opcode = self._arith_opcode(expr.datatype)
            self.add_stmt(opcode, f"{v1} {op} {v2}")
        self.add_stmt("save", var)
        return var
    
    # MARK: compound assigns
    
    def visit_assigncompound_expr(self, expr: AssignCompound):
        name = expr.target.name.lexeme
        mangled = self._mangled_name(name)

        val_var = self._resolve_operand(expr.value)
        base_operator = expr.operator.lexeme.replace("=", "").strip()

        if expr.datatype is Datatypes.STRING and base_operator == "+":
            self.add_stmt("concat", f"${mangled}$ {val_var}")
        else:
            opcode = self._arith_opcode(expr.datatype)
            self.add_stmt(opcode, f"${mangled}$ {base_operator} {val_var}")
        self.add_stmt("save", mangled)
        return mangled

    def visit_updateexpr_expr(self, expr: UpdateExpr):
        name = expr.argument.name.lexeme
        mangled = self._mangled_name(name)
        
        # Handles ++ and --
        operator = "+" if expr.operator.lexeme == "++" else "-"
        opcode = self._arith_opcode(expr.datatype)
        self.add_stmt(opcode, f"${mangled}$ {operator} 1")
        self.add_stmt("save", mangled)
        return mangled
    
    # MARK: conditional
    def visit_conditional_expr(self, expr : Conditional):
        result_var = self.next_tmp()
        else_lbl = self.next_label("ternary_else")
        end_lbl = self.next_label("ternary_end")
        
        self.generate_truthiness(expr.condition)
        self.add_stmt("jmpnot", else_lbl)
        
        v1 = self._eval_expr(expr.val1)
        self.add_stmt("load", v1)
        self.add_stmt("save", result_var)
        self.add_stmt("jmp", end_lbl)
        
        self.add_stmt("dest", else_lbl)
        v2 = self._eval_expr(expr.val2)
        self.add_stmt("load", v2)
        self.add_stmt("save", result_var)
        
        self.add_stmt("dest", end_lbl)
        return result_var
    
    # MARK: inbuilts

    def visit_inbuiltfunctionarg1_expr(self, expr : InbuiltFunctionArg1):
        if expr.type is TokenType.STRING_CAST:
            return self._eval_expr(expr.val)

        if expr.type in (TokenType.INT_CAST, TokenType.FLOAT_CAST):
            if not self.explicit_conversions: # else ignore, used only for typechecking
                return self._eval_expr(expr.val)

            if expr.val.datatype is expr.datatype:
                return self._eval_expr(expr.val)

            result_val = self.next_tmp()
            val = self._resolve_operand(expr.val)
            opcode = self._arith_opcode(expr.datatype)
            self.add_stmt(opcode, f"{val} + 0")
            self.add_stmt("save", f"{result_val}")
            return result_val

        result_val = self.next_tmp()
        val = expr.val.accept(self)
        match expr.type:
            case TokenType.ROUND:
                 self.add_stmt("load", str(val))
                 self.add_stmt("round")
                 self.add_stmt("save", f"{result_val}")
                 return result_val
            
            case TokenType.CEIL:
                 self.add_stmt("load", str(val))
                 self.add_stmt("ceil")
                 self.add_stmt("save", f"{result_val}")
                 return result_val
            
            case TokenType.FLOOR:
                 self.add_stmt("load", str(val))
                 self.add_stmt("floor")
                 self.add_stmt("save", f"{result_val}")
                 return result_val
            
            case TokenType.LISTEN:
                self.add_stmt("listen", f"${val}$")
                self.add_stmt("save", f"{result_val}")
                return result_val
            
            case TokenType.POLL:
                self.add_stmt("poll", f"${val}$")
                self.add_stmt("save", f"{result_val}")
                return result_val
            
            case TokenType.LENGTH:
                self.add_stmt("length", f"${val}$")
                self.add_stmt("save", f"{result_val}")
                return result_val
            
            case TokenType.SPLITCOUNT:
                self.add_stmt("load", str(val))
                self.add_stmt("splitcount")
                self.add_stmt("save", f"{result_val}")
                return result_val
    
    def visit_inbuiltfunctionarg2_expr(self, expr : InbuiltFunctionArg2):
        result_val = self.next_tmp()
        if expr.type is TokenType.SPLIT:
            left_const, v1_name = self._operand_name(expr.val1)
            if not left_const:
                self.pending_protect.append(v1_name)
            v2 = self._resolve_operand(expr.val2)
            if not left_const:
                self.pending_protect.pop()
            v1 = v1_name if left_const else f"${v1_name}$"

            if left_const:
                self.add_stmt("buffer", str(v1))
            else:
                self.add_stmt("load", str(v1).strip("$"))

            self.add_stmt("split", v2)
            
            self.add_stmt("save", result_val)
            return result_val

    def visit_inbuiltfunctionarg0_expr(self, expr : InbuiltFunctionArg0):
        result_val = self.next_tmp()
        match expr.type:
            case TokenType.POP:
                self.add_stmt("pop")
                self.add_stmt("save", f"{result_val}")
            case TokenType.PEEK:
                self.add_stmt("peek")
                self.add_stmt("save", f"{result_val}")
            case TokenType.WORLDTIME:
                self.add_stmt("worldtime")
                self.add_stmt("save", f"{result_val}")
        return result_val
    
    # MARK: string slicing    
    def visit_stringslice_expr(self, expr: StringSlice):
        parts = [expr.value]
        if expr.left is not None:
            parts.append(expr.left)
        if expr.right is not None:
            parts.append(expr.right)

        (value_c, value_v), *rest = self._eval_protected_sequence(parts)
        left_op = rest.pop(0) if expr.left is not None else None
        right_op = rest.pop(0) if expr.right is not None else None

        result_val = self.next_tmp()

        if left_op is None:
            self.add_stmt("buffer" if value_c else "load", str(value_v))
            self.add_stmt("first", self._wrap(*right_op))
            self.add_stmt("save", result_val)
            return result_val

        if right_op is None:
            value_var = value_v if not value_c else self.next_tmp()
            if value_c:
                self.add_stmt("buffer", str(value_v))
                self.add_stmt("save", value_var)

            len_var = self.next_tmp()
            self.add_stmt("length", f"${value_var}$")
            self.add_stmt("save", len_var)

            self.add_stmt("load", value_var)
            self.add_stmt("last", self._wrap(*self._diff_operand((False, len_var), left_op)))
            self.add_stmt("save", result_val)
            return result_val

        self.add_stmt("buffer" if value_c else "load", str(value_v))
        self.add_stmt("first", self._wrap(*right_op))
        self.add_stmt("last", self._wrap(*self._diff_operand(right_op, left_op)))
        self.add_stmt("save", result_val)
        return result_val

    def visit_stringindex_expr(self, expr: StringIndex):
        (value_c, value_v), (idx_c, idx_v) = \
            self._eval_protected_sequence([expr.value, expr.idx])

        first_amt = self._plus_one_operand((idx_c, idx_v))

        result_val = self.next_tmp()
        if value_c:
            self.add_stmt("buffer", str(value_v))
        else:
            self.add_stmt("load", str(value_v))

        self.add_stmt("first", self._wrap(*first_amt))
        self.add_stmt("last", "1")
        self.add_stmt("save", result_val)
        return result_val