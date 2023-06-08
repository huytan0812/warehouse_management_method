from functools import wraps

# Outer function() takes a view_function() as an argument
def is_activating_warehouse_management_method(view_function):

    # Inner function() wraps a decorated function()
    def wrapper_function(*args, **kwargs):

        # Pre handling
        print("Hello, World 1")
        print("Hello, World 2")

        # Decorated function()
        view_function(*args, **kwargs)

        # Post handling
        print("Hello, World 3")
        print("Hello, World 4")
        print("Hello, World 5")

    return wrapper_function

@is_activating_warehouse_management_method
def greet():
    print("Hello, World!")