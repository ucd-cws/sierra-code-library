import code_library

'''these don't yet function as unit tests, but they are the assertions that should be used for that function'''

assert code_library.isiterable(list('a','b')),True
assert code_library.isiterable(list()),True
assert code_library.isiterable(tuple()),True
assert code_library.isiterable("stringy"),False
assert code_library.isiterable(5),False