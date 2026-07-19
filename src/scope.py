class Scope():
    def __init__(self, parent=None):
        self.parent : Scope | None = parent
        self.variables = {}
        self.functions = {}

    def define(self, name, value):
        self.variables[name] = value
    
    def define_funct(self, name, function):
        self.functions[name] = function
    
    def check_exists(self, name) -> bool:
        if name in self.variables:
            return True
        elif self.parent is not None:
            return self.parent.check_exists(name)
        else:
            return False
    
    def check_function_exists(self, name) -> bool:
        if name in self.functions:
            return True
        elif self.parent is not None:
            return self.parent.check_function_exists(name)
        else:
            return False
    
    def check_exists_in_scope(self, name) -> bool:
        return name in self.variables
    
    def check_function_exists_in_scope(self, name) -> bool:
        return name in self.functions

    def resolve(self, name):
        if name in self.variables:
            return self.variables[name]
        elif self.parent is not None:
            return self.parent.resolve(name)
        else:
            raise NameError(f"Variable '{name}' is not defined.")
    
    def resolve_function(self, name):
        if name in self.functions:
            return self.functions[name]
        elif self.parent is not None:
            return self.parent.resolve_function(name)
        else:
            raise NameError(f"Function with signature '{name}' is not defined.")
        
    def update(self, name, datatype):
        if name in self.variables:
            self.variables[name] = datatype
        elif self.parent is not None:
            self.parent.update(name, datatype)
        else:
            raise NameError(f"Variable '{name}' is not defined.")