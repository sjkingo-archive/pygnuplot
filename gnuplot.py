#!/usr/bin/env python2.6

from __future__ import print_function
from tempfile import mkstemp
from time import sleep
import os
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
        'font_face': 'Minion Pro', # XXX this won't work for PNG
        'font_size': 12,
        'legend_location': 'outside right',
        'width': 800,
        'height': 600,
    }

    _output_types = {
        'eps': 'postscript eps enhanced color font "%s" %d',
        'svg': 'svg font "%s,%d"',
        'png': 'svg font "%s,%d"', # we convert svg to png because libgd sucks
    }

    _files = [] #: list of files to remove when destroyed
    _convert_png = False #: whether to convert to a PNG using imagemagick
    output_fp = None #: file-like object to write final graph to, or None
    output_filename = None #: filename to write output to

    def __init__(self, output, type=None, verbose=False, **kwargs):
        self._verbose = verbose

        # If output is a file-like object, we write to a temporary file
        # and then copy (byte for byte, yuk) to the given pointer. This
        # allows in-memory graphing by passing us a StringIO instance.
        if hasattr(output, 'write'):
            if output.closed:
                raise IOError('The file-like object passed is not open')
            self.output_fp = output
            fd, self.output_filename = mkstemp(suffix='.gnuplot-output')
            os.close(fd)
            self._files.append(self.output_filename)
        else:
            self.output_filename = output

        # If we got a file-like object, type must be set
        if self.output_fp is not None and type is None:
            raise ValueError('__init__ was passed a file-like object: '
                    'this requires the keyword argument `type` to be set!')

        # The type is normally inferred from the file extension, but it
        # can be overridden (and must be if the output is a file-like).
        #
        # Note we don't blindly support any type, so check if the type is
        # supported too.
        if type is not None:
            self.output_ext = type
        else:
            self.output_ext = os.path.splitext(self.output_filename)[1][1:]
        if self.output_ext not in self._output_types:
            raise ValueError('Unknown output type %s' % self.output_ext)

        # Merge the passed keyword arguments with the default options
        self.opts = dict(self._default_opts)
        for k, v in kwargs.items():
            self.opts[k] = v

        if self.output_ext == 'png':
            self._print('png extension selected: will generate an svg and '
                    'call imagemagick to convert it to png - stupid libgd '
                    'fails with png support')
            self._convert_png = True
            if self.output_fp is not None:
                raise Exception('XXX Sorry, converting to PNG with a '
                        'file-like object is not yet supported')
            self.output_filename_orig = self.output_filename
            fd, self.output_filename = mkstemp(suffix='.gnuplot-output.svg')
            os.close(fd)
            self._files.append(self.output_filename)

    def __del__(self):
        for f in self._files:
            print('removing temp file', f)
            os.remove(f)

    def write(self, gnuplot, data):
        self._print(data)
        gnuplot.stdin.write('%s\n' % data)
        gnuplot.stdin.flush()

    def _print(self, str):
        if self._verbose:
            print(str)

    def plot(self, data_points):
        files = []
        for label, vals in data_points:
            fd, path = mkstemp(suffix='.gnuplot-%s' % label, text=True)
            self._files.append(path)
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

        # If png format, convert it from SVG
        if self._convert_png:
            input = self.output_filename
            self.output_filename = self.output_filename_orig
            args = ['convert', input, '-transparent', 'white',
                    self.output_filename]
            self._print(' '.join(args))
            g = subprocess.Popen(args)
            g.wait()

        # Transfer the file into the given fp
        if self.output_fp is not None:
            with open(self.output_filename, 'r') as fp:
                self.output_fp.write(fp.read())

    def _call_gnuplot(self, plots):
        g = subprocess.Popen(['gnuplot'], stdin=subprocess.PIPE)

        self.write(g, 'set fontpath "/usr/share/fonts/!:/usr/local/share/fonts/!"')
        self.write(g, 'set term %s' % (self._output_types[self.output_ext] %
                (self.opts.get('font_face'), self.opts.get('font_size')) + 
                ' size %d, %d' % (self.opts.get('width'),
                self.opts.get('height'))))
        self.write(g, 'set output "%s"' % self.output_filename)
        self.write(g, 'set key %s' % self.opts.get('legend_location'))

        if self.opts.get('title', None) is not None:
            self.write(g, 'set title "%s"' % self.opts.get('title'))

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

        self.write(g, p)
        self.write(g, 'unset output') # needed to flush before quiting

        sleep(1)
        self.write(g, 'quit')
        g.kill()
