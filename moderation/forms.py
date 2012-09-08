from django import forms
from django.contrib.contenttypes.models import ContentType

from moderation.models import Changeset, MODERATION_STATUS_PENDING

class MockObject():
    def save(self, *args, **kwargs):
        pass

class BaseModeratedObjectForm(forms.ModelForm):
    def save(self, request, commit=True, *args, **kwargs):
        changes = dict([(k, v) for k, v in self.cleaned_data.items() if k in self.changed_data])
        if changes:
            ct = ContentType.objects.get_for_model(self.instance)
            Changeset.objects.create(
                content_type = ct,
                object_pk = self.instance.pk,
                changed_by=request and request.user.is_authenticated() and request.user or None,
                moderation_status = MODERATION_STATUS_PENDING,
                object_diff = changes,
            )

        return self.instance or self._meta.model()

    def save_m2m(self, *args, **kwargs):
        pass