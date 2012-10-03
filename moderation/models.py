import datetime
import random
from django.conf import settings
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db.utils import IntegrityError
from moderation.diff import calculate_full_diff

from picklefield.fields import PickledObjectField
from tagging.utils import parse_tag_input


MODERATION_STATUS_REJECTED = 0
MODERATION_STATUS_APPROVED = 1
MODERATION_STATUS_PENDING = 2
MODERATION_STATUS_CREATED = 3

MODERATION_PENDING_LIST = (MODERATION_STATUS_PENDING, MODERATION_STATUS_CREATED)

STATUS_CHOICES = (
    (MODERATION_STATUS_APPROVED, "Approved"),
    (MODERATION_STATUS_PENDING, "Pending"),
    (MODERATION_STATUS_REJECTED, "Rejected"),
    (MODERATION_STATUS_CREATED, "Created"),
)


class Changeset(models.Model):
    content_type = models.ForeignKey(ContentType, editable=False)
    object_pk = models.PositiveIntegerField(editable=False, null=True)
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")
    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    moderation_status = models.SmallIntegerField(choices=STATUS_CHOICES, default=MODERATION_STATUS_CREATED, editable=False)
    moderated_by = models.ForeignKey('auth.User', editable=False, null=True, related_name='moderated_by_set')
    moderation_date = models.DateTimeField(editable=False, blank=True, null=True)
    moderation_reason = models.TextField(blank=True, null=True)

    changed_by = models.ForeignKey('auth.User', editable=False, null=True, related_name='changed_by_set')
    object_diff = PickledObjectField(editable=False)

    def get_model_name(self):
        return self.content_type.name

    def get_children(self):
        changesets = Changeset.objects.filter(moderation_status__in=MODERATION_PENDING_LIST)
        for cs in changesets:
            obj = cs.content_object
            if not obj:
                continue

            for f in obj._meta.fields:
                if getattr(obj, f.name, None) == self.content_object:
                    yield cs

    def get_changes_data(self):
        return {
            'obj': self,
            'diff': calculate_full_diff(self.content_object, self.object_diff),
            'children':self.get_children(),
        }

    def get_content_type_name(self):
        return self.content_object and self.content_object._meta.verbose_name

    def get_content_type_name_plural(self):
        return self.content_object and self.content_object._meta.verbose_name_plural

    @property
    def is_creation(self):
        old_cs = Changeset.objects.filter(content_type=self.content_type, object_pk=self.object_pk, pk__lt=self.pk)
        return not old_cs.exists()

    def approve(self, user, reason):
        self.apply_changes()

        self.moderation_status = MODERATION_STATUS_APPROVED
        self.moderated_by = user
        self.moderation_date = datetime.datetime.now()
        self.moderation_reason = reason

        self.save()

    def reject(self, user, reason):
        self.moderation_status = MODERATION_STATUS_REJECTED
        self.moderated_by = user
        self.moderation_date = datetime.datetime.now()
        self.moderation_reason = reason
        self.save()

    def apply_changes(self):
        if not self.object_pk:
            return

        Model = self.content_type.model_class()
        obj_fields = dict([(f[0].name, f[0]) for f in Model()._meta.get_fields_with_model()])
        update_params = {}
        for k,v in self.object_diff.items():
            field = obj_fields.get(k)
            if not field:
                continue

            if not field.editable:
                continue

            if v is None:
                if not field.null or not field.blank:
                    continue

            if 'FileBrowseField' in type(field).__name__:
                from filebrowser.fields import FileObject
                v = FileObject(u'%s%s' % (settings.FILEBROWSER_DIRECTORY, v))

            if 'TagField' in type(field).__name__:
                from tagging.models import Tag
                tags = parse_tag_input(v)
                lower_tags = []
                real_tags = []
                for t in tags:
                    if not t.lower() in lower_tags:
                        lower_tags.append(t.lower())
                        real_tags.append(t)
                real_tags_str = ', '.join('"%s"' % t for t in real_tags)
                Tag.objects.update_tags(self.content_object, real_tags_str)

            if getattr(field, 'rel', None) and isinstance(v, int):
                v = field.rel.to(pk=v)

            update_params[k] = v

        update_params.update(moderation_active=True)
        update_qs = Model.all_objects.filter(pk=self.object_pk)

        if 'slug' in update_params:
            siblings = Model.all_objects.exclude(pk=self.pk)
            update_params['slug'] = update_params['slug'][:50]
            while siblings.filter(slug=update_params['slug']).exists():
                update_params['slug'] += '_%s' % random.randint(10, 99)
                update_params['slug'] = update_params['slug'][-50:]
            update_params['slug'] = update_params['slug'][:50]
        
        update_qs.update(**update_params)

class ModeratedManager(models.Manager):
    def get_query_set(self):
        return super(ModeratedManager, self).get_query_set().filter(moderation_active=True)

class ModeratedModel(models.Model):
    moderation_active = models.BooleanField(editable=False, default=False)

    objects = ModeratedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True