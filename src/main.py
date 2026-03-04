_current_computation = None

class Reactive:
    def __init__(self, value=None, compute_fn=None):
        self._compute_fn = compute_fn
        self._value = value
        self._dependencies = []  # dependencies this computed value relies on
        self._dependents = set() # computed Reactive objects that depend on us
        if compute_fn is not None:
            self.compute()

    @property
    def value(self):
        global _current_computation
        if _current_computation is not None:
            if self not in _current_computation._dependencies:
                _current_computation._dependencies.append(self)
                self._dependents.add(_current_computation)
        return self._value

    @value.setter
    def value(self, new_val):
        if self._compute_fn is not None:
            raise Exception("Cannot directly set value of a computed Reactive")
        if new_val != self._value:
            self._value = new_val
            # Trigger dependents to recompute.
            for dep in list(self._dependents):
                dep.compute()

    def compute(self):
        if self._compute_fn is None:
            return
        # Remove self from old dependencies.
        for dep in self._dependencies:
            dep._dependents.discard(self)
        self._dependencies.clear()

        global _current_computation
        prev = _current_computation
        _current_computation = self
        new_val = self._compute_fn()
        _current_computation = prev

        if new_val != self._value:
            self._value = new_val
            for dep in list(self._dependents):
                dep.compute()

    def __repr__(self):
        return f"Reactive({self._value})"

    # Helpers for binary arithmetic that automatically create computed Reactive values.
    def _binary_op(self, other, op):
        if not isinstance(other, Reactive):
            other = Reactive(other)
        return Reactive(compute_fn=lambda: op(self.value, other.value))

    def __add__(self, other):
        return self._binary_op(other, lambda x, y: x + y)
    
    def __radd__(self, other):
        return self._binary_op(other, lambda x, y: y + x)
    
    def __sub__(self, other):
        return self._binary_op(other, lambda x, y: x - y)
    
    def __rsub__(self, other):
        return self._binary_op(other, lambda x, y: y - x)
    
    def __mul__(self, other):
        return self._binary_op(other, lambda x, y: x * y)
    
    def __rmul__(self, other):
        return self._binary_op(other, lambda x, y: y * x)
    
    def __truediv__(self, other):
        return self._binary_op(other, lambda x, y: x / y)
    
    def __rtruediv__(self, other):
        return self._binary_op(other, lambda x, y: y / x)

# Example usage:
if __name__ == "__main__":
    a = Reactive(5)
    b = 1 + a   # computed as 1 + a.value
    c = 2 + b   # computed as 2 + b.value

    print("Initial values:", a.value, b.value, c.value)  # 5, 6, 8
    print("---- Updating a to 3 ----")
    a.value = 3
    print("Updated values:", a.value, b.value, c.value)  # 3, 4, 6
