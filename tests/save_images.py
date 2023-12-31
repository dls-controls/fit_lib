#!/dls_sw/prod/tools/RHEL5/bin/python2.6

# Retrieves series of images from camera and saves to matlabl file
#
# Usage: save_image <pv> <count> <filename>

from pkg_resources import require
require('cothread')
require('scipy')

import sys
import os
import cothread
import scipy.io

sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..')))

from fit_lib import camera


try:
    pv, count, filename = sys.argv[1:]
    timed = count[0] == 'T'
    if timed: count = count[1:]
    count = int(count)
except ValueError:
    print 'Usage: save_image <pv> [T]<count> <filename>'
    sys.exit(1)

cam = camera.Mr1394(pv)
sub = cam.subscribe()

if timed:
    cothread.Timer(count, lambda: sub.close())
    images = list(sub)
    print 'Captured', len(images)
else:
    images = []
    for i in range(count):
        images.append(sub.get_image())
        sys.stdout.write('.')
        sys.stdout.flush()
    sub.close()
    print

scipy.io.savemat(filename, dict(images = images), oned_as = 'row')
