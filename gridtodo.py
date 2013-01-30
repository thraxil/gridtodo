from google.appengine.api import channel
from google.appengine.ext import db
import logging
import webapp2
import os
import random
import string
import time
import json
from google.appengine.ext.webapp import template


template_dir = os.path.join(
    os.path.dirname(__file__),
    "templates")

random.seed(time.time())

def gen_id():
    source = string.lowercase + string.uppercase + string.digits
    return "".join([random.choice(source) for x in range(20)])

class Grid(db.Model):
    title = db.StringProperty(required=True)
    rows = db.StringListProperty()
    cols = db.StringListProperty()
    cells = db.BlobProperty(default=None)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)

class IndexPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
            template.render(
                os.path.join(template_dir, 'index.html'),
                dict()))

    def post(self):
        title = self.request.get('title')
        row_labels = [r.strip() for r in self.request.get("rows").split("\n")]
        col_labels = [c.strip() for c in self.request.get("cols").split("\n")]
        k = gen_id()
        grid = Grid(key_name=k, title=title)
        grid.rows = row_labels
        grid.cols = col_labels
        cells = []
        for r in row_labels:
            row = []
            for c in col_labels:
                row.append(0)
            cells.append(row)
        grid.cells = json.dumps(dict(cells=cells))
        grid.put()
        self.redirect("/grid/%s/" % k)

class GridPage(webapp2.RequestHandler):
    def get(self, grid_id):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)

        messager = GridMessager(grid_id)
        channel_token = messager.create_channel_token()

        template_values = dict(grid=g, gridkey=grid_id,
                               rows=g.rows,
                               cols=g.cols,
                               cells=json.loads(g.cells)['cells'],
                               channel_id=channel_token,
                               )
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
            template.render(
                os.path.join(template_dir, 'grid.html'),
                template_values))


class CellUpdate(webapp2.RequestHandler):
    def post(self, grid_id, ridx, cidx):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)
        row = int(ridx)
        col = int(cidx)

        cells = json.loads(g.cells)['cells']
        cells[row][col] = int(self.request.get('v'))
        g.cells = json.dumps(dict(cells=cells))
        g.put()
        messager = GridMessager(grid_id)
        messager.send({
                "cell_update": {
                    "row":row,
                    "col":col,
                    "value": cells[row][col]
                    }
                })
        self.response.write("ok")

class AddRow(webapp2.RequestHandler):
    def post(self, grid_id):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)
        label = self.request.get("label")
        cells = json.loads(g.cells)['cells']
        g.rows = list(g.rows) + [label]
        new_row = []
        for col in g.cols:
            new_row.append(0)
        cells.append(new_row)
        g.cells = json.dumps(dict(cells=cells))
        g.put()
        self.redirect("/grid/%s/" % grid_id)

class AddCol(webapp2.RequestHandler):
    def post(self, grid_id):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)
        label = self.request.get("label")
        old_cols = list(g.cols)
        g.cols = list(old_cols) + [label]
        cells = json.loads(g.cells)['cells']
        # simplest thing to do is just make a new matrix
        # and copy everything it
        new_cells = []
        for r, row in enumerate(g.rows):
            new_row = []
            # copy existing ones
            for c, col in enumerate(old_cols):
                new_row.append(cells[r][c])
            # add a new column
            new_row.append(0)
            new_cells.append(new_row)

        g.cells = json.dumps(dict(cells=new_cells))
        g.put()
        self.redirect("/grid/%s/" % grid_id)


class GridMessager(object):
    """Sends a message to a given client."""
    def __init__(self, grid_key):
        # new random id
        self.id = grid_key

    def create_channel_token(self):
        logging.info("Create channel: " + self.id)
        return channel.create_channel(self.id)

    def send(self, message):
        channel.send_message(self.id, json.dumps(message))

app = webapp2.WSGIApplication(
    [
        ('/', IndexPage),
        ('/grid/([^/]+)/', GridPage),
        ('/cellupdate/([^/]+)/(\d+)/(\d+)/', CellUpdate),
        ('/add_row/([^/]+)/', AddRow),
        ('/add_col/([^/]+)/', AddCol),
    ], debug=True)
