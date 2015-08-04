# -*- coding: utf-8 -*-
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.translation import ugettext as _
from mptt.managers import TreeManager
from model_utils import Choices
from model_utils.managers import PassThroughManagerMixin
from autoslug import AutoSlugField


class PassThroughTreeManager(PassThroughManagerMixin, TreeManager):
    def get_queryset(self, *args, **kwargs):
        qs = super(PassThroughTreeManager, self).get_queryset(*args, **kwargs)
        return qs.select_related('category')


class JednostkaAdministracyjnaQuerySet(models.QuerySet):

    def voivodeship(self):
        return self.filter(category__level=1)

    def county(self):
        return self.filter(category__level=2)

    def community(self):
        return self.filter(category__level=3)


class Category(models.Model):
    LEVEL = Choices((1, 'voivodeship', _('voivodeship')),
                    (2, 'county', _('county')),
                   (3, 'community', _('community')))
    name = models.CharField(max_length=50)
    slug = AutoSlugField(populate_from='name')

    level = models.IntegerField(choices=LEVEL, db_index=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')


class JednostkaAdministracyjna(MPTTModel):
    id = models.CharField(max_length=7, primary_key=True)
    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')
    name = models.CharField(_('Name'), max_length=36,)
    category = models.ForeignKey(Category)
    slug = AutoSlugField(populate_from='name')
    updated_on = models.DateField(verbose_name=_("Updated date"))
    active = models.BooleanField(default=False)
    objects = PassThroughTreeManager.for_queryset_class(JednostkaAdministracyjnaQuerySet)()

    def __unicode__(self):
        return u'{0} ({1})'.format(self.name, self.category.name)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = _('Unit of administrative division')
        verbose_name_plural = _('Units of administrative division')