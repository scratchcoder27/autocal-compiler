from ast_nodes import Block, Function, VariableDeclaration, Program
from stmt import *
from expr import *

class DeadFunctionEliminationPass(StmtVisitor, ExprVisitor):
    def __init__(self, call_graph: dict[str, set[str]]):
        self.call_graph = call_graph
        self.reachable: set[str] = self._compute_reachable()

    def _compute_reachable(self) -> set[str]:
        reachable = set()
        worklist = list(self.call_graph.get("<global>", set()))
        while worklist:
            name = worklist.pop()
            if name in reachable:
                continue
            reachable.add(name)
            worklist.extend(self.call_graph.get(name, set()))
        return reachable

    def _is_dead(self, func_name: str) -> bool:
        return func_name not in self.reachable

    def eliminate(self, program):
        new_stmts = []
        for stmt in program.stmts:
            if isinstance(stmt, Function) and self._is_dead(stmt.name):
                continue
            if isinstance(stmt, FunctionDeclarationStmt) and self._is_dead(stmt.name):
                continue
            new_stmts.append(stmt.accept(self))
        return Program(new_stmts)

    # MARK: Statements

    def visit_function_stmt(self, stmt: Function):
        body = stmt.body.accept(self)
        return Function(stmt.name, stmt.params, stmt.datatype, body, location=stmt.location)

    def visit_return_stmt(self, stmt):
        new_expr = stmt.expression.accept(self) if stmt.expression else None
        return Return(new_expr, location=stmt.location)

    def visit_compound_stmt(self, stmt):
        new_block = stmt.block.accept(self)
        return Compound(new_block, location=stmt.location)

    def visit_block_stmts(self, stmt):
        new_body = []
        for item in stmt.body:
            if isinstance(item, Function) and self._is_dead(item.name):
                continue
            if isinstance(item, FunctionDeclarationStmt) and self._is_dead(item.name):
                continue
            new_body.append(item.accept(self))
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

    def visit_while_stmt(self, stmt: While):
        new_cond = stmt.condition.accept(self)
        new_body = stmt.body.accept(self)
        return While(
            new_cond,
            new_body,
            stmt.label,
            location=stmt.location,
        )

    def visit_dowhile_stmt(self, stmt: DoWhile):
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

    def visit_inbuiltprocedurearg1_stmt(self, stmt: InbuiltProcedureArg1):
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

    def visit_functiondeclarationstmt_stmt(self, stmt):
        return stmt

    # MARK: Expressions

    def visit_functioncall_expr(self, expr: FunctionCall):
        params = [param.accept(self) for param in expr.params]
        obj = FunctionCall(
            name=expr.name,
            params=params,
            location=expr.location,
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

    def visit_unaryexpr_expr(self, expr):
        new_operand = expr.expression.accept(self)
        obj = UnaryExpr(
            expr.operator,
            new_operand,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

    def visit_binaryexpr_expr(self, expr):
        new_left = expr.left.accept(self)
        new_right = expr.right.accept(self)
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

    def visit_inbuiltfunctionarg0_expr(self, expr: InbuiltFunctionArg0):
        obj = InbuiltFunctionArg0(
            expr.type,
            location=expr.location,
        )
        obj.datatype = expr.datatype
        return obj

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