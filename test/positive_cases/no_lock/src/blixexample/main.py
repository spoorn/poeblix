from nemoize import memoize


@memoize
class Test:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


if __name__ == "__main__":
    t1 = Test(5)
    t2 = Test(6)
    t3 = Test(5)

    assert t1 == t3
    assert id(t1) == id(t3)
    assert t1 != t2
    assert id(t1) != id(t2)
