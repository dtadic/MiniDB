import shlex
import functools


class MiniDB:
    collections = {}

    def __init__(self, name):
        self.name = name

    def add_collection(self, name):
        self.collections[name] = []

    def add_document(self, collection, document):
        if collection not in self.collections:
            self.add_collection(collection)

        self.collections[collection].append(document)

    def find(self, collection, what):
        results = []
        for doc in self.collections[collection]:
            good = True
            for k, v in what.items():
                if k not in doc:
                    good = False
                    break
                if v != doc[k]:
                    good = False
                    break
            if good:
                results.append(doc)
        return results if len(results) != 0 else None

    def find_predicate(self, predicate, collection, what):
        results = []
        for doc in self.collections[collection]:
            good = True
            for k, v in what.items():
                if k not in doc:
                    good = False
                    break
                if not predicate(doc[k], v):
                    good = False
                    break
            if good:
                results.append(doc)
        return results if len(results) != 0 else None

    def remove(self, collection, document):
        results = []
        for dok in self.collections[collection]:
            good = True
            for k, v in document.items():
                if k not in dok:
                    good = False
                    break
                if v != dok[k]:
                    good = False
                    break
            if good:
                results.append(dok)
        for rez in results:
            self.collections[collection].remove(rez)

    def __str__(self):
        return self.name + " = " + str(self.collections)


class Lexer:
    tokens = []

    def analyze(self, input_string):
        lexer = shlex.shlex(input_string)
        lexer.wordchars += '.?+-*/^=<>'
        for t in lexer:
            self.tokens.append(t)

    def reset(self):
        self.tokens = []


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.pos = 0

    def parse(self):
        out = []
        while self.pos < len(self.lexer.tokens):
            t = self.lexer.tokens[self.pos]
            self.pos += 1
            if t == ')':
                return tuple(out)
            elif t == '(':
                out.append(self.parse())
            elif t == '{':
                out.append(self.parsedoc())
            else:
                out.append(t)
        return tuple(out)

    def parsedoc(self):
        result = {}
        tmp_name = ""
        counter = 0
        while self.pos < len(self.lexer.tokens):
            t = self.lexer.tokens[self.pos]
            val = t
            self.pos += 1
            if t == '}':
                return result
            elif t == '(':
                val = self.parse()
            elif t == '{':
                val = self.parsedoc()
            if counter % 2 == 0:
                tmp_name = val
                counter += 1
            else:
                result[tmp_name] = val
                counter += 1
        return result

    def reset(self):
        self.pos = 0


