# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Morituri - for those about to RIP

# Copyright (C) 2009 Thomas Vander Stichele

# This file is part of morituri.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import os

from morituri.common import logcommand, task, accurip, program
from morituri.image import image, cue
from morituri.result import result
from morituri.program import cdrdao, cdparanoia


class Encode(logcommand.LogCommand):
    summary = "encode image"

    def addOptions(self):
        # FIXME: get from config
        self.parser.add_option('-O', '--output-directory',
            action="store", dest="output_directory",
            help="output directory (defaults to current directory)")

        default = 'vorbis'

        # here to avoid import gst eating our options
        from morituri.common import encode

        self.parser.add_option('', '--profile',
            action="store", dest="profile",
            help="profile for encoding (default '%s', choices '%s')" % (
                default, "', '".join(encode.ALL_PROFILES.keys())),
            default=default)


    def do(self, args):
        prog = program.Program()
        prog.outdir = (self.options.output_directory or os.getcwd())
        prog.outdir = prog.outdir.decode('utf-8')

        # here to avoid import gst eating our options
        from morituri.common import encode

        profile = encode.ALL_PROFILES[self.options.profile]()

        runner = task.SyncRunner()

        for arg in args:
            arg = unicode(arg)
            indir = os.path.dirname(arg)
            cueImage = image.Image(arg)
            cueImage.setup(runner)
            # FIXME: find a decent way to get an album-specific outdir
            root, ext = os.path.splitext(os.path.basename(indir))
            outdir = os.path.join(prog.outdir, root)
            try:
                os.makedirs(outdir)
            except:
                # FIXME: handle other exceptions than OSError Errno 17
                pass
            # FIXME: handle this nicer
            assert outdir != indir

            taskk = image.ImageEncodeTask(cueImage, profile, outdir)
            runner.run(taskk)

            # FIXME: translate .m3u file if it exists
            root, ext = os.path.splitext(arg)
            m3upath = root + '.m3u'
            if os.path.exists(m3upath):
                self.debug('translating .m3u file')
                inm3u = open(m3upath)
                outm3u = open(os.path.join(outdir, os.path.basename(m3upath)),
                    'w')
                for line in inm3u.readlines():
                    root, ext = os.path.splitext(line)
                    if ext:
                        # newline is swallowed by splitext here
                        outm3u.write('%s.%s\n' % (root, profile.extension))
                    else:
                        outm3u.write('%s' % root)
                outm3u.close()

class Verify(logcommand.LogCommand):
    summary = "verify image"

    def do(self, args):
        prog = program.Program()
        runner = task.SyncRunner()
        cache = accurip.AccuCache()

        for arg in args:
            arg = unicode(arg)
            cueImage = image.Image(arg)
            cueImage.setup(runner)

            url = cueImage.table.getAccurateRipURL()
            responses = cache.retrieve(url)

            # FIXME: this feels like we're poking at internals.
            prog.cuePath = arg
            prog.result = result.RipResult()
            for track in cueImage.table.tracks:
                tr = result.TrackResult()
                tr.number = track.number
                prog.result.tracks.append(tr)

            prog.verifyImage(runner, responses) 

            print "\n".join(prog.getAccurateRipResults()) + "\n"

class Image(logcommand.LogCommand):
    summary = "handle images"

    subCommandClasses = [Encode, Verify, ]