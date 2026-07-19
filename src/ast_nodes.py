from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from expr import Expr
from node import Node
from stmt import Stmt, VariableDeclaration
from tokens import Token
from datatypes import Datatypes

class StmtVisitor(ABC):
    @abstractmethod
    def visit_return_stmt(self, stmt):
        pass


class Stmt(ABC):
    @abstractmethod
    def accept(self, visitor):
        pass

@dataclass
class Program:
    stmts: list[Declaration]

type Declaration = Function | VariableDeclaration

@dataclass
class BlockItem(Node):
    stmt: Stmt | VariableDeclaration

@dataclass
class Function(Node):
    name: Token
    params : list[tuple[Token, Datatypes]]
    datatype : Datatypes
    body: Block

    def accept(self, visitor):
        return visitor.visit_function_stmt(self)

@dataclass
class Block(Node):
    body: list[BlockItem]

    def accept(self, visitor):
        return visitor.visit_block_stmts(self)

@dataclass 
class InitDecl(Node):
    val : Expr | Stmt