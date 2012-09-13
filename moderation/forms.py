from django import forms
from django.contrib.contenttypes.models import ContentType

from moderation.models import Changeset, MODERATION_STATUS_PENDING

class MockObject():
    def save(self, *args, **kwargs):
        pass

class BaseModeratedObjectForm(forms.ModelForm):
    def save(self, request, commit=True, *args, **kwargs):
        changes = dict([(k, v) for k, v in self.cleaned_data.items() if k in self.changed_data])
        create = False

        if not self.instance or not self.instance.pk:
            self.instance = super(BaseModeratedObjectForm, self).save(commit=commit, *args, **kwargs)
            create = True

        if changes or create:
            ct = ContentType.objects.get_for_model(self.instance)
            Changeset.objects.create(
                content_type = ct,
                object_pk = self.instance.pk,
                changed_by=request and request.user.is_authenticated() and request.user or None,
                moderation_status = MODERATION_STATUS_PENDING,
                object_diff = changes,
            )
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
