_current_computation = None

class Reactive:
    def __init__(self, value=None, formula=None):
        self._formula = formula  # hidden: used for computed values
        self._value = value
        self._dependencies = set()   # reactives this one depends on
        self._dependents = set()     # reactives that depend on this one
        if self._formula is not None:
            self.recompute()

    @property
    def value(self):
        global _current_computation
        if _current_computation is not None:
            self._dependents.add(_current_computation)
            _current_computation._dependencies.add(self)
        return self._value

    @value.setter
    def value(self, new_val):
        if self._formula is not None:
            raise Exception("Cannot assign to a computed Reactive value.")
        if new_val != self._value:
            self._value = new_val
            for dep in self._dependents.copy():
                dep.recompute()

    def recompute(self):
        if self._formula is None:
            return
        # Clear old dependencies.
        for dep in self._dependencies:
            dep._dependents.discard(self)
        self._dependencies.clear()
        global _current_computation
        old = _current_computation
        _current_computation = self
        new_val = self._formula()
        _current_computation = old
        if new_val != self._value:
            self._value = new_val
            for dep in self._dependents.copy():
                dep.recompute()

    def __repr__(self):
        return str(self.value)

    # Basic operator overloads for arithmetic/string operations.
    def _binary_op(self, other, op):
        if not isinstance(other, Reactive):
            other = Reactive(other)
        return Reactive(formula=lambda: op(self.value, other.value))

    def __add__(self, other):
        return self._binary_op(other, lambda a, b: a + b)

    def __radd__(self, other):
        return self._binary_op(other, lambda a, b: other + a)

# Helper to generate computed HTML from a template.
def html_template(template, **reactives):
    """
    Takes a template string with placeholders and reactive values.
    Usage:
        page = html_template("<h1>{title}</h1><p>{body}</p>", title=title, body=body)
    """
    return Reactive(formula=lambda: template.format(**{k: v.value for k, v in reactives.items()}))

# Helper to generate a reactive HTML list from a reactive CSV string.
def html_list(reactive_str, separator=","):
    """
    Splits the reactive string by separator and returns a string
    containing <li> tags for each item.
    """
    return Reactive(formula=lambda: "".join(f"<li>{item.strip()}</li>" 
                                              for item in reactive_str.value.split(separator)))

# --- Example Usage ---
if __name__ == "__main__":
    # Define reactive state like normal Python.
    title = Reactive("My Page")
    body_text = Reactive("Welcome to my reactive HTML!")
    items_str = Reactive("Apple, Banana, Cherry")

    # Create a computed reactive that produces a list in HTML.
    items_html = html_list(items_str)

    # Create a computed reactive for the full HTML page.
    page = html_template(
        """
<html>
  <head>
    <title>{title}</title>
  </head>
  <body>
    <h1>{title}</h1>
    <p>{body_text}</p>
    <ul>
      {items_html}
    </ul>
  </body>
</html>
""",
        title=title,
        body_text=body_text,
        items_html=items_html
    )

    # Print initial HTML.
    print("Initial HTML:")
    print(page.value)

    # Update underlying state—the HTML recomputes automatically.
    title.value = "My New Page"
    body_text.value = "This is updated reactive HTML content."
    items_str.value = "Avocado, Blueberry, Cantaloupe"

    print("\nUpdated HTML:")
    print(page.value)
