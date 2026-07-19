class Optimiser:
    def optimise_program(self, program: list[tuple[str, list]]) -> list[tuple[str, list]]:
        while True:
            program, mutated = self._optimise_pass(program)
            if not mutated:
                break
        return program


    def _optimise_pass(self, program: list[tuple[str, list]]) -> tuple[list[tuple[str, list]], bool]:
        optimized = []
        mutated = False
        skip_next = 0

        for i in range(len(program)):
            if skip_next > 0:
                skip_next -= 1
                continue

            if (
                i + 1 < len(program)
                and program[i][0] == "buffer"
                and program[i + 1][0] == "buffer"
            ):
                mutated = True
                continue

            if (
                i + 2 < len(program)
                and program[i][0] == "eval"
                and program[i + 1][0] == "save"
                and program[i + 2][0] == "eval"
            ):
                temp = program[i + 1][1][0]

                if temp.startswith("t_"):
                    expr1 = program[i][1][0]
                    expr2 = program[i + 2][1][0]

                    placeholder = f"${temp}$"

                    if expr2.count(placeholder) == 1:
                        optimized.append(
                            ("eval", [expr2.replace(placeholder, f"({expr1})")])
                        )

                        skip_next = 2
                        mutated = True
                        continue

            if i < len(program) - 1:
                action = self._check_merge(program, i)
                if action is not None:
                    optimized.append(program[i])
                    skip_next = action
                    mutated = True
                    continue

            if self._is_dead_store(program, i):
                mutated = True
                continue

            optimized.append(program[i])

        return optimized, mutated


    def _check_merge(self, program: list[tuple[str, list]], i: int) -> bool | None:
        curr_op, curr_args = program[i]
        next_op, next_args = program[i + 1]

        curr_target = curr_args[0] if curr_args else None
        next_target = next_args[0] if next_args else None

        # save x; load x  -> save x
        is_save_load_pair = (
            (curr_op == "save" and next_op == "load") or
            (curr_op == "load" and next_op == "save")
        ) and curr_target == next_target and curr_target is not None

        # save x; save x -> save x
        is_double_save = (
            curr_op == "save"
            and next_op == "save"
            and curr_target == next_target
            and curr_target is not None
        )

        # eval ...; floor -> evalr ...
        is_eval_floor = (
            curr_op == "eval"
            and next_op == "round"
        )

        # jmp label; dest label -> remove jump
        is_useless_jump = (
            curr_op == "jmp"
            and next_op == "dest"
            and curr_target == next_target
            and curr_target is not None
        )

        if is_save_load_pair or is_double_save:
            return True

        if is_eval_floor:
            program[i] = ("evalr", curr_args)
            return True

        if is_useless_jump:
            program[i] = program[i + 1]
            return True

        return None


    def _is_variable_used(self, program, target, exclude_index):
        for j, (op, args) in enumerate(program):
            if j == exclude_index:
                continue
            
            # Skip checking 'save' arguments
            if op == "save" and args and args[0] == target:
                continue

            for tok in args:
                if tok == target:
                    return True

                if isinstance(tok, str) and f"${target}$" in tok:
                    return True

        return False


    def _uses_variable(self, args: list, target: str) -> bool:
        for arg in args:
            if arg == target:
                return True
            if isinstance(arg, str) and f"${target}$" in arg:
                return True
        return False


    def _is_dead_store(self, program, i):
        op, args = program[i]

        if op != "save":
            return False

        target = args[0]

        # Global dead code elimination
        if not self._is_variable_used(program, target, exclude_index=i):
            return True

        # Local elimination
        for j in range(i + 1, len(program)):
            op2, args2 = program[j]

            if op2 in {"dest", "jmp", "jmpnot", "call", "ret"}:
                return False

            if op2 == "load" and args2 and args2[0] == target:
                return False

            if self._uses_variable(args2, target):
                return False

            if op2 == "save" and args2 and args2[0] == target:
                return True

        return True
