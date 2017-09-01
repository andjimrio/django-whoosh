from django.db import models
from django_whoosh.managers import WhooshManager


class Post(models.Model):
    title = models.CharField(max_length=55)
    body = models.TextField()
    date_posted = models.DateTimeField(auto_now=True)
    
    objects = WhooshManager('title', fields=['title', 'body'])

    def __str__(self):
        return self.title

    def on_save(self):
        pass
