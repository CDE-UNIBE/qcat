from contextlib import contextmanager


@contextmanager
def ignored(*exceptions):
    """
    Context manager to ignore particular exceptions.

    Example:

        obj = None
        with ignored(MyModel.DoesNotExist):
            obj = MyModel.objects.get(id=1)

    :param exceptions: A variable number of exception classes.
    """
    try:
        yield
    except exceptions:
        pass
