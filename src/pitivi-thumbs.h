/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef PITIVI_THUMBS_H
#define PITIVI_THUMBS_H

/*
 * Potentially, include other headers on which this header depends.
 */

#include <gtk/gtk.h>
#include <gst/gst.h>


/*
 * Type macros.
 */

#define PITIVI_THUMBS_TYPE (pitivi_thumbs_get_type ())
#define PITIVI_THUMBS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), PITIVI_THUMBS_TYPE, PitiviThumbs))
#define PITIVI_THUMBS_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), PITIVI_THUMBS_TYPE, PitiviThumbsClass))
#define PITIVI_IS_THUMBS(obj) (G_TYPE_CHECK_TYPE ((obj), PITIVI_THUMBS_TYPE))
#define PITIVI_IS_THUMBS_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), PITIVI_THUMBS_TYPE))
#define PITIVI_THUMBS_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), PITIVI_THUMBS_TYPE, PitiviThumbsClass))


#define DIR_LENGTH 50
#define FRAME	   10
#define TIMEOUT	   5000

typedef struct _PitiviThumbs PitiviThumbs;
typedef struct _PitiviThumbsClass PitiviThumbsClass;
typedef struct _PitiviThumbsPrivate PitiviThumbsPrivate;

struct _PitiviThumbs
{
  GObject parent;

  /* instance public members */
  gchar  *output;
  gint64 info;
  
  /* private */
  PitiviThumbsPrivate *private;
};

struct _PitiviThumbsClass
{
  GObjectClass parent;
  /* class members */
  gchar *(* generate_thumb) (PitiviThumbs *this);
};

/* used by PITIVI_THUMBS_TYPE */
GType pitivi_thumbs_get_type (void);

/*
 * Method definitions.
 */

PitiviThumbs	*pitivi_thumbs_new(gchar *filename, GObject *object, int i);

#endif
