# django-whoosh

This is an integration layer that sits between Whoosh and Django so that
full-text searching can be not only possible within any Django project, but
extremely easy as well.


## Install
You only must copy the file ```managers.py``` onto your project. You just have to add one setting to your settings.py:

```python
WHOOSH_STORAGE_DIR = '/data/whoosh'
```


## Example
Here's how a django-whoosh enabled model might look:

```python
import datetime
from django.db import models
from django_whoosh.managers import WhooshManager

class Post(models.Model):
    title = models.CharField(max_length=55)
    body = models.TextField()
    date_posted = models.DateTimeField(default=datetime.datetime.now)

    # The first argument is the default query field
    objects = WhooshManager('title', fields=['title', 'body'])

    def __str__(self):
        return self.title
```


Here's how you would use it:

```bash
>>> p = Post(title='first post', body='This is my first post')
>>> p.save() # The new model is already added to the index
>>> Post.objects.query('title', first')
[<Post: first post>]
```

## Built with
* [Django 1.11](https://www.djangoproject.com/)
* [Whoosh 2.7](http://whoosh.readthedocs.io/en/latest/index.html)


## Success Stories
* [LT-News](https://github.com/andjimrio/LTN) - End of Degree work


## Licence
This project is licensed under License - see the [LICENSE](LICENSE) file for details