class Interpreter:
    def __init__(self, parser):
        self.parser = parser
        self.builtin_opers_nonfixed = {
            '+': lambda x, y: x + y,
            '-': lambda x, y: x - y,
            '*': lambda x, y: x * y,
            '/': lambda x, y: x / y
        }
        self.builtin_opers_fixed = {
            'def': self.define_variable,
            'print': self.print,
            '^': lambda x, y: x ** y,
            '%': lambda x, y: x % y,
            'db': self.new_database,
            '?+': self.add_to_database,
            '?-': self.remove_from_database,
            '?=': self.find_in_database_eq,
            '?<': self.find_in_database_lt,
            '?>': self.find_in_database_gt,
            'and': lambda x, y: x and y,
            'or': lambda x, y: x or y,
            'not': lambda x: not x,
            '>': lambda x, y: x > y,
            '<': lambda x, y: x < y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            'neg': lambda x: -x,
        }
        self.builtin_opers_subroutine = {
            'while': self.oper_while,
            'oper': self.new_oper,
            'if': self.oper_if
        }
        self.constants = {
            'true': True,
            'false': False
        }
        self.variables = {}
        self.bases = []
        self.docposition = 0

    def calc(self, inp, args=None):
        if not args:
            args = {}
        nonfixed_oper = None
        oper = None
        lista = []

        for elem in inp:
            if isinstance(elem, tuple):
                lista.append(self.calc(elem, args))
            elif isinstance(elem, dict):
                lista.append(self.calc_doc(elem))
            elif elem in self.builtin_opers_nonfixed.keys():
                nonfixed_oper = self.builtin_opers_nonfixed[elem]
            elif elem in self.builtin_opers_fixed.keys():
                oper = self.builtin_opers_fixed[elem]
            elif elem in self.builtin_opers_subroutine.keys():
                subr = self.builtin_opers_subroutine[elem]
                return subr(*inp[1:], args)
            else:
                try:
                    lista.append(float(elem))
                except ValueError:
                    if elem[0] == "'":
                        lista.append(elem.replace("'", ''))
                    elif elem[0] == '"':
                        lista.append(elem.replace('"', ''))
                    else:
                        if elem in args.keys():
                            if isinstance(args[elem], self.Func):
                                oper = args[elem]
                            else:
                                lista.append(args[elem])
                        elif elem in self.constants.keys():
                            lista.append(self.constants[elem])
                        elif oper == self.builtin_opers_fixed['def']:
                            lista.append(elem)
                        elif elem in self.variables.keys():
                            if isinstance(self.variables[elem], self.Func):
                                oper = self.variables[elem]
                            else:
                                lista.append(self.variables[elem])
                        else:
                            raise Exception("'" + elem + "' not defined")
        if nonfixed_oper is not None:
            return functools.reduce(nonfixed_oper, lista)
        elif oper is not None:
            return oper(*lista)
        elif len(lista) == 1:
            return lista[0]

    def calc_doc(self, doc):
        def f(v):
            if isinstance(v, tuple):
                return self.calc(v)
            else:
                try:
                    return float(v)
                except ValueError:
                    if v[0] == "'":
                        return v.replace("'", '')
                    elif v[0] == '"':
                        return v.replace('"', '')

        return {f(k): f(v) for k, v in doc.items()}

    def define_variable(self, name, value):
        self.variables[name] = value

    def new_database(self, name):
        baza = MiniDB(name)
        self.bases.append(baza)
        return baza

    def add_to_database(self, base, collection, document):
        base.add_document(collection, document)

    def find_in_database_eq(self, db: MiniDB, coll, term):
        return db.find(coll, term)

    def find_in_database_lt(self, db: MiniDB, coll, term):
        return db.find_predicate(lambda x, y: x < y, coll, term)

    def find_in_database_gt(self, db: MiniDB, coll, term):
        return db.find_predicate(lambda x, y: x > y, coll, term)

    def remove_from_database(self, db: MiniDB, collection, document):
        db.remove(collection, document)

    def print(self, *args):
        print(*args)

    def oper_if(self, cnd, lhs, rhs, propagating):
        return self.calc(lhs, propagating) if self.calc(cnd, propagating) else self.calc(rhs, propagating)

    def oper_while(self, cnd, op, propagating):
        while self.calc(cnd, propagating):
            self.calc(op, propagating)

    class Func:

        def __init__(self, args, body, interpreter, propagating):
            self.interpreter = interpreter
            self.args = args
            self.body = body
            self.propagating = propagating

        def __call__(self, *args):
            calc_args = {}
            for pos, arg in enumerate(self.args):
                calc_args[arg] = args[pos]
            calc_args.update(self.propagating)
            return self.interpreter.calc(self.body, calc_args)

    def new_oper(self, args, body, propagating):
        return self.Func(args, body, self, propagating)


a = Lexer()
p = Parser(a)
i = Interpreter(p)

'''
a.analyze('print "Hello" "world!"')
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("print (- (* 2 3) (+ 3 3))")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("print (+ 1 2 3)")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("(def a 5)"
          "(print (+ (- (* 2 a) 2) (/ 2 3)))")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("(def pi 3.14159265359)"
          "(def r 7)"
          "(print (*(^ r 2) pi))"
          "(print (*(* 2 r) pi))")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("(def osobe (db 'osobni podaci'))"
          "(def o 5)"
          "(def d 3)"
          "(def dok {'ime' 'Pero' 'prihod' (+ 2 5)})"
          "(def dok2 {'ime' 'Mile' 'prihod' (+ o d)})"
          "(?+ osobe 'prihodi' dok)"
          "(?+ osobe 'prihodi' dok2)"
          "(print osobe)"
          "(print (?= osobe 'prihodi' {'prihod' (+ o d)}))"
          "(print (?< osobe 'prihodi' {'prihod' (+ o d)}))"
          "(print (?< osobe 'prihodi' {'prihod' (- 10 2)}))")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("print (== 5 3)")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("print (if false 1 2)")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("(def x 0)"
          "(while (< x 5)"
          "       ((print x)"
          "        (def x (+ x 1))"
          "        )"
          ")"
          "(print 'Kraj!')")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("(def aps"
          "  (oper (n)"
          "    ((if (> n 0)"
          "      (n)"
          "        (neg n)))))"
          "(print (aps -1))")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("""
(def izracunaj
(oper (x f)
(f x)))
(print (izracunaj 5 (oper (n) (* n n))))
""")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()

a.analyze("""
(def f
(oper ()
(oper (n m) (% n m))))
(print ((f) 10 4))
""")
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()


(def min
(oper (a b) (- a b)))
(def miin
(oper (a b)(min b a))
)
(print (miin 10 4)


'''

prog = '''
(def fib
    (oper (n)
        (
            (if (< n 2)
                (n)
                (+
                    (fib ((- n 1))) (fib ((- n 2)))
                )
            )
        )
    )
)
(def n 1)
(while (< n 10)(
    (print (fib n))
    (def n (+ n 1)))
)
'''
a.analyze(prog)
r = p.parse()
print(r)
i.calc(r)
a.reset()
p.reset()
