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

#include "pitivi.h"
#include "pitivi-thumbs.h"

struct _PitiviThumbsPrivate
{
  /* instance private members */
  
  gboolean	dispose_has_run;
  
  /* Thumbs and Receive information */
  
  GObject       *receiver;
  gchar		*filename;
  GstElement    *pipeline;
  gint64        timeout;
  gint64        frame;
  gboolean      can_finish;
};

/*
 * forward definitions
 */

enum {
  PROP_FILENAME = 1,
  PROP_RECEIVER,
  PROP_FRAME,
  PROP_INFO,
  LAST_PROP
};

/*
 * Insert "added-value" functions here
 */

static     GObjectClass *parent_class;


PitiviThumbs *
pitivi_thumbs_new (gchar *filename, GObject *receiver, int i)
{
  PitiviThumbs	*thumbs;

  thumbs = (PitiviThumbs *) g_object_new(PITIVI_THUMBS_TYPE,
					 "receiver",
					 receiver,
					 "info",
					 i,
					 "thumb-filename",
					 filename,
					 NULL);
  g_assert(thumbs != NULL);
  return thumbs;
}

static GObject *
pitivi_thumbs_constructor (GType type,
			     guint n_construct_properties,
			     GObjectConstructParam * construct_properties)
{
  GObject *obj;
  obj = parent_class->constructor (type, n_construct_properties,
				   construct_properties);
  
  PitiviThumbs	*thumbs = (PitiviThumbs	*) obj;
  return obj;
}

static void
pitivi_thumbs_instance_init (GTypeInstance * instance, gpointer g_class)
{
  PitiviThumbs *this = (PitiviThumbs *) instance;

  this->private = g_new0(PitiviThumbsPrivate, 1);
  
  /* initialize all public and private members to reasonable default values. */ 
  
  this->private->dispose_has_run = FALSE;  
  this->private->frame = FRAME;
  this->private->timeout = TIMEOUT;
}

static void
pitivi_thumbs_dispose (GObject *object)
{
  PitiviThumbs	*this = PITIVI_THUMBS(object);

  /* If dispose did already run, return. */
  if (this->private->dispose_has_run)
    return;
  
  /* Make sure dispose does not run twice. */
  this->private->dispose_has_run = TRUE;	
  G_OBJECT_CLASS (parent_class)->dispose (object);
}

