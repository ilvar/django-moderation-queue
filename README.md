django-moderation-queue
=======================

This app is inspired by the feature-rich [django-moderation](https://github.com/dominno/django-moderation)
(also, thanks for all _diff_ stuff) but we needed incremental moderation in wikipedia style.

Installation
------------

Installation is very easy

# `pip install -e "git@github.com:ilvar/django-moderation-queue.git#egg=django-moderation-queue"
# Add `'moderation'` in `INSTALLED_APPS`
# Inherit your admin sites from `moderation.admin.ModerationAdmin`
# And your model forms from `moderation.forms.BaseModeratedObjectForm`
# Done.