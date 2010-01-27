#!/usr/bin/env python2.6

from __future__ import print_function
from tempfile import mkstemp
import os
from time import sleep
import subprocess

class GnuPlot(object):
    _plot_types = {
        1: 'plot',
        2: 'plot',
        3: 'splot',
    }

    _default_opts = {
        'lines': True,
        'smooth': True,
        'filled': False,
        'filled_colour': 'skyblue', # see 'gnuplot> show palette colornames'
        'opacity': 1.0,
        'opacity_border': False,
        'font_face': 'Minion Pro',
        'font_size': 12,
    }

    _output_types = {
        'eps': 'postscript eps enhanced color font "%s" %d',
        'svg': 'svg font "%s,%d"',
        'png': 'png transparent interlace enhanced font "%s" %d',
    }

    def __init__(self, output_filename, verbose=False, **kwargs):
        self.output_filename = output_filename
        self.output_ext = os.path.splitext(self.output_filename)[1][1:]
        self._verbose = verbose

        self.opts = dict(self._default_opts)
        for k, v in kwargs.items():
            self.opts[k] = v

        if self.output_ext not in self._output_types:
            raise ValueError('Unknown output type %s' % self.output_ext)

        if self.output_ext == 'png' and \
                not os.path.isfile(self.opts.get('font_face')):
            raise ValueError('When png output is selected, font_face must '
                    'be the full path to a font face, including extension.')

    @classmethod
    def write(cls, gnuplot, data):
        gnuplot.stdin.write('%s\n' % data)
        gnuplot.stdin.flush()

    #@classmethod
    #def check_inputs(cls, data_points):
    #    if len(data_points) < 1:
    #        raise ValueError('Nothing to plot')
    #
    #    first_len = len(data_points[0][1])
    #    for label, vals in data_points:
    #        if len(vals) != first_len:
    #            raise ValueError('Not all plots are the same length '
    #                    '(%s)' % label)

    def _print(self, str):
        if self._verbose:
            print(str)

    def plot(self, data_points):
        files = []
        for label, vals in data_points:
            fd, path = mkstemp(suffix='.gnuplot-%s' % label, text=True)
            files.append((label, path, len(vals[0])))
            for coords in vals:
                for i, x in enumerate(coords):
                    os.write(fd, '%s' % str(x))
                    if i + 1 < len(coords):
                        os.write(fd, ' ')
                    else:
                        os.write(fd, '\n')
            os.close(fd)

        self._call_gnuplot(files)
        for _, path, _ in files:
            os.remove(path)

    def _call_gnuplot(self, plots):
        g = subprocess.Popen(['gnuplot'], stdin=subprocess.PIPE)

        self.write(g, 'set fontpath "/usr/share/fonts/!:/usr/local/share/fonts/!"')
        self.write(g, 'set term %s' % (self._output_types[self.output_ext] %
                (self.opts.get('font_face'), self.opts.get('font_size'))))
        self.write(g, 'set output "%s"' % self.output_filename)

        if self.opts.get('opacity') != 1.0:
            s = 'set style fill solid %.3f' % (self.opts.get('opacity'))
            if not self.opts.get('opacity_border'):
                s += ' noborder'
            self.write(g, s)

        if self.opts.get('xlabel', None) is not None:
            self.write(g, 'set xlabel "%s"' % self.opts.get('xlabel'))
        if self.opts.get('ylabel', None) is not None:
            self.write(g, 'set ylabel "%s"' % self.opts.get('ylabel'))

        p = ''
        for n, (label, path, num_axes) in enumerate(plots):
            axes = ':'.join([str(x) for x in xrange(1, num_axes + 1)])
            if n == 0:
                p += '%s "%s"' % (self._plot_types[num_axes], path)
            if n > 0 and n < len(plots):
                p += ', "%s"' % path
            p += ' using %s' % axes

            # smooth=True allows smoothing of the lines
            # (note that this will silently fail if lines != True)
            if self.opts.get('smooth') and self.opts.get('lines'):
                p += ' smooth csplines'

            # !!!! the title must go here !!!!
            p += ' title "%s"' % label
            
            # lines=True draws lines between each data point
            if self.opts.get('lines') and (not self.opts.get('filled') and \
                    not self.opts.get('filled_%s' % label, False)):
                p += ' with lines'

            # filled=True will fill the plot from the given "line" made by
            # each point in the dataset to the x-axis. Note that it will
            # fill *all*  datasets!
            #
            # filled_<label_name>=True will fill only the given dataset as
            # above.
            #
            # Change the colour by setting filled_colour='<rgb_or_name>'
            if self.opts.get('filled') or self.opts.get('filled_%s' % label,
                    False):
                p += ' with filledcurves x1 lt rgb "%s"' % \
                        self.opts.get('filled_%s_colour' % label, 
                        self.opts.get('filled_colour'))

        self._print(p)
        self.write(g, p)
        self.write(g, 'unset output') # needed to flush before quiting

        sleep(1) # give it 1 second to flush
        self.write(g, 'quit')
        g.kill()
