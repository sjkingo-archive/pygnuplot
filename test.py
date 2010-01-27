#!/usr/bin/env python2.6

from gnuplot import GnuPlot
from StringIO import StringIO
import sys

g = GnuPlot(sys.argv[1], filled=True, filled_familiar_colour='red', opacity=0.5,
        xlabel='Accuracy (%)', ylabel='Iterations', verbose=True, title='Test SVG')

s = """0   4.098360    3.884533
50  55.59515    38.48895
100 77.690662   51.967377
200 94.654312   59.337134
300 99.287241   64.433357
400 99.679258   67.533856
500 99.893086   68.104062
800 99.893086   68.175338"""

fam = []
unfam = []
for l in s.split('\n'):
    vals = l.split()
    fam.append((vals[0], vals[1]))
    unfam.append((vals[0], vals[2]))

g.plot([
    ('familiar', fam),
    ('unfamiliar', unfam),
])

#g.plot([
#    ('test1', [(0, 1, 3), (1, 2, 3), (2, 3, 3)]),
#    ('test2', [(4, 3, 3), (1, 2, 1), (0, -1, 4)]),
#])
