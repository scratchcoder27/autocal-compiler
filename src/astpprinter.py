from ast_nodes import Function
from stmt import *
from expr import *
from enum import Enum, auto

class Datatypes(Enum):
    NUMBER = auto()
    STRING = auto()

class AstPrinter(StmtVisitor, ExprVisitor):
    def __init__(self):
        self.level = 0
        self.show_types = False

    def print(self, program, show_types=False):
        self.show_types = show_types
        results = []
        for stmt in program.stmts:
            results.append(stmt.accept(self))
        return "\n".join(results)

    def _indent(self):
        return "    " * self.level

    def _type_str(self, node):
        if self.show_types and hasattr(node, 'datatype') and node.datatype is not None:
            return f" [type: {node.datatype.name}]"
        return " <untyped> "

    #  Statements 

    def visit_function_stmt(self, stmt : Function):
        indent = self._indent()

        param_str = ""
        for item in stmt.params:
            param_str += f"{item[0]} [{item[1]}], "
        
        self.level += 3
        body = stmt.body.accept(self)
        self.level -= 3

        return (
            f"{indent}Function Definition(\n"
            f"{indent}        name=\"{stmt.name}\",\n"
            f"{indent}        params=({param_str})\n"
            f"{indent}        returns=({stmt.datatype})\n"
            f"{indent}        (\n{body}\n"
            f"{indent}        )"
        )
    
    def visit_functiondeclarationstmt_stmt(self, stmt):
        return f"{self._indent()}Function Declaration (Name: {stmt.name})"


    def visit_break_stmt(self, expr):
        return f"{self._indent()}Break Statement (Label: {expr.label})"

    def visit_continue_stmt(self, expr):
        return f"{self._indent()}Continue Statement (Label: {expr.label})"

    def visit_dowhile_stmt(self, expr):
        indent = self._indent()

        self.level += 1
        testexp = expr.condition.accept(self)
        stmt = expr.body.accept(self)
        label = expr.label if expr.label else "unlabelled"
        self.level -= 1

        return (
            f"{indent}Do(\n"
            f"{stmt}"
            f"{indent}While(\n"
            f"{testexp}',\n"
            f"{indent}) <label: {label}>"
        )

    def visit_while_stmt(self, expr):
        indent = self._indent()

        self.level += 1
        testexp = expr.condition.accept(self)
        stmt = expr.body.accept(self)
        label = expr.label if expr.label else "unlabelled"
        self.level -= 1

        return (
            f"{indent}While(\n"
            f"{testexp}',\n"
            f"{indent}Do(\n"
            f"{stmt}"
            f"{indent})  <label: {label}>"
        )

    def visit_block_stmts(self, expr):
        indent = self._indent()

        self.level += 1
        body = []
        for item in expr.body:
            body.append(item.accept(self))
        self.level -= 1

        return (
            f"{indent}Compound Statement(\n"
            f"{"\n".join(body)}\n"
            f"{indent})"
        )

    def visit_return_stmt(self, stmt):
        indent = self._indent()

        self.level += 1
        if stmt.expression:
            expr = stmt.expression.accept(self)
        else:
            expr = f"{indent} <None>"
        self.level -= 1

        return (
            f"{indent}Return(\n"
            f"{expr}\n"
            f"{indent})"
        )

    def visit_compound_stmt(self, expr):
        return expr.block.accept(self)

    def visit_variabledeclaration_stmt(self, expr):
        indent = self._indent()

        self.level += 1
        if expr.init is not None:
            val = expr.init.accept(self)
        else:
            val = f"{indent}    No definition"
        self.level -= 1

        return (
            f"{indent}Declare(\n{indent}    name='{expr.name.lexeme}',\n"
            f"{val}\n"
            f"{indent})"
        )

    def visit_ifstmt_stmt(self, expr):
        indent = self._indent()

        self.level += 1
        testexp = expr.expression.accept(self)
        if_stmt = expr.then.accept(self)
        if expr.Else:
            else_stmt = expr.Else.accept(self)
            else_stmt = f"{indent}) Else:\n{else_stmt}\n{indent})"
        else:
            else_stmt = ""
        self.level -= 1

        return (
            f"{indent}If(\n"
            f"{testexp}',\n"
            f"{indent}Then(\n"
            f"{if_stmt}"
            f"{else_stmt}"
            f"{indent})"
        )

    def visit_expression_stmt(self, expr):
        return expr.expression.accept(self)

    def visit_null_stmt(self, expr):
        return f"{self._indent()}<Null expr>"
    
        
    def visit_inbuiltstatementnoarg_stmt(self, expr : InbuiltStatementNoarg):
        return f"{self._indent()}<{expr.type} statement>"
    
    def visit_sendstatement_stmt(self, expr : SendStatement):
        indent = self._indent()

        self.level += 1
        data = expr.data.accept(self)
        name = expr.name.accept(self)
        self.level -= 1

        return (
            f"{indent}Send(\n{name},\n"
            f"{data}\n"
            f"{indent})"
        )
    
    def visit_inbuiltprocedurearg1_stmt(self, expr : InbuiltProcedureArg1):
        indent = self._indent()

        self.level += 1
        val = expr.val.accept(self)
        self.level -= 1

        return (
            f"{indent}Inbuild Procedure  type:{expr.type}(\n"
            f"{val}\n"
            f"{indent})\n"
        )

    #  Expressions 

    def visit_var_expr(self, expr):
        return f"{self._indent()}      expr.name.literal{self._type_str(expr)}"

    def visit_assign_expr(self, expr):
        indent = self._indent()

        self.level += 1
        name = expr.name.name
        val = expr.value.accept(self)
        self.level -= 1

        return (
            f"{indent}Assign {self._type_str(expr)}(\n"
            f"{indent}    '{name}'\n{indent}) to\n"
            f"{val}\n"
            f"{indent})\n"
        )

    def visit_constant_expr(self, expr):
        indent = self._indent()

        value = (
            expr.value.literal
            if expr.value.literal is not None
            else expr.value.lexeme
        )

        type_str = self._type_str(expr) if self.show_types else f" [type: {expr.datatype}]"
        return f"{indent}    Constant({value}){type_str}"

    def visit_unaryexpr_expr(self, expr):
        indent = self._indent()

        self.level += 1
        operand = expr.expression.accept(self)
        self.level -= 1

        return (
            f"{indent}UnaryExpr{self._type_str(expr)}(\n"
            f"{indent}    operator='{expr.operator.lexeme}',\n"
            f"{indent}    operand=\n"
            f"{operand}\n"
            f"{indent})"
        )

    def visit_binaryexpr_expr(self, expr):
        indent = self._indent()

        self.level += 1
        left = expr.left.accept(self)
        right = expr.right.accept(self)
        self.level -= 1

        return (
            f"{indent}BinaryExpr{self._type_str(expr)}(\n"
            f"{indent}    operator='{expr.operator.lexeme}',\n"
            f"{indent}    left=\n"
            f"{left}\n"
            f"{indent}    right=\n"
            f"{right}\n"
            f"{indent})"
        )

    def visit_assigncompound_expr(self, expr):
        indent = self._indent()

        self.level += 1
        target = expr.target.accept(self)
        value = expr.value.accept(self)
        self.level -= 1

        return (
            f"{indent}AssignCompound{self._type_str(expr)}(\n"
            f"{indent}    operator='{expr.operator.lexeme}',\n"
            f"{indent}    target=\n"
            f"{target}\n"
            f"{indent}    value=\n"
            f"{value}\n"
            f"{indent})"
        )

    def visit_updateexpr_expr(self, expr):
        indent = self._indent()

        self.level += 1
        argument = expr.argument.accept(self)
        self.level -= 1

        expr_type = "Prefix" if expr.isPrefix else "Postfix"

        return (
            f"{indent}UpdateExpr{self._type_str(expr)}(\n"
            f"{indent}    type='{expr_type}',\n"
            f"{indent}    operator='{expr.operator.lexeme}',\n"
            f"{indent}    argument=\n"
            f"{argument}\n"
            f"{indent})"
        )

    def visit_conditional_expr(self, expr):
        indent = self._indent()

        self.level += 1
        cond = expr.condition.accept(self)
        v1 = expr.val1.accept(self)
        v2 = expr.val2.accept(self)
        self.level -= 1

        return (
            f"{indent}ConditionalOperator{self._type_str(expr)}(\n"
            f"{indent}    condition=\n"
            f"{cond}\n"
            f"{indent}    value true=\n"
            f"{v1}\n"
            f"{indent}    value false=\n"
            f"{v2}\n"
            f"{indent})"
        )

    def visit_functioncall_expr(self, expr : FunctionCall):
        indent = self._indent()
        
        name = expr.name
        self.level += 1
        params = [param.accept(self) for param in expr.params]
        self.level -= 1

        return (
            f"{indent}FunctionCall(\n"
            f"{indent}    name:    '{name}'\n{indent}) body: (\n"
            f"{"\n".join(params)}\n"
            f"{indent})\n"
        )
    
    def visit_inbuiltfunctionarg0_expr(self, expr : InbuiltFunctionArg0):
        return f"Inbuilt function <type: {expr.type}>"
    
    def visit_inbuiltfunctionarg1_expr(self, expr : InbuiltFunctionArg1):
        indent = self._indent()

        name = expr.type
        self.level += 1
        val = expr.val.accept(self)
        self.level -= 1

        return (
            f"{indent}Inbuilt Function(\n"
            f"{indent}    '{name}'\n{indent}) body: (\n"
            f"{val}\n"
            f"{indent})\n"
        )
    
    def visit_inbuiltfunctionarg2_expr(self, expr : InbuiltFunctionArg2):
        indent = self._indent()

        name = expr.type
        self.level += 1
        val1 = expr.val1.accept(self)
        val2 = expr.val2.accept(self)
        self.level -= 1

        return (
            f"{indent}Inbuilt Function(\n"
            f"{indent}    '{name}'\n{indent}) body: (\n"
            f"{val1}\n"
            f"{val2}\n"
            f"{indent})\n"
        )
    
    def visit_stringslice_expr(self, expr : StringSlice):
        indent = self._indent()

        self.level += 1
        val = expr.value.accept(self)
        left = expr.left.accept(self)
        right = expr.right.accept(self)
        self.level -= 1

        return (
            f"{indent}String Slice{self._type_str(expr)}(\n"
            f"{indent}    string=\n"
            f"{val}\n"
            f"{indent}    left=\n"
            f"{left}\n"
            f"{indent}    right=\n"
            f"{right}\n"
            f"{indent})"
        )

    def visit_stringindex_expr(self, expr : StringIndex):
        indent = self._indent()

        self.level += 1
        val = expr.value.accept(self)
        idx = expr.idx.accept(self)
        self.level -= 1

        return (
            f"{indent}String Index{self._type_str(expr)}(\n"
            f"{indent}    string=\n"
            f"{val}\n"
            f"{indent}    idx=\n"
            f"{idx}\n"
            f"{indent})"
        )