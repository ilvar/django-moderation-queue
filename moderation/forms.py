from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import File, ContentFile
from django.forms.models import BaseModelFormSet, BaseInlineFormSet
from django.db import models

from moderation.models import Changeset, MODERATION_STATUS_PENDING, MODERATION_STATUS_CREATED
from utils.forms import ChangeLoggingFormset

class MockObject():
    def save(self, *args, **kwargs):
        pass

def put_on_moderation(obj, data, user, create):
    ct = ContentType.objects.get_for_model(obj)
    changeset = Changeset.objects.create(
        content_type = ct,
        object_pk = obj.pk,
        changed_by=user,
        moderation_status = create and MODERATION_STATUS_CREATED or MODERATION_STATUS_PENDING,
        object_diff = data,
    )

    MODERATION_SKIP = getattr(settings, 'MODERATION_SKIP', False)
    SUPERUSER_MODERATION_SKIP = getattr(settings, 'SUPERUSER_MODERATION_SKIP', True)

    if MODERATION_SKIP or (user and user.is_superuser and SUPERUSER_MODERATION_SKIP):
        changeset.approve(user, 'Auto')
        obj.moderation_active = True

class BaseModeratedObjectForm(forms.ModelForm):
    def save(self, request, commit=True, skip_moderation=False, *args, **kwargs):
        if skip_moderation:
            obj = super(BaseModeratedObjectForm, self).save(commit=False, *args, **kwargs)
            obj.moderation_active=True
            if commit:
                obj.save()
            return obj

        create = False

        if not self.instance or not self.instance.pk:
            self.instance = super(BaseModeratedObjectForm, self).save(commit=True, *args, **kwargs)
            create = True

        changes = {}
        for k, v in self.cleaned_data.items():
            if k in self.changed_data:
                if isinstance(v, models.Model):
                    changes[k] = v.pk
                elif isinstance(v, File):
                    if create:
                        changes[k] = getattr(self.instance, k).name
                    else:
                        fake_instance = self._meta.model()
                        getattr(fake_instance, k).save(v.name, v, save=False)
                        changes[k] = getattr(fake_instance, k).name
                else:
                    changes[k] = v

        if changes or create:
            user = request and request.user.is_authenticated() and request.user or None
            put_on_moderation(self.instance, data=changes, user=user, create=create)
        return self.instance

    def save_m2m(self):
        cleaned_data = self.cleaned_data
        opts = self.instance._meta
        fields = self.fields.keys()
        for f in opts.many_to_many:
            if fields and f.name not in fields:
                continue
            if f.name in cleaned_data:
                f.save_form_data(self.instance, cleaned_data[f.name])

class ModerationModelFormset(ChangeLoggingFormset, BaseModelFormSet):
    def save_new(self, form, commit=True, **kwargs):
        obj = form.save(request=self.request, commit=False, **kwargs)
        if commit:
            obj.save()
        if commit and hasattr(form, 'save_m2m'):
            form.save_m2m()
        return obj

    def save_existing(self, form, instance, commit=True):
        """Saves and returns an existing model instance for the given form."""
        return form.save(request=self.request, commit=commit)

    def save(self, request, instance=None, commit=True):
        if instance:
            self.instance = instance
        self.request = request
        return super(ModerationModelFormset, self).save(commit=commit)

class ModerationInlineFormset(ModerationModelFormset, BaseInlineFormSet):
    def save_new(self, form, commit=True, **kwargs):
        obj = form.save(request=self.request, commit=False, **kwargs)
        pk_value = getattr(self.instance, self.fk.rel.field_name)
        setattr(obj, self.fk.get_attname(), getattr(pk_value, 'pk', pk_value))

        if commit:
            obj.save()
        if commit and hasattr(form, 'save_m2m'):
            form.save_m2m()
        return obj

    def set_instance(self, instance):
        self.instance = instance

