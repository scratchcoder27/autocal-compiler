from ast_nodes import Block, Function, VariableDeclaration, Program
from stmt import *
from expr import *
from token_types import TokenType
from scope import Scope
from variable import Variable


class TypeError(Exception):
    def __init__(
        self,
        message: str,
        file_no: int | None = None,
        line_no: int | None = None,
    ):
        super().__init__(message)
        self.file_no = file_no
        self.line_no = line_no


class TypeCheckingPass(StmtVisitor, ExprVisitor):
    def __init__(self):
        self.options = dict()
        self.scope = Scope()
        self.function_return_stack : list[Datatypes] = []
        self.function_is_returned_stack : list[Datatypes] = [] # there's definitely a better way somewhere
        self.function_declarations_stack : list[list[str]] = [[]]
        
        self.call_graph: dict[str, set[str]] = {}   # for ded code elimination
        self.current_function_stack: list[str] = []

    def _name_str(self, name) -> str:
        if hasattr(name, "lexeme"):
            return name.lexeme
        if hasattr(name, "name"):
            return self._name_str(name.name)
        return str(name)
    
    def _signature_str(self, name : str) -> str:
        split = name.strip("-").split("-")
        func_name = split[0]
        func_name += "("
        param_len = len(split[1:])
        for i, param in enumerate(split[1:]):
            match param:
                case "i":    func_name += "int"
                case "s":    func_name += "str"
                case "f":    func_name += "float"
                case _:      return name
            if i != (param_len - 1):
                func_name += ", "
        func_name += ")"
        return func_name
    
    def _forward_declare_function(self, stmt: Function):
        func_name = self.name_mangle(stmt.name.lexeme, [item[1] for item in stmt.params])

        if self.scope.check_function_exists_in_scope(func_name):
            raise TypeError(
                f"Function with signature {self._signature_str(func_name)} already exists in scope",
                *stmt.location,
            )
        if self.scope.check_exists_in_scope(func_name):
            raise TypeError(
                f"Function with signature {self._signature_str(func_name)} conflicts with variable already in scope",
                *stmt.location,
            )

        self.scope.define_funct(func_name, stmt.datatype)

    def check(self, program, options):
        self.explicit_conversions : bool = options.get("explicit_conversions", "false").lower() == "true"

        for item in program.stmts:
            if isinstance(item, Function):
                self._forward_declare_function(item)
        
        stmts = []
        for stmt in program.stmts:
            if not isinstance(stmt, Null):
                stmts.append(stmt.accept(self))
        
        if len(self.function_declarations_stack) > 0:
            body_top = []
            for item in self.function_declarations_stack[-1]:
                body_top.append(FunctionDeclarationStmt(item, location=None))
        body_top += stmts

        return Program(
            body_top
        )
    
    def name_mangle(self, name : str, param_types : list[Datatypes]) -> str:
        type_str = "-"
        for param_type in param_types:
            match param_type:
                case Datatypes.INT:
                    type_str += "i"
                case Datatypes.FLOAT:
                    type_str += "f"
                case Datatypes.STRING:
                    type_str += "s"
                case _:
                    raise TypeError(f"Could not find datatype {param_type}")
            type_str += "-"
        return name + type_str

    # MARK: Scope helpers

    def _enter_scope(self):
        self.scope = Scope(parent=self.scope)

    def _exit_scope(self):
        self.scope = self.scope.parent

    def _next_modifier(self, name) -> int:
        if self.scope.parent is not None and self.scope.parent.check_exists(name):
            outer_variable = self.scope.parent.resolve(name)
            return outer_variable.modifier + 1
        return 0

    # MARK: Statements

    def visit_function_stmt(self, stmt : Function):
        func_name = self.name_mangle(stmt.name.lexeme, [item[1] for item in stmt.params])
        self.function_return_stack.append(stmt.datatype)
        self.function_is_returned_stack.append(False)

        if not self.scope.check_function_exists_in_scope(func_name):
            if self.scope.check_exists_in_scope(func_name):
                raise TypeError(
                    f"Function with signature {self._signature_str(func_name)} conflicts with variable already in scope",
                    *stmt.location,
                )
            self.scope.define_funct(func_name, stmt.datatype)

        self._enter_scope()

        for param, param_type in stmt.params:
            name = self._name_str(param)
            modifier = self._next_modifier(name)
            self.scope.define(param.lexeme, Variable(name, param_type, modifier))

        self.current_function_stack.append(func_name)
        body = stmt.body.accept(self)
        self.current_function_stack.pop()

        self._exit_scope()

        if self.function_is_returned_stack[-1] is False:
            if stmt.datatype is None:
                body.body.append(Return(None, location=stmt.location))
                self.function_is_returned_stack[-1] = True
            else:
                raise TypeError(
                    f"Function with signature {self._signature_str(func_name)} does not return [with return datatype {stmt.datatype}]",
                    *stmt.location,
                )

        self.function_is_returned_stack.pop()
        self.function_return_stack.pop()

        self.function_declarations_stack[-1].append(func_name)
        return Function(func_name, stmt.params, stmt.datatype, body, location=stmt.location)

    def visit_return_stmt(self, stmt):
        new_expr = stmt.expression.accept(self) if stmt.expression else None

        if len(self.function_is_returned_stack) == 0:
            # trying to return from outermost scope
            raise TypeError(f"Return statement attempts to return from outermost scope", *stmt.location)
        
        self.function_is_returned_stack[-1] = True
        if (new_expr.datatype if new_expr else None) is not self.function_return_stack[-1]:
            raise TypeError(f"Type of expression in return ({new_expr.datatype}) does not agree with expected datatype {self.function_return_stack[-1]}", *stmt.location)
        
        return Return(new_expr, location=stmt.location)

    def visit_compound_stmt(self, stmt):
        new_block = stmt.block.accept(self)
        return Compound(new_block, location=stmt.location)

    def visit_block_stmts(self, stmt):
        self._enter_scope()
        self.function_declarations_stack.append([])

        for item in stmt.body:
            if isinstance(item, Function):
                self._forward_declare_function(item)

        new_body = [item.accept(self) for item in stmt.body]
        new_declarations = self.function_declarations_stack.pop()
        body_top = []
        for item in new_declarations:
            body_top.append(FunctionDeclarationStmt(item, location=stmt.location))
        body_top += new_body
        self._exit_scope()
        return Block(body_top, location=stmt.location)
    
    def visit_functiondeclarationstmt_stmt(self, expr):
        return expr # also stub

    def visit_variabledeclaration_stmt(self, stmt):
        name = self._name_str(stmt.name)

        if self.scope.check_exists_in_scope(name):
            print(self.scope.variables)
            raise TypeError(
                f"Variable '{name}' is already declared in this scope",
                *stmt.location,
            )

        modifier = self._next_modifier(name)

        self.scope.define(name, Variable(name, None, modifier))

        new_init = stmt.init.accept(self) if stmt.init is not None else None

        datatype = new_init.datatype if new_init is not None else None
        self.scope.update(name, Variable(name, datatype, modifier))

        return VariableDeclaration(
            stmt.name,
            new_init,
            location=stmt.location,
        )

    def visit_expression_stmt(self, stmt):
        new_expr = stmt.expression.accept(self)
        return Expression(new_expr, location=stmt.location)

    def visit_ifstmt_stmt(self, stmt):
        new_cond = stmt.expression.accept(self)
        new_then = stmt.then.accept(self)
        new_else = stmt.Else.accept(self) if stmt.Else else None
        return IfStmt(
            new_cond,
            new_then,
            new_else,
            location=stmt.location,
        )

    def visit_while_stmt(self, stmt):
        new_cond = stmt.condition.accept(self)
        new_body = stmt.body.accept(self)
        return While(
            new_cond,
            new_body,
            stmt.label,
            location=stmt.location,
        )

    def visit_dowhile_stmt(self, stmt):
        new_cond = stmt.condition.accept(self)
        new_body = stmt.body.accept(self)
        return DoWhile(
            new_cond,
            new_body,
            stmt.label,
            location=stmt.location,
        )

    def visit_break_stmt(self, stmt):
        return Break(stmt.label, location=stmt.location)

    def visit_continue_stmt(self, stmt):
        return Continue(stmt.label, location=stmt.location)

    def visit_null_stmt(self, stmt):
        return stmt

    def visit_inbuiltstatementnoarg_stmt(self, expr):
        return expr

    def visit_sendstatement_stmt(self, expr: SendStatement):
        name: Expr = expr.name.accept(self)

        if name.datatype is not Datatypes.STRING:
            raise TypeError(
                "Channel name for send statement must be a string",
                *expr.location,
            )

        data = expr.data.accept(self)
        return SendStatement(
            name,
            data,
            location=expr.location,
        )
    
    def visit_inbuiltprocedurearg1_stmt(self, expr : InbuiltProcedureArg1):
        val = expr.val.accept(self)
        obj = InbuiltProcedureArg1(expr.type, val, location=expr.location)
        match obj.type:
            case TokenType.SET_SPLITTER:
                if val.datatype is not Datatypes.STRING:
                    raise TypeError("The parameter for setting a splitter must always be a string", *expr.location)
            case TokenType.PUSH:
                pass # can be INT, or STR, and thats all we have anyway

        return obj

    # MARK: Expressions

    def visit_functioncall_expr(self, expr : FunctionCall):
        name = expr.name
        params = [param.accept(self) for param in expr.params]
        param_types = [param.datatype for param in params]
        name = self.name_mangle(name, param_types)

        if not self.scope.check_function_exists(name):
            raise TypeError(f"Could not find function with signature {self._signature_str(name)}", *expr.location)
        
        caller = self.current_function_stack[-1] if self.current_function_stack else "<global>"
        self.call_graph.setdefault(caller, set()).add(name)
        
        obj = FunctionCall(
            name,
            params,
            location=expr.location
        )

        obj.datatype = self.scope.resolve_function(name)

        return obj

    def visit_constant_expr(self, expr: Constant):
        val = Constant(
            expr.value,
            location=expr.location,
        )

        if expr.value.type is TokenType.STRING:
            val.datatype = Datatypes.STRING
        elif expr.value.type is TokenType.INT:
            val.datatype = Datatypes.INT
        elif expr.value.type is TokenType.FLOAT:
            val.datatype = Datatypes.FLOAT

        return val

    def visit_var_expr(self, expr: Var):
        name = self._name_str(expr.name)

        if not self.scope.check_exists(name):
            raise TypeError(
                f"Variable '{name}' is not defined",
                *expr.location,
            )

        val = Var(
            expr.name,
            location=expr.location,
        )

        variable = self.scope.resolve(name)
        val.datatype = variable.type
        return val

    def visit_assign_expr(self, expr: Assign):
        name = self._name_str(expr.name)

        if not self.scope.check_exists(name):
            raise TypeError(
                f"Cannot assign to undefined variable '{name}'",
                *expr.location,
            )

        new_value = expr.value.accept(self)
        if not new_value.datatype:
            print(new_value)

        existing_variable = self.scope.resolve(name)
        existing_type = existing_variable.type

        if existing_type is not None and new_value.datatype != existing_type:
            print(new_value)
            raise TypeError(
                f"Cannot assign {new_value.datatype.name} to variable '{name}' "
                f"of type {existing_type.name}",
                *expr.location,
            )

        self.scope.update(
            name,
            Variable(name, new_value.datatype, existing_variable.modifier),
        )

        val = Assign(
            expr.name,
            new_value,
            location=expr.location,
        )

        val.datatype = new_value.datatype
        return val

    def visit_assigncompound_expr(self, expr: AssignCompound):
        name = (
            expr.target.name.lexeme
            if hasattr(expr.target.name, "lexeme")
            else expr.target.name
        )

        if not self.scope.check_exists(name):
            raise TypeError(
                f"Cannot assign to undefined variable '{name}'",
                *expr.location,
            )

        new_target = expr.target.accept(self)
        new_value = expr.value.accept(self)

        if (new_target.datatype is Datatypes.STRING or new_value.datatype is Datatypes.STRING):
            if expr.operator.type is not TokenType.PLUS_EQUALS:
                raise TypeError(
                    f"Cannot perform compound operation '{expr.operator.lexeme}' on strings",
                    *expr.location,
                )
            result_type = Datatypes.STRING
        elif (new_target.datatype is Datatypes.FLOAT or new_value.datatype is Datatypes.FLOAT):
            result_type = Datatypes.FLOAT
        else:
            result_type = Datatypes.INT

        if (
            new_target.datatype is not None
            and result_type != new_target.datatype
        ):
            raise TypeError(
                f"Compound assignment result type {result_type.name} does not match "
                f"variable '{name}' of type {new_target.datatype.name}",
                *expr.location,
            )

        existing_variable = self.scope.resolve(name)
        self.scope.update(
            name,
            Variable(name, result_type, existing_variable.modifier),
        )

        val = AssignCompound(
            new_target,
            expr.operator,
            new_value,
            location=expr.location,
        )
        val.datatype = result_type
        return val

    def visit_unaryexpr_expr(self, expr: UnaryExpr):
        new_operand = expr.expression.accept(self)

        if new_operand.datatype is Datatypes.STRING:
            raise TypeError(
                f"String operands do not support unary operations {expr.operator}",
                *expr.location,
            )

        val = UnaryExpr(
            expr.operator,
            new_operand,
            location=expr.location,
        )
        val.datatype = new_operand.datatype
        return val

    def visit_binaryexpr_expr(self, expr: BinaryExpr):
        new_left = expr.left.accept(self)
        new_right = expr.right.accept(self)

        val = BinaryExpr(
            expr.operator,
            new_left,
            new_right,
            location=expr.location,
        )

        if (
            new_left.datatype is Datatypes.STRING
            or new_right.datatype is Datatypes.STRING
        ):
            if expr.operator.type not in  (TokenType.PLUS, TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
                raise TypeError(
                    f"Cannot perform operation '{expr.operator.lexeme}' on strings",
                    *expr.location,
                )
            if expr.operator.type in (TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
                val.datatype = Datatypes.INT
            else:
                val.datatype = Datatypes.STRING
        else:
            if (
                new_left.datatype is Datatypes.FLOAT
                or new_right.datatype is Datatypes.FLOAT
            ):
                val.datatype = Datatypes.FLOAT
            else:
                val.datatype = Datatypes.INT

        return val

    def visit_updateexpr_expr(self, expr: UpdateExpr):
        new_arg = expr.argument.accept(self)

        if new_arg.datatype not in (Datatypes.INT, Datatypes.FLOAT):
            raise TypeError(
                "String operands do not support update expressions (++ / --)",
                *expr.location,
            )

        val = UpdateExpr(
            expr.operator,
            new_arg,
            expr.isPrefix,
            location=expr.location,
        )
        val.datatype = new_arg.datatype
        return val

    def visit_conditional_expr(self, expr: Conditional):
        new_cond = expr.condition.accept(self)
        new_v1 = expr.val1.accept(self)
        new_v2 = expr.val2.accept(self)

        if new_v1.datatype != new_v2.datatype:
            raise TypeError(
                f"Branches of conditional expression must have the same type, "
                f"got {new_v1.datatype.name} and {new_v2.datatype.name}",
                *expr.location,
            )

        val = Conditional(
            new_cond,
            new_v1,
            new_v2,
            location=expr.location,
        )
        val.datatype = new_v1.datatype
        return val
    
    def visit_inbuiltfunctionarg0_expr(self, expr : InbuiltFunctionArg0):
        obj = InbuiltFunctionArg0(expr.type, location=expr.location)
        match expr.type:
            case TokenType.POP | TokenType.PEEK:
                obj.datatype = Datatypes.STRING
            case TokenType.WORLDTIME:
                obj.datatype = Datatypes.INT
            case _:
                raise TypeError(f"Function not found: {expr.type}")
        return obj
    
    def visit_inbuiltfunctionarg2_expr(self, expr: InbuiltFunctionArg2):
        val1: Expr = expr.val1.accept(self)
        val2: Expr = expr.val2.accept(self)
        obj = InbuiltFunctionArg2(expr.type, val1, val2, location=expr.location)
        
        if expr.type is TokenType.SPLIT:
            if val1.datatype is not Datatypes.STRING:
                raise TypeError("Can only split a string [first param must be a STRING]")
            if val2.datatype is not Datatypes.INT:
                raise TypeError("Can only split an integeral part from string [second param must be a INT]")
            obj.datatype = Datatypes.STRING
        
        return obj            
    
    def visit_inbuiltfunctionarg1_expr(self, expr: InbuiltFunctionArg1):
        val: Expr = expr.val.accept(self)

        exp = InbuiltFunctionArg1(
            expr.type,
            val,
            location=expr.location,
        )

        if expr.type in {TokenType.ROUND, TokenType.FLOOR, TokenType.CEIL}:
            if val.datatype not in (Datatypes.INT, Datatypes.FLOAT):
                raise TypeError(
                    f"Cannot use mathematical function {expr.type} with object of type {val.datatype}",
                    *expr.location,
                )
            exp.datatype = Datatypes.INT

        elif expr.type in {TokenType.LISTEN, TokenType.POLL}:
            if val.datatype is not Datatypes.STRING:
                raise TypeError(
                    f"Cannot use function {expr.type} with object of type {val.datatype}",
                    *expr.location,
                )
            exp.datatype = Datatypes.STRING

        elif expr.type is TokenType.STRING_CAST:
            exp.datatype = Datatypes.STRING

        elif expr.type is TokenType.INT_CAST:
            exp.datatype = Datatypes.INT

        elif expr.type is TokenType.FLOAT_CAST:
            exp.datatype = Datatypes.FLOAT
        
        elif expr.type in {TokenType.LENGTH, TokenType.SPLITCOUNT}:
            expr.datatype = Datatypes.INT
        
        if expr.type in (TokenType.STRING_CAST, TokenType.INT_CAST, TokenType.FLOAT_CAST) and not self.explicit_conversions:
            obj = exp.val
            obj.datatype = exp.datatype
            return obj
        
        return exp
    
    def visit_stringslice_expr(self, expr: StringSlice):
        value = expr.value.accept(self)
        left = expr.left.accept(self) if expr.left else None
        right = expr.right.accept(self) if expr.right else None
        obj = StringSlice(value, left, right, location=expr.location)


        if value.datatype is not Datatypes.STRING:
            raise TypeError("Can only slice a string [value must be a STRING]")
        if left and left.datatype is not Datatypes.INT:
            raise TypeError("String slice bound must be an INT [left must be a INT]")
        if right and right.datatype is not Datatypes.INT:
            raise TypeError("String slice bound must be an INT [right must be a INT]")

        obj.datatype = Datatypes.STRING
        return obj

    def visit_stringindex_expr(self, expr: StringIndex):
        value = expr.value.accept(self)
        idx = expr.idx.accept(self)
        obj = StringIndex(value, idx, location=expr.location)

        if value.datatype is not Datatypes.STRING:
            raise TypeError("Can only index a string [value must be a STRING]")
        if idx.datatype is not Datatypes.INT:
            raise TypeError("String index must be an INT [idx must be a INT]")

        obj.datatype = Datatypes.STRING
        return obj