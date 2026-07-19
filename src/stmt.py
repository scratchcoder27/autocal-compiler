from __future__ import annotations
from abc import ABC, abstractmethod
from node import Node
from tokens import Token
from datatypes import Datatypes
from token_types import TokenType
from dataclasses import dataclass, field


class StmtVisitor(ABC):
    @abstractmethod
    def visit_return_stmt(self, expr):
        pass

    @abstractmethod
    def visit_expression_stmt(self, expr):
        pass

    @abstractmethod
    def visit_null_stmt(self, expr):
        pass

    @abstractmethod
    def visit_variabledeclaration_stmt(self, expr):
        pass

    @abstractmethod
    def visit_ifstmt_stmt(self, expr):
        pass

    @abstractmethod
    def visit_compound_stmt(self, expr):
        pass

    @abstractmethod
    def visit_break_stmt(self, expr):
        pass

    @abstractmethod
    def visit_continue_stmt(self, expr):
        pass

    @abstractmethod
    def visit_while_stmt(self, expr):
        pass

    @abstractmethod
    def visit_dowhile_stmt(self, expr):
        pass

    @abstractmethod
    def visit_inbuiltstatementnoarg_stmt(self, expr):
        pass

    @abstractmethod
    def visit_sendstatement_stmt(self, expr):
        pass

    @abstractmethod
    def visit_functiondeclarationstmt_stmt(self, expr):
        pass

    @abstractmethod
    def visit_inbuiltprocedurearg1_stmt(self, expr):
        pass



class Stmt(Node, ABC):
    @abstractmethod
    def accept(self, visitor):
        pass


@dataclass
class Return(Stmt):
    expression: Expr

    def accept(self, visitor):
        return visitor.visit_return_stmt(self)


@dataclass
class Expression(Stmt):
    expression: Expr

    def accept(self, visitor):
        return visitor.visit_expression_stmt(self)


@dataclass
class Null(Stmt):
    none: None

    def accept(self, visitor):
        return visitor.visit_null_stmt(self)


@dataclass
class VariableDeclaration(Stmt):
    name: Token
    init: Expr

    def accept(self, visitor):
        return visitor.visit_variabledeclaration_stmt(self)


@dataclass
class IfStmt(Stmt):
    expression: Expr
    then: Stmt
    Else: Stmt

    def accept(self, visitor):
        return visitor.visit_ifstmt_stmt(self)


@dataclass
class Compound(Stmt):
    block: Block

    def accept(self, visitor):
        return visitor.visit_compound_stmt(self)


@dataclass
class Break(Stmt):
    label: str

    def accept(self, visitor):
        return visitor.visit_break_stmt(self)


@dataclass
class Continue(Stmt):
    label: str

    def accept(self, visitor):
        return visitor.visit_continue_stmt(self)


@dataclass
class While(Stmt):
    condition: Expr
    body: Stmt
    label: str

    def accept(self, visitor):
        return visitor.visit_while_stmt(self)


@dataclass
class DoWhile(Stmt):
    condition: Expr
    body: Stmt
    label: str

    def accept(self, visitor):
        return visitor.visit_dowhile_stmt(self)


@dataclass
class InbuiltStatementNoarg(Stmt):
    type: TokenType

    def accept(self, visitor):
        return visitor.visit_inbuiltstatementnoarg_stmt(self)


@dataclass
class SendStatement(Stmt):
    name: Expr
    data: Expr

    def accept(self, visitor):
        return visitor.visit_sendstatement_stmt(self)


@dataclass
class FunctionDeclarationStmt(Stmt):
    name: str

    def accept(self, visitor):
        return visitor.visit_functiondeclarationstmt_stmt(self)


@dataclass
class InbuiltProcedureArg1(Stmt):
    type: TokenType
    val: Expr

    def accept(self, visitor):
        return visitor.visit_inbuiltprocedurearg1_stmt(self)


