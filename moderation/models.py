import datetime
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db.utils import IntegrityError

from picklefield.fields import PickledObjectField


MODERATION_STATUS_REJECTED = 0
MODERATION_STATUS_APPROVED = 1
MODERATION_STATUS_PENDING = 2

STATUS_CHOICES = (
    (MODERATION_STATUS_APPROVED, "Approved"),
    (MODERATION_STATUS_PENDING, "Pending"),
    (MODERATION_STATUS_REJECTED, "Rejected"),
)


class Changeset(models.Model):
    content_type = models.ForeignKey(ContentType, editable=False)
    object_pk = models.PositiveIntegerField(editable=False, null=True)
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")
    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    moderation_status = models.SmallIntegerField(choices=STATUS_CHOICES, default=MODERATION_STATUS_PENDING, editable=False)
    moderated_by = models.ForeignKey('auth.User', editable=False, null=True, related_name='moderated_by_set')
    moderation_date = models.DateTimeField(editable=False, blank=True, null=True)
    moderation_reason = models.TextField(blank=True, null=True)

    changed_by = models.ForeignKey('auth.User', editable=False, null=True, related_name='changed_by_set')
    object_diff = PickledObjectField(editable=False)

    def approve(self, user, reason):
        try:
            self.apply_changes()
        except IntegrityError, e:
            print 'Error on chaangeset %s:' % self.pk, e
        else:
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
        from filebrowser.fields import FileBrowseField
        from filebrowser.base import FileObject

        Model = self.content_type.model_class()
        obj_fields = dict([(f[0].name, f[0]) for f in Model()._meta.get_fields_with_model()])
        update_params = {}
        for k,v in self.object_diff.items():
            field = obj_fields.get(k)
            if not field:
                continue

            if isinstance(field, FileBrowseField):
                v = FileObject(v, site=field.site)

            update_params[k] = v

        if self.object_pk:
            update_qs = Model.objects.filter(pk=self.object_pk)
            update_qs.update(**update_params)
        else:
            Model.objects.create(**update_params)
