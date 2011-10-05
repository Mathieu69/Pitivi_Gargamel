# PiTiVi , Non-linear video editor
#
#       pitivi/check.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Runtime checks.
"""

import gtk
import gst

from gettext import gettext as _

from pitivi.instance import PiTiVi
from pitivi.configure import APPNAME, PYGTK_REQ, GTK_REQ, PYGST_REQ, GST_REQ, GNONLIN_REQ, PYCAIRO_REQ

global soft_deps
soft_deps = {}


def initiate_videosinks():
    """
    Test if the autovideosink element can initiate, return TRUE if it is the
    case.
    """
    sink = gst.element_factory_make("autovideosink")
    if not sink.set_state(gst.STATE_READY):
        return False
    sink.set_state(gst.STATE_NULL)
    return True


def initiate_audiosinks():
    """
    Test if the autoaudiosink element can initiate, return TRUE if it is the
    case.
    """
    sink = gst.element_factory_make("autoaudiosink")
    if not sink.set_state(gst.STATE_READY):
        return False
    sink.set_state(gst.STATE_NULL)
    return True


def __try_import__(modulename):
    """
    Attempt to load given module.
    Returns True on success, else False.
    """
    try:
        __import__(modulename)
        return True
    except:
        return False


def _version_to_string(version):
    return ".".join([str(x) for x in version])


def _string_to_list(version):
    return [int(x) for x in version.split(".")]


def check_required_version(modulename):
    """
    Checks if the installed module is the required version or more recent.
    Returns [None, None] if it's recent enough, else will return a list
    containing the strings of the required version and the installed version.
    This function does not check for the existence of the given module !
    """
    if modulename == "pygtk":
        if list(gtk.pygtk_version) < _string_to_list(PYGTK_REQ):
            return [PYGTK_REQ, _version_to_string(gtk.pygtk_version)]
    if modulename == "gtk":
        if list(gtk.gtk_version) < _string_to_list(GTK_REQ):
            return [GTK_REQ, _version_to_string(gtk.gtk_version)]
    if modulename == "pygst":
        if list(gst.get_pygst_version()) < _string_to_list(PYGST_REQ):
            return [PYGST_REQ, _version_to_string(gst.get_pygst_version())]
    if modulename == "cairo":
        import cairo
        if _string_to_list(cairo.cairo_version_string()) < _string_to_list(PYCAIRO_REQ):
            return [PYCAIRO_REQ, cairo.cairo_version_string()]
    if modulename == "gst":
        if list(gst.get_gst_version()) < _string_to_list(GST_REQ):
            return [GST_REQ, _version_to_string(gst.get_gst_version())]
    if modulename == "gnonlin":
        gnlver = gst.registry_get_default().find_plugin("gnonlin").get_version()
        if _string_to_list(gnlver) < _string_to_list(GNONLIN_REQ):
            return [GNONLIN_REQ, gnlver]
    return [None, None]


def initial_checks():
    reg = gst.registry_get_default()
    if PiTiVi:
        return (_("%s is already running") % APPNAME,
                _("An instance of %s is already running in this script.") % APPNAME)
    if not reg.find_plugin("gnonlin"):
        return (_("Could not find the GNonLin plugins"),
                _("Make sure the plugins were installed and are available in the GStreamer plugins path."))
    if not reg.find_plugin("autodetect"):
        return (_("Could not find the autodetect plugins"),
                _("Make sure you have installed gst-plugins-good and that it's available in the GStreamer plugin path."))
    if not hasattr(gtk.gdk.Window, 'cairo_create'):
        return (_("PyGTK doesn't have cairo support"),
                _("Please use a version of the GTK+ Python bindings built with cairo support."))
    if not initiate_videosinks():
        return (_("Could not initiate the video output plugins"),
                _("Make sure you have at least one valid video output sink available (xvimagesink or ximagesink)."))
    if not initiate_audiosinks():
        return (_("Could not initiate the audio output plugins"),
                _("Make sure you have at least one valid audio output sink available (alsasink or osssink)."))
    if not __try_import__("cairo"):
        return (_("Could not import the cairo Python bindings"),
                _("Make sure you have the cairo Python bindings installed."))
    if not __try_import__("goocanvas"):
        return (_("Could not import the goocanvas Python bindings"),
                _("Make sure you have the goocanvas Python bindings installed."))
    if not __try_import__("xdg"):
        return (_("Could not import the xdg Python library"),
                _("Make sure you have the xdg Python library installed."))
    req, inst = check_required_version("pygtk")
    if req:
        return (_("You do not have a recent enough version of the GTK+ Python bindings (your version %s)") % inst,
                _("Install a version of the GTK+ Python bindings greater than or equal to %s.") % req)
    req, inst = check_required_version("gtk")
    if req:
        return (_("You do not have a recent enough version of GTK+ (your version %s)") % inst,
                _("Install a version of GTK+ greater than or equal to %s.") % req)
    req, inst = check_required_version("pygst")
    if req:
        return (_("You do not have a recent enough version of GStreamer Python bindings (your version %s)") % inst,
                _("Install a version of the GStreamer Python bindings greater than or equal to %s.") % req)
    req, inst = check_required_version("gst")
    if req:
        return (_("You do not have a recent enough version of GStreamer (your version %s)") % inst,
                _("Install a version of the GStreamer greater than or equal to %s.") % req)
    req, inst = check_required_version("cairo")
    if req:
        return (_("You do not have a recent enough version of the cairo Python bindings (your version %s)") % inst,
                _("Install a version of the cairo Python bindings greater than or equal to %s.") % req)
    req, inst = check_required_version("gnonlin")
    if req:
        return (_("You do not have a recent enough version of the GNonLin GStreamer plugin (your version %s)") % inst,
                _("Install a version of the GNonLin GStreamer plugin greater than or equal to %s.") % req)
    if not __try_import__("ges"):
        #FIXME enable version checking in GES
        return (_("Could not import GStreamer Editing Services "),
                _("Make sure you have GStreamer Editing Services installed."))
    if not __try_import__("zope.interface"):
        return (_("Could not import the Zope interface module"),
                _("Make sure you have the zope.interface module installed."))
    if not __try_import__("pkg_resources"):
        return (_("Could not import the distutils modules"),
                _("Make sure you have the distutils Python module installed."))

    # The following are soft dependencies
    # Note that instead of checking for plugins using gst.registry_get_default().find_plugin("foo"),
    # we could check for elements using gst.element_factory_make("foo")
    if not __try_import__("numpy"):
        soft_deps["NumPy"] = _("Enables the autoalign feature")
    try:
        #if not gst.registry_get_default().find_plugin("frei0r"):
        gst.element_factory_make("frei0r-filter-scale0tilt")
    except gst.ElementNotFoundError:
        soft_deps["Frei0r"] = _("Additional video effects")
    if not gst.registry_get_default().find_plugin("ffmpeg"):
        soft_deps["GStreamer FFmpeg plugin"] = _('Additional multimedia codecs through the FFmpeg library')
    # Test for gst bad
    # This is disabled because, by definition, gst bad is a set of plugins that can
    # move to gst good or ugly, and we don't really have something to rely upon.
    #if not gst.registry_get_default().find_plugin("swfdec"): # FIXME: find a more representative plugin
    #    soft_deps["GStreamer bad plugins"] = _('Additional GStreamer plugins whose code is not of good enough quality, or are not considered tested well enough. The licensing may or may not be LGPL')
    # Test for gst ugly
    #if not gst.registry_get_default().find_plugin("x264"):
    #    soft_deps["GStreamer ugly plugins"] = _('Additional good quality GStreamer plugins whose license is not LGPL or with licensing issues')
    return None
