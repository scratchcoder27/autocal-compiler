from ast_nodes import Block, Function, VariableDeclaration, Program
from stmt import *
from expr import *
import operator


class SemanticError(Exception):
    def __init__(
        self,
        message: str,
        file_no: int | None = None,
        line_no: int | None = None,
    ):
        super().__init__(message)
        self.file_no = file_no
        self.line_no = line_no

        

class ConstantFoldingPass(StmtVisitor, ExprVisitor):
    def __init__(self):
        self.OPERATIONS = {
            TokenType.PLUS: operator.add,
            TokenType.MINUS: operator.sub,
            TokenType.STAR: operator.mul,
            TokenType.SLASH: operator.truediv,
        }


    def fold(self, program):
        return Program(
            [stmt.accept(self) for stmt in program.stmts],
        )
    
    # MARK: Statments
    def visit_function_stmt(self, stmt : Function):
        body = stmt.body.accept(self)
        return Function(stmt.name, stmt.params, stmt.datatype, body, location=stmt.location)

    def visit_return_stmt(self, stmt):
        new_expr = stmt.expression.accept(self) if stmt.expression else None
        return Return(new_expr, location=stmt.location)

    def visit_compound_stmt(self, stmt):
        new_block = stmt.block.accept(self)
        return Compound(new_block, location=stmt.location)

    def visit_block_stmts(self, stmt):
        new_body = [item.accept(self) for item in stmt.body]
        return Block(new_body, location=stmt.location)

    def visit_variabledeclaration_stmt(self, stmt):
        new_init = stmt.init.accept(self) if stmt.init is not None else None
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

    def visit_while_stmt(self, stmt : While):
        new_cond = stmt.condition.accept(self)

        new_body = stmt.body.accept(self)

        return While(
            new_cond,
            new_body,
            stmt.label,
            location=stmt.location,
        )

    def visit_dowhile_stmt(self, stmt : DoWhile):
        new_cond = stmt.condition.accept(self)

        new_body = stmt.body.accept(self)

        return DoWhile(
            new_cond,
            new_body,
            stmt.label,
            location=stmt.location,
        )

    def visit_break_stmt(self, stmt):
       return stmt

    def visit_continue_stmt(self, stmt):
        return stmt
    
    def visit_inbuiltprocedurearg1_stmt(self, stmt : InbuiltProcedureArg1):
        expr = stmt.val.accept(self)
        return InbuiltProcedureArg1(stmt.type, expr, location=stmt.location)

    def visit_null_stmt(self, stmt):
        return stmt

    def visit_functioncall_stmt(self, stmt):
        return stmt

    def visit_inbuiltstatementnoarg_stmt(self, stmt):
        return stmt

    def visit_sendstatement_stmt(self, stmt: SendStatement):
        name = stmt.name.accept(self)
        data = stmt.data.accept(self)
        return SendStatement(
            name,
            data,
            location=stmt.location,
        )

    # MARK: Expressions

    def visit_functioncall_expr(self, expr : FunctionCall):
        params = [param.accept(self) for param in expr.params]
        obj = FunctionCall(
            name = expr.name,
            params = params,
            location=expr.location
        )
        obj.datatype = expr.datatype
        return obj

    def visit_constant_expr(self, expr):
        obj = Constant(
            expr.value,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_var_expr(self, expr):
        obj = Var(
            expr.name,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_assign_expr(self, expr):
        new_value = expr.value.accept(self)
        obj = Assign(
            expr.name,
            new_value,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_assigncompound_expr(self, expr):
        new_target = expr.target.accept(self)
        new_value = expr.value.accept(self)
        obj = AssignCompound(
            new_target,
            expr.operator,
            new_value,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_unaryexpr_expr(self, expr : UnaryExpr):
        new_operand = expr.expression.accept(self)

        if isinstance(expr.expression, Constant):
            val = None
            if expr.operator.type is TokenType.MINUS:
                if expr.datatype in (Datatypes.INT, Datatypes.FLOAT):
                    val = -int(expr.expression.value.literal)
                    val = int(val) if expr.datatype is Datatypes.INT else float(val)

                    val = Token(TokenType.INT if expr.datatype is Datatypes.INT else TokenType.FLOAT, str(val), val, expr.location[0], expr.location[1])
            
            if val and isinstance(val, Token):
                return Constant(val, location=expr.location)

        obj = UnaryExpr(
            expr.operator,
            new_operand,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_binaryexpr_expr(self, expr : BinaryExpr):
        new_left : Expr = expr.left.accept(self)
        new_right : Expr = expr.right.accept(self)

        if isinstance(new_left, Constant) and isinstance(new_right, Constant):
            val = None
            if expr.datatype is Datatypes.STRING:
                if expr.operator.type is TokenType.PLUS:
                    new_str = str(new_left.value.lexeme.strip("\"")) + str(new_right.value.lexeme.strip("\""))
                    val = Token(TokenType.STRING, lexeme=f"\"{new_str}\"", literal=new_str, line_no=expr.location[0], file_no=expr.location[1])

            elif expr.datatype in(Datatypes.FLOAT, Datatypes.INT):
                val = None
                val1 = int(new_left.value.literal) if expr.datatype is Datatypes.INT else float(new_left.value.literal)
                val2 = int(new_right.value.literal) if expr.datatype is Datatypes.INT else float(new_right.value.literal)

                try:
                    if expr.operator.type in self.OPERATIONS:
                        val = self.OPERATIONS[expr.operator.type](val1, val2)
                        val = int(val) if expr.datatype is Datatypes.INT else float(val)
                except (ValueError, ZeroDivisionError) as e:
                    if isinstance(e, ZeroDivisionError):
                        raise SemanticError("Division by zero is not allowed", expr.location[0], expr.location[1])
                    val = None
                
                if val:
                    val = Token(TokenType.INT if expr.datatype is Datatypes.INT else TokenType.FLOAT, str(val), val, line_no=expr.location[0], file_no=expr.location[1])
                
            if val:
                obj = Constant(
                    value=val,
                    location=expr.location
                )
                obj.datatype = expr.datatype
                return obj

        obj = BinaryExpr(
            expr.operator,
            new_left,
            new_right,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_updateexpr_expr(self, expr):
        new_arg = expr.argument.accept(self)
        obj = UpdateExpr(
            expr.operator,
            new_arg,
            expr.isPrefix,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_conditional_expr(self, expr):
        new_cond = expr.condition.accept(self)
        new_v1 = expr.val1.accept(self)
        new_v2 = expr.val2.accept(self)
        obj = Conditional(
            new_cond,
            new_v1,
            new_v2,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_inbuiltfunctionarg1_expr(self, expr: InbuiltFunctionArg1):
        val = expr.val.accept(self)
        obj = InbuiltFunctionArg1(
            expr.type,
            val,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj
    
    def visit_inbuiltfunctionarg2_expr(self, expr: InbuiltFunctionArg2):
        val1 = expr.val1.accept(self)
        val2 = expr.val2.accept(self)
        obj = InbuiltFunctionArg2(
            expr.type,
            val1,
            val2,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj
    
    
    def visit_inbuiltfunctionarg0_expr(self, expr : InbuiltFunctionArg0):
        obj = InbuiltFunctionArg0(
            expr.type,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj
    
    
    def visit_functiondeclarationstmt_stmt(self, expr):
        return expr
    
    def visit_stringslice_expr(self, expr: StringSlice):
        value = expr.value.accept(self)
        left = expr.left.accept(self) if expr.left else None
        right = expr.right.accept(self) if expr.right else None
        obj = StringSlice(
            value,
            left,
            right,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_stringindex_expr(self, expr: StringIndex):
        value = expr.value.accept(self)
        idx = expr.idx.accept(self)
        obj = StringIndex(
            value,
            idx,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj