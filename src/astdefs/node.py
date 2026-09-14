from dataclasses import dataclass, field


@dataclass
class Node:
    location: tuple[int, int] | None = field(default=None, kw_only=True)