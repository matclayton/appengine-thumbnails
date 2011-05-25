from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api.images import Image, JPEG, NotImageError
from google.appengine.api import memcache
from google.appengine.api import urlfetch

import urllib, random

from datetime import datetime, timedelta

ALLOWED_DIMENSIONS = (
    # (width, height, quality)
    # User Profile Images
    (50, 50, 85),
    (28, 28, 85),
    (150, 150, 85),
    (300, 100, 85),
    (300, 150, 85),
    (300, 300, 85),
    (80, 80, 75),
    # Cloudcast Images
    (50, 50, 85),
    (25, 25, 85),
    (100, 100, 85),
    (300, 150, 85),
    (300, 300, 85),
    (80, 80, 75),
    # Consumer Images
    (60, 60, 85),
    # Campaigns
    (270, 200, 85),
    # Fixed width ones
    (300, None, 85),
)

BASE_URL = 'http://www.mixcloud.com/media/'

class OriginalImage(db.Model):
    image_data = db.BlobProperty()

class BaseResizeHandler(webapp.RequestHandler):
    def get(self, width, height, quality, content_url):
        width, quality = int(width), int(quality)
        height = int(height) if height else None

        if not content_url or not (width, height, quality) in ALLOWED_DIMENSIONS:
            return self.error('Invalid arguments')

        url = BASE_URL + content_url

        response_image_data = self.get_cached(url, width, height, quality)
        if response_image_data is not None:
            self.send_image_response(response_image_data)
            return

        image_data = self.load_image_data(url)
        response_image_data = self.process_image(image_data, width, height, quality)

        self.set_cached(url, width, height, quality, response_image_data)
        self.send_image_response(response_image_data)

    def get_cache_key(self, url, width, height, quality):
        return 'resized-image:%s:%s:%s:%s:%s' % (self.cache_prefix, url, width, height, quality)

    def get_cached(self, url, width, height, quality):
        return memcache.get(self.get_cache_key(url, width, height, quality))

    def set_cached(self, url, width, height, quality, image_data):
        # Cache for 25 to 35 days, to avoid everything expiring at once
        cache_days = 25 + (random.randint(0, 10))
        return memcache.add(self.get_cache_key(url, width, height, quality), image_data, cache_days * 24 * 60 * 60)

    def load_image_data(self, url):
        key = 'fetched-image:%s' % url
        image = OriginalImage.get_by_key_name(key)
        if image is None:
            response = urlfetch.fetch(url)
            if response.status_code == 200:
                image_data = response.content
                image = OriginalImage(image_data=image_data, key_name=key)
                image.put()
        return image.image_data

    def send_image_response(self, image_data):
        self.response.headers['Content-Type'] = 'image/jpeg'
        self.response.headers['Cache-Control'] = 'public,max-age=31536000'
        expires_date = datetime.utcnow() + timedelta(days=365)
        self.response.headers['Expires'] = expires_date.strftime("%d %b %Y %H:%M:%S GMT")
        self.response.out.write(image_data)

    def error(self, msg):
        self.response.out.write("""
            <html>
            <head><title>Error</title></head>
            <body><h1>%s</h1></body>
            </html>""" % msg
        )

class WidthHandler(BaseResizeHandler):
    cache_prefix = 'width'

    def get(self, width, quality, content_url):
        super(WidthHandler, self).get(width, None, quality, content_url)

    def process_image(self, image_data, width, height, quality):
        img = Image(image_data=image_data)
        try:
            img.resize(width=width)
            return img.execute_transforms(output_encoding=JPEG, quality=quality)
        except NotImageError:
            return image_data

class CropHandler(BaseResizeHandler):
    cache_prefix = 'crop'

    def process_image(self, image_data, width, height, quality):
        img = Image(image_data = image_data)
        image_ops = crop_ops(img.width, img.height, width, height)
        if image_ops:
            for op, kwargs in image_ops:
                getattr(img, op)(**kwargs)
            return img.execute_transforms(output_encoding = JPEG, quality=quality)
        return image_data

def crop_ops(width, height, requested_width, requested_height):
    #import logging
    width, height = float(width), float(height)
    requested_width, requested_height = float(requested_width), float(requested_height)
    r = max(requested_width/width, requested_height/height)
    #logging.info('r:%s' % r)
    new_width, new_height = width*r, height*r
    #logging.info('new_width:%s new_height:%s' % (new_width, new_height))
    ops = []
    if r != 1.0:
        ops.append(('resize', {'width': int(new_width), 'height': int(new_height)}))
    ex, ey = (new_width-min(new_width, requested_width))/2, (new_height-min(new_height, requested_height))/2
    #logging.info('ex:%s ey:%s' % (ex, ey))
    if ex or ey:
        ops.append(
            ('crop', {
                'left_x': ex / new_width,
                'right_x': (new_width - ex) / new_width,
                'top_y': ey / new_height,
                'bottom_y': (new_height - ey) / new_height,
            })
        )
    #ops.append(('resize', {'width': int(width), 'height': int(height)}))
    #logging.info('ops:%s' % ops)
    return ops

if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([
        (r'/w/(\d+)/h/(\d+)/q/(\d+)/([a-zA-Z0-9-_/.]+)', CropHandler),
        (r'/w/(\d+)/q/(\d+)/([a-zA-Z0-9-_/.]+)', WidthHandler),
    ], debug=False))
