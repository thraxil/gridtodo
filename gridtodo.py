from google.appengine.ext import db
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
        for cl in row_labels:
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
                               cols=g.sorted_cols())
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(template_values))


app = webapp2.WSGIApplication(
    [
        ('/', IndexPage),
        ('/grid/([^/]+)/', GridPage),
    ], debug=True)