static void
pitivi_thumbs_finalize (GObject *object)
{
  PitiviThumbs	*this = PITIVI_THUMBS(object);
  g_free (this->private);
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
pitivi_thumbs_set_property (GObject * object,
			    guint property_id,
			    const GValue * value, GParamSpec * pspec)
{
  PitiviThumbs *this = (PitiviThumbs *) object;

  switch (property_id)
    {
    case PROP_FILENAME:
      this->private->filename = g_value_get_pointer (value);
      break;
    case PROP_RECEIVER:
      this->private->receiver = g_value_get_pointer (value);
      break;
    case PROP_INFO:
      this->info = g_value_get_int (value);
      break;
    case PROP_FRAME:
      this->private->frame = g_value_get_int (value);
      break;
    default:
      g_assert (FALSE);
      break;
    }
}

static void
pitivi_thumbs_get_property (GObject * object,
			      guint property_id,
			      GValue * value, GParamSpec * pspec)
{
  PitiviThumbs *this = (PitiviThumbs *) object;

  switch (property_id)
    {
    default:
      g_assert (FALSE);
      break;
    }
}

void pitivi_thumb_end_of_snap (GstElement *sink, PitiviThumbs *this)
{
  gst_element_set_state (this->private->pipeline, GST_STATE_NULL);
  g_signal_emit_by_name (this->private->receiver, "snapped", this);
}

/* timeout after a given amount of time */
gboolean pitivi_thumb_timeout (GstPipeline *gen)
{
  /* setting the state NULL will make iterate return false */
  gst_element_set_state (GST_ELEMENT (gen), GST_STATE_NULL);
  return FALSE;
}

gboolean pitivi_thumb_iterator (GstPipeline *gen)
{
  /* setting the state NULL will make iterate return false */
  return gst_bin_iterate (GST_BIN (gen));
}


static int
pitivi_thumbnail_pngenc_get (PitiviThumbs *this)
{
  GstElement *gnomevfssrc;
  GstElement *snapshot;
  GstElement *sink;
  GstPad *pad;
  GstEvent *event;
  gboolean res;
  GError *error = NULL;
  int i;
  
  this->private->pipeline = gst_parse_launch ("gnomevfssrc name=gnomevfssrc ! spider ! " 
					      "videoscale ! ffcolorspace ! video/x-raw-rgb,width=48,height=48 !"
					      "pngenc name=snapshot",
					      &error);
  
  if (!GST_IS_PIPELINE (this->private->pipeline))
    {
      g_print ("Parse error: %s\n", error->message);
      return  -1;
    }
  gnomevfssrc = gst_bin_get_by_name (GST_BIN (this->private->pipeline), "gnomevfssrc");
  snapshot = gst_bin_get_by_name (GST_BIN (this->private->pipeline), "snapshot");
  g_assert (GST_IS_ELEMENT (snapshot));
  g_assert (GST_IS_ELEMENT (gnomevfssrc));
  g_object_set (G_OBJECT (gnomevfssrc), "location", this->private->filename, NULL);

  gst_element_set_state (this->private->pipeline, GST_STATE_PLAYING);
    
  for (i = 0; i < this->private->frame; ++i)
    gst_bin_iterate (GST_BIN (this->private->pipeline));
	
  gst_element_set_state (this->private->pipeline, GST_STATE_PAUSED);
    
  sink = gst_element_factory_make ("filesink", "sink");
  g_assert (GST_IS_ELEMENT (sink));
  g_object_set (G_OBJECT (sink), "location", this->output, NULL);
  gst_bin_add (GST_BIN (this->private->pipeline), sink);
  gst_element_link (snapshot, sink);
  g_signal_connect (G_OBJECT (sink), "handoff",
		    G_CALLBACK (pitivi_thumb_end_of_snap), this);

  gst_element_set_state (this->private->pipeline, GST_STATE_PLAYING);
	
  g_timeout_add (TIMEOUT, (GSourceFunc) pitivi_thumb_timeout, this->private->pipeline);
  g_idle_add ((GSourceFunc) pitivi_thumb_iterator, this->private->pipeline);
  this->private->can_finish = TRUE;
  return 1;
}

gchar *
pitivi_thumbs_get_last_charoccur (gchar *s, char c)
{
  gchar *str;
  int len;

  len = strlen (s) - 1;
  if (len > 0)
    {
      str = s + len;
      if (str && *str)
	{
	  while (len)
	    {
	    if (*str == c)
	      return str + 1;
	    str--;
	    len--;
	    }
	}
    }
  return NULL;
}

gchar *
pitivi_thumbs_generate (PitiviThumbs *this)
{
  GstElement *pngenc = NULL;
  gchar	     *tmp = NULL;

  pngenc = gst_element_factory_make ("pngenc", "pngenc");
  if (this->private->filename && pngenc != NULL)
    {
      tmp = pitivi_thumbs_get_last_charoccur (this->private->filename, '/');
      if ( tmp )
	{
	  this->output = g_malloc (strlen (this->private->filename) + DIR_LENGTH);
	  g_sprintf (this->output, "/tmp/%s%c%d", tmp, '\0', this->info);
	  if ( pitivi_thumbnail_pngenc_get (this) > 0)
	      return this->output;
	}
    }
  return NULL;
}

static void
pitivi_thumbs_class_init (gpointer g_class, gpointer g_class_data)
{
  GObjectClass *gobject_class = G_OBJECT_CLASS (g_class);
  PitiviThumbsClass *thumb_class = PITIVI_THUMBS_CLASS (g_class);

  parent_class = G_OBJECT_CLASS (g_type_class_peek_parent (g_class));

  gobject_class->constructor = pitivi_thumbs_constructor;
  gobject_class->dispose = pitivi_thumbs_dispose;
  gobject_class->finalize = pitivi_thumbs_finalize;

  gobject_class->set_property = pitivi_thumbs_set_property;
  gobject_class->get_property = pitivi_thumbs_get_property;
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_RECEIVER,
				   g_param_spec_pointer ("receiver","receiver","receiver",
							 G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_INFO,
				   g_param_spec_int      ("info","info","info",
							  G_MININT, G_MAXINT, 0, G_PARAM_READWRITE)); 

  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_FILENAME,
				   g_param_spec_pointer ("thumb-filename","thumb-filename","thumb-filename",
							 G_PARAM_READWRITE));
  
  g_object_class_install_property (G_OBJECT_CLASS (gobject_class), PROP_FRAME,
				   g_param_spec_pointer ("frame","frame","frame",
							 G_PARAM_READWRITE));

  thumb_class->generate_thumb = pitivi_thumbs_generate;
}

GType
pitivi_thumbs_get_type (void)
{
  static GType type = 0;
 
  if (type == 0)
    {
      static const GTypeInfo info = {
	sizeof (PitiviThumbsClass),
	NULL,			/* base_init */
	NULL,			/* base_finalize */
	pitivi_thumbs_class_init,	/* class_init */
	NULL,			/* class_finalize */
	NULL,			/* class_data */
	sizeof (PitiviThumbs),
	0,			/* n_preallocs */
	pitivi_thumbs_instance_init	/* instance_init */
      };
      type = g_type_register_static (G_TYPE_OBJECT,
				     "PitiviThumbsType", &info, 0);
    }

  return type;
}
