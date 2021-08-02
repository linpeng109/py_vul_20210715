import py_libssh_poc

if __name__ == '__main__':
    result = py_libssh_poc.execute('localhost', 2222, 'ls')

    print(result)
