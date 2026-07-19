from pathlib import Path


def define_ast(
    output_dir: str,
    base_name: str,
    types: list[str],
    make_dataclass: bool = False,
    extra_fields: list[tuple[str, str, str]] | None = None,  # (name, type, default_expr)
) -> None:
    
    path = Path(output_dir) / "src" / f"{base_name.lower()}.py"

    with open(path, "w", encoding="utf-8") as writer:
        writer.write("from __future__ import annotations\n")
        writer.write("from abc import ABC, abstractmethod\n")
        writer.write("from node import Node\n")
        writer.write("from tokens import Token\n")
        writer.write("from datatypes import Datatypes\n")
        writer.write("from token_types import TokenType\n")
        writer.write("from dataclasses import dataclass, field\n\n\n")

        define_visitor(writer, base_name, types)

        if make_dataclass:
            writer.write("@dataclass\n")
        writer.write(f"class {base_name}(Node, ABC):\n")

        for fname, ftype, fdefault in extra_fields or []:
            writer.write(f"    {fname}: {ftype} = field(init=False, default={fdefault})\n")

        writer.write("    @abstractmethod\n")
        writer.write("    def accept(self, visitor):\n")
        writer.write("        pass\n\n\n")

        for type_def in types:
            class_name, fields = map(str.strip, type_def.split(":", 1))
            define_type(writer, base_name, class_name, fields)


def define_visitor(writer, base_name: str, types: list[str]) -> None:
    writer.write(f"class {base_name}Visitor(ABC):\n")

    for type_def in types:
        class_name = type_def.split(":")[0].strip()

        writer.write("    @abstractmethod\n")
        writer.write(
            f"    def visit_{class_name.lower()}_{base_name.lower()}(self, expr):\n"
        )
        writer.write("        pass\n\n")

    writer.write("\n\n")


def define_type(
    writer,
    base_name: str,
    class_name: str,
    field_list: str,
) -> None:

    writer.write("@dataclass\n")
    writer.write(f"class {class_name}({base_name}):\n")

    fields = []

    if field_list:
        fields = [f.strip() for f in field_list.split(",")]

        for field in fields:
            field_type, field_name = field.rsplit(" ", 1)
            writer.write(f"    {field_name}: {field_type}\n")

        writer.write("\n")

    writer.write("    def accept(self, visitor):\n")
    writer.write(
        f"        return visitor.visit_{class_name.lower()}_{base_name.lower()}(self)\n"
    )

    writer.write("\n\n")

def main():
    define_ast(
        ".",
        "Stmt",
        [
            "Return : Expr expression",
            "Expression : Expr expression",
            "Null : None none",
            "VariableDeclaration : Token name, Expr init",
            "IfStmt : Expr expression, Stmt then, Stmt Else",
            "Compound : Block block",
            "Break : str label",
            "Continue : str label",
            "While : Expr condition, Stmt body, str label",
            "DoWhile : Expr condition, Stmt body, str label",
            "InbuiltStatementNoarg : TokenType type",
            "SendStatement : Expr name, Expr data",
            "FunctionDeclarationStmt : str name",
            "InbuiltProcedureArg1: TokenType type, Expr val"
        ],
    )
    define_ast(
        ".",
        "Expr",
        [
            "Constant : Token value",
            "UnaryExpr : Token operator, Expr expression",
            "BinaryExpr : Token operator, Expr left, Expr right",
            "Var: Token name",
            "Assign: Expr name, Expr value",
            "AssignCompound : Expr target, Token operator, Expr value",
            "UpdateExpr : Token operator, Expr argument, bool isPrefix",
            "Conditional : Expr condition, Expr val1, Expr val2",
            "InbuiltFunctionArg0: TokenType type",
            "InbuiltFunctionArg1 : TokenType type, Expr val",
            "InbuiltFunctionArg2 : TokenType type, Expr val1, Expr val2",
            "FunctionCall : str name, list[Expr] params",
            "StringSlice : Expr value, Expr left, Expr right",
            "StringIndex : Expr value, Expr idx"
        ],
        
        make_dataclass=True,
        extra_fields=[("datatype", "Datatypes", "None")],
    )


if __name__ == "__main__":
    main()
