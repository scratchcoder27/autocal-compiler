from __future__ import annotations
from abc import ABC, abstractmethod
from node import Node
from tokens import Token
from datatypes import Datatypes
from token_types import TokenType
from dataclasses import dataclass, field


class ExprVisitor(ABC):
    @abstractmethod
    def visit_constant_expr(self, expr):
        pass

    @abstractmethod
    def visit_unaryexpr_expr(self, expr):
        pass

    @abstractmethod
    def visit_binaryexpr_expr(self, expr):
        pass

    @abstractmethod
    def visit_var_expr(self, expr):
        pass

    @abstractmethod
    def visit_assign_expr(self, expr):
        pass

    @abstractmethod
    def visit_assigncompound_expr(self, expr):
        pass

    @abstractmethod
    def visit_updateexpr_expr(self, expr):
        pass

    @abstractmethod
    def visit_conditional_expr(self, expr):
        pass

    @abstractmethod
    def visit_inbuiltfunctionarg0_expr(self, expr):
        pass

    @abstractmethod
    def visit_inbuiltfunctionarg1_expr(self, expr):
        pass

    @abstractmethod
    def visit_inbuiltfunctionarg2_expr(self, expr):
        pass

    @abstractmethod
    def visit_functioncall_expr(self, expr):
        pass

    @abstractmethod
    def visit_stringslice_expr(self, expr):
        pass

    @abstractmethod
    def visit_stringindex_expr(self, expr):
        pass



@dataclass
class Expr(Node, ABC):
    datatype: Datatypes = field(init=False, default=None)
    @abstractmethod
    def accept(self, visitor):
        pass


@dataclass
class Constant(Expr):
    value: Token

    def accept(self, visitor):
        return visitor.visit_constant_expr(self)


@dataclass
class UnaryExpr(Expr):
    operator: Token
    expression: Expr

    def accept(self, visitor):
        return visitor.visit_unaryexpr_expr(self)


@dataclass
class BinaryExpr(Expr):
    operator: Token
    left: Expr
    right: Expr

    def accept(self, visitor):
        return visitor.visit_binaryexpr_expr(self)


@dataclass
class Var(Expr):
    name: Token

    def accept(self, visitor):
        return visitor.visit_var_expr(self)


@dataclass
class Assign(Expr):
    name: Expr
    value: Expr

    def accept(self, visitor):
        return visitor.visit_assign_expr(self)


@dataclass
class AssignCompound(Expr):
    target: Expr
    operator: Token
    value: Expr

    def accept(self, visitor):
        return visitor.visit_assigncompound_expr(self)


@dataclass
class UpdateExpr(Expr):
    operator: Token
    argument: Expr
    isPrefix: bool

    def accept(self, visitor):
        return visitor.visit_updateexpr_expr(self)


@dataclass
class Conditional(Expr):
    condition: Expr
    val1: Expr
    val2: Expr

    def accept(self, visitor):
        return visitor.visit_conditional_expr(self)


@dataclass
class InbuiltFunctionArg0(Expr):
    type: TokenType

    def accept(self, visitor):
        return visitor.visit_inbuiltfunctionarg0_expr(self)


@dataclass
class InbuiltFunctionArg1(Expr):
    type: TokenType
    val: Expr

    def accept(self, visitor):
        return visitor.visit_inbuiltfunctionarg1_expr(self)


@dataclass
class InbuiltFunctionArg2(Expr):
    type: TokenType
    val1: Expr
    val2: Expr

    def accept(self, visitor):
        return visitor.visit_inbuiltfunctionarg2_expr(self)


@dataclass
class FunctionCall(Expr):
    name: str
    params: list[Expr]

    def accept(self, visitor):
        return visitor.visit_functioncall_expr(self)


@dataclass
class StringSlice(Expr):
    value: Expr
    left: Expr
    right: Expr

    def accept(self, visitor):
        return visitor.visit_stringslice_expr(self)


@dataclass
class StringIndex(Expr):
    value: Expr
    idx: Expr

    def accept(self, visitor):
        return visitor.visit_stringindex_expr(self)


