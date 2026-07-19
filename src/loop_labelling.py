from ast_nodes import Block, Function, VariableDeclaration, Program
from stmt import *
from expr import *


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


class LoopLabellingPass(StmtVisitor, ExprVisitor):
    def __init__(self):
        self.loop_number = 0
        self.loop_stack = []

    def label(self, program):
        return Program(
            [stmt.accept(self) for stmt in program.stmts],
        )
    
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

    def visit_while_stmt(self, stmt):
        new_cond = stmt.condition.accept(self)

        self.loop_number += 1
        self.loop_stack.append(self.loop_number)

        new_body = stmt.body.accept(self)

        self.loop_stack.pop()
        return While(
            new_cond,
            new_body,
            self.loop_number,
            location=stmt.location,
        )

    def visit_dowhile_stmt(self, stmt):
        new_cond = stmt.condition.accept(self)

        self.loop_number += 1
        self.loop_stack.append(self.loop_number)

        new_body = stmt.body.accept(self)

        self.loop_stack.pop()
        return DoWhile(
            new_cond,
            new_body,
            self.loop_number,
            location=stmt.location,
        )

    def visit_break_stmt(self, stmt):
        if not stmt.label:
            try:
                label = self.loop_stack[-1]
            except IndexError:
                raise SemanticError(
                    "Could not find matching while, do-while, or for loop for break statement",
                    *stmt.location,
                )
            return Break(label, location=stmt.location)

        return Break(stmt.label, location=stmt.location)

    def visit_continue_stmt(self, stmt):
        if not stmt.label:
            try:
                label = self.loop_stack[-1]
            except IndexError:
                raise SemanticError(
                    "Could not find matching while, do-while, or for loop for continue statement",
                    *stmt.location,
                )
            return Continue(label, location=stmt.location)

        return Continue(stmt.label, location=stmt.location)
    
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
        return FunctionCall(
            name = expr.name,
            params = params,
            location=expr.location
        )

    def visit_constant_expr(self, expr):
        return Constant(
            expr.value,
            location=expr.location,
        )

    def visit_var_expr(self, expr):
        return Var(
            expr.name,
            location=expr.location,
        )

    def visit_assign_expr(self, expr):
        new_value = expr.value.accept(self)
        return Assign(
            expr.name,
            new_value,
            location=expr.location,
        )

    def visit_assigncompound_expr(self, expr):
        new_target = expr.target.accept(self)
        new_value = expr.value.accept(self)
        return AssignCompound(
            new_target,
            expr.operator,
            new_value,
            location=expr.location,
        )

    def visit_unaryexpr_expr(self, expr):
        new_operand = expr.expression.accept(self)
        return UnaryExpr(
            expr.operator,
            new_operand,
            location=expr.location,
        )

    def visit_binaryexpr_expr(self, expr):
        new_left = expr.left.accept(self)
        new_right = expr.right.accept(self)
        return BinaryExpr(
            expr.operator,
            new_left,
            new_right,
            location=expr.location,
        )

    def visit_updateexpr_expr(self, expr):
        new_arg = expr.argument.accept(self)
        return UpdateExpr(
            expr.operator,
            new_arg,
            expr.isPrefix,
            location=expr.location,
        )

    def visit_conditional_expr(self, expr):
        new_cond = expr.condition.accept(self)
        new_v1 = expr.val1.accept(self)
        new_v2 = expr.val2.accept(self)
        return Conditional(
            new_cond,
            new_v1,
            new_v2,
            location=expr.location,
        )

    def visit_inbuiltfunctionarg1_expr(self, expr: InbuiltFunctionArg1):
        val = expr.val.accept(self)
        return InbuiltFunctionArg1(
            expr.type,
            val,
            location=expr.location,
        )
    
    def visit_inbuiltfunctionarg2_expr(self, expr: InbuiltFunctionArg2):
        val1 = expr.val1.accept(self)
        val2 = expr.val2.accept(self)
        return InbuiltFunctionArg2(
            expr.type,
            val1,
            val2,
            location=expr.location,
        )
    
    
    def visit_inbuiltfunctionarg0_expr(self, expr : InbuiltFunctionArg0):
        return expr
    
    
    def visit_functiondeclarationstmt_stmt(self, expr):
        return expr # stub, they don't exist yet in the AST
    
    def visit_stringslice_expr(self, expr: StringSlice):
        value = expr.value.accept(self)
        left = expr.left.accept(self) if expr.left else None
        right = expr.right.accept(self) if expr.right else None
        return StringSlice(
            value,
            left,
            right,
            location=expr.location,
        )

    def visit_stringindex_expr(self, expr: StringIndex):
        value = expr.value.accept(self)
        idx = expr.idx.accept(self)
        return StringIndex(
            value,
            idx,
            location=expr.location,
        )