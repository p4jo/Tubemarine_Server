import time

# import numpy as np


def timeTest(f = None, log = print, alertTime = 0.3, alertRepeat = 400):
    if log == print:
        def log(self, *args, **kwargs):
            print(*args, **kwargs)

    def timeTestWrapperFunc(func):
        # times = []
        average = 0
        n = 0
        N = 0

        def res(self, *args, **kwargs):
            nonlocal average, n, N #, times
            t = time.time()
            r = func(self, *args, **kwargs)
            d = time.time() - t
            average = (average * n + d)/(n+1)
            n += 1
            # times.append(d)
            if n >= N + alertRepeat or d > alertTime:
                N = n
                log(self, f"{type(self).__name__}.{func.__name__}({args}) took {d:.3f}s to execute. Average over the last {n} executions: {average}s.")
            return r
        return res
    if f is None:
        return timeTestWrapperFunc # Wird dann auf Funktion angewendet
    else:
        return timeTestWrapperFunc(f) # Wir werden gerade schon selber auf die Funktion angewendet (Klammern weggelassen)