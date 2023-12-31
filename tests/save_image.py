#!/dls_sw/prod/tools/RHEL5/bin/python2.6

# Retrieves image from given camera and saves it as matlab file
#
# Usage: save_image <pv> <filename>

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
    pv, filename = sys.argv[1:]
except ValueError:
    print 'Usage: save_image <pv> <filename>'
    sys.exit(1)

cam = camera.Mr1394(pv)
image = cam.get_image()
scipy.io.savemat(filename, dict(image = image), oned_as = 'row')
