django-moderation-queue
=======================

This app is inspired by the feature-rich [django-moderation](https://github.com/dominno/django-moderation)
(also, thanks for all _diff_ stuff) but we needed incremental moderation in wikipedia style.

Installation
------------

Installation is very easy

1. `pip install -e "git@github.com:ilvar/django-moderation-queue.git#egg=django-moderation-queue"
1. Add `'moderation'` in `INSTALLED_APPS`
1. Inherit your admin sites from `moderation.admin.ModerationAdmin`
1. And your model forms from `moderation.forms.BaseModeratedObjectForm`
1. Done.