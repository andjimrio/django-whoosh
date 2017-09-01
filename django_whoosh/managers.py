import os
import shutil

from django.db import models
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_save, post_delete, class_prepared

from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT, DATETIME
from whoosh.index import create_in, open_dir, exists_in
from whoosh.qparser import QueryParser, MultifieldParser

try:
    STORAGE_DIR = settings.WHOOSH_STORAGE_DIR
except AttributeError:
    raise ImproperlyConfigured(u'Could not find WHOOSH_STORAGE_DIR setting. ' +
                               'Please make sure that you have added that setting.')

field_mapping = {
    'AutoField': ID(unique=True, stored=True),
    'BooleanField': STORED,
    'CharField': TEXT(stored=True),
    'CommaSeparatedIntegerField': STORED,
    'DateField': ID,
    'DateTimeField': DATETIME,
    'DecimalField': STORED,
    'EmailField': ID,
    'FileField': ID,
    'FilePathField': ID,
    'FloatField': STORED,
    'ImageField': ID,
    'IntegerField': STORED,
    'IPAddressField': ID,
    'NullBooleanField': STORED,
    'PositiveIntegerField': STORED,
    'PositiveSmallIntegerField': STORED,
    'SlugField': KEYWORD,
    'SmallIntegerField': STORED,
    'TextField': TEXT(stored=True),
    'TimeField': ID,
    'URLField': ID,
    'ForeignKey': TEXT(stored=True),
}


class WhooshManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.default = args[0] if args else kwargs.pop("default", None)
        self.fields = kwargs.pop('fields', []) + ['id']
        self.real_time = kwargs.pop('real_time', True)

        if not os.path.exists(STORAGE_DIR):
            os.mkdir(STORAGE_DIR)

        super().__init__()

    # -----------------------------------------------------------
    # BASIC OPERATIONS
    # -----------------------------------------------------------

    def contribute_to_class(self, model, name):
        super().contribute_to_class(model, name)
        class_prepared.connect(self.class_prepared_callback, sender=self.model)

    def class_prepared_callback(self, sender, **kwargs):
        self.__create_index(self.model, self.fields)

        if self.real_time:
            post_save.connect(self.post_save_callback, sender=self.model)
            post_delete.connect(self.post_delete_callback, sender=self.model)

    def post_save_callback(self, sender, instance, created, **kwargs):
        dct = dict([(f, str(getattr(instance, f))) for f in self.fields])

        index = open_dir(STORAGE_DIR)
        writer = index.writer()

        if created:
            writer.add_document(**dct)
        else:
            writer.update_document(**dct)
        writer.commit()

        instance.on_save()

    def post_delete_callback(self, sender, instance, **kwargs):
        pass

    def rebuild_index(self, model, instances):
        if os.path.exists(STORAGE_DIR):
            shutil.rmtree(STORAGE_DIR)
            os.mkdir(STORAGE_DIR)

        self.__create_index(model, self.fields)
        for instance in instances:
            self.post_save_callback(instance=instance, created=True, sender=None)

    # -----------------------------------------------------------
    # INDEX OPERATIONS
    # -----------------------------------------------------------

    @staticmethod
    def get_keywords(field, item_id, num_terms=20):
        index = open_dir(STORAGE_DIR)

        with index.searcher() as searcher:
            query = QueryParser('id', index.schema).parse(str(item_id))
            results = searcher.search(query)
            keywords = [keyword for keyword, score in results.key_terms(field, numterms=num_terms)]

        return keywords

    def get_more_like_this(self, field, item_id, limit=None):
        index = open_dir(STORAGE_DIR)

        with index.searcher() as searcher:
            query = QueryParser('id', index.schema).parse(str(item_id))
            results = searcher.search(query)
            identities = results[0].more_like_this(field, top=limit)
            ids = [r['id'] for r in identities]

        return self.filter(id__in=ids)

    # -----------------------------------------------------------
    # QUERIES
    # -----------------------------------------------------------

    def query(self, field, query):
        ids = self.__query_search(field, query)
        return self.filter(id__in=ids)

    def query_multifield(self, fields, query):
        ids = self.__query_multifield_search(fields, query)
        return self.filter(id__in=ids)

    # HELPERS QUERIES

    def query_list_and(self, field, query_list):
        query = self.__list_to_query(query_list, 'AND')
        return self.query(field, query)

    def query_list_or(self, field, query_list):
        query = self.__list_to_query(query_list, 'OR')
        return self.query(field, query)

    def query_multifield_dict(self, dict_data):
        fields, query = self.__dict_to_query(dict_data)
        return self.query_multifield(fields, query)

    # PRIVATE METHODS

    @staticmethod
    def __create_index(model, fields):
        if not exists_in(STORAGE_DIR):
            schema_dict = {}
            for field_name in fields:
                field_type = model._meta.get_field(field_name).get_internal_type()
                schema_dict[field_name] = field_mapping[field_type]
            schema = Schema(**schema_dict)

            create_in(STORAGE_DIR, schema)

    @staticmethod
    def __query_search(field, search, limit=None):
        index = open_dir(STORAGE_DIR)

        with index.searcher() as searcher:
            query = QueryParser(field, index.schema).parse(str(search))
            results = searcher.search(query, limit=limit)
            ids = [r['id'] for r in results]

        return ids

    @staticmethod
    def __query_multifield_search(fields, search, limit=None):
        index = open_dir(STORAGE_DIR)

        with index.searcher() as searcher:
            query = MultifieldParser(fields, index.schema).parse(str(search))
            results = searcher.search(query, limit=limit)
            ids = [r['id'] for r in results]

        return ids

    @staticmethod
    def __list_to_query(query_list, word):
        and_or = " {} ".format(word)
        return and_or.join(query_list)

    @staticmethod
    def __dict_to_query(dict_data):
        fields = []
        queries = []

        for key, value in dict_data.items():
            if value != '' and value is not None:
                fields.append(key)
                queries.append("{}:{}".format(key, value))

        query = " ".join(queries)
        return fields, query