from google.appengine.ext import db
import logging
import webapp2
import jinja2
import os
import random
import string
import time

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(
            os.path.dirname(__file__),
            "templates")))

random.seed(time.time())

def gen_id():
    source = string.lowercase + string.uppercase + string.digits
    return "".join([random.choice(source) for x in range(20)])

class Grid(db.Model):
    title = db.StringProperty(required=True)

    def sorted_rows(self):
        rows = [r for r in self.rows]
        rows.sort(key=lambda x: x.display_order)
        return rows

    def sorted_cols(self):
        cols = [r for r in self.cols]
        cols.sort(key=lambda x: x.display_order)
        return cols

    def get_cell(self, ridx, cidx):
        for c in self.cells:
            if c.row.display_order == ridx and c.col.display_order == cidx:
                return c
        return None


class Row(db.Model):
    grid = db.ReferenceProperty(
        Grid,
        collection_name='rows')
    label = db.StringProperty(required=True)
    display_order = db.IntegerProperty(required=True)

class Col(db.Model):
    grid = db.ReferenceProperty(
        Grid,
        collection_name='cols')
    label = db.StringProperty(required=True)
    display_order = db.IntegerProperty(required=True)

class Cell(db.Model):
    grid = db.ReferenceProperty(
        Grid,
        collection_name='cells')
    row = db.ReferenceProperty(
        Row,
        collection_name='cells')
    col = db.ReferenceProperty(
        Col,
        collection_name='cells')
    value = db.IntegerProperty(required=True)


class IndexPage(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('index.html')
        template_values = dict()
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(template_values))

    def post(self):
        title = self.request.get('title')
        row_labels = [r.strip() for r in self.request.get("rows").split("\n")]
        col_labels = [c.strip() for c in self.request.get("cols").split("\n")]
        k = gen_id()
        grid = Grid(key_name=k, title=title)
        grid.put()
        i = 0
        for rl in row_labels:
            r = Row(key_name=gen_id(), grid=grid, label=rl, display_order=i)
            r.put()
            i += 1
        i = 0
        for cl in col_labels:
            c = Col(key_name=gen_id(), grid=grid, label=cl, display_order=i)
            c.put()
            i += 1
        self.redirect("/grid/%s/" % k)

class GridPage(webapp2.RequestHandler):
    def get(self, grid_id):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)

        template = jinja_environment.get_template('grid.html')
        template_values = dict(grid=g, gridkey=grid_id,
                               rows=g.sorted_rows(),
                               cols=g.sorted_cols(),
                               cells=g.cells
                               )
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(template_values))


class CellUpdate(webapp2.RequestHandler):
    def post(self, grid_id, ridx, cidx):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)
        row = g.sorted_rows()[int(ridx)]
        col = g.sorted_cols()[int(cidx)]

        cell = g.get_cell(int(ridx), int(cidx))
        v = int(self.request.get('v'))
        if cell is None:
            if v != 0:
                cell = Cell(key_name=gen_id(),
                            grid=g, row=row, col=col,
                            value=v)
                cell.put()
        else:
            if v != 0:
                cell.value = v
                cell.put()
            else:
                cell.delete()

        self.response.write("ok")

class AddRow(webapp2.RequestHandler):
    def post(self, grid_id):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)

        row = Row(key_name=gen_id(),
                  grid=g,
                  label=self.request.get("label"),
                  display_order=len(g.sorted_rows())
                  )
        row.put()
        self.redirect("/grid/%s/" % grid_id)

class AddCol(webapp2.RequestHandler):
    def post(self, grid_id):
        k = db.Key.from_path("Grid", grid_id)
        g = db.get(k)

        col = Col(key_name=gen_id(),
                  grid=g,
                  label=self.request.get("label"),
                  display_order=len(g.sorted_cols())
                  )
        col.put()
        self.redirect("/grid/%s/" % grid_id)


app = webapp2.WSGIApplication(
    [
        ('/', IndexPage),
        ('/grid/([^/]+)/', GridPage),
        ('/cellupdate/([^/]+)/(\d+)/(\d+)/', CellUpdate),
        ('/add_row/([^/]+)/', AddRow),
        ('/add_col/([^/]+)/', AddCol),
    ], debug=True)
