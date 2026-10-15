from __future__ import annotations

import base64
import uuid
import logging
from datetime import timedelta
from io import BytesIO
from typing import Optional

import cv2
import numpy as np

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from MakerPom.models import CreatPom
from dashboard.models import (
    ContentActivityLog,
    RegistrationRequest,
    ContentManagerRegistration,
    RegistrationLog,
)
from dashboard.email_service import send_admin_notification_email

from authentication.services.face_detection import detect_faces
from authentication.services.face_verification import (
    extract_face_feature,
    check_duplicate_face,
)


class DuplicateFaceError(Exception):
    """Raised when a submitted dashboard registration face belongs to another user."""


class PoemManagementService:
    """Service layer for content‑manager actions on poems and audio."""

    @transaction.atomic
    def approve_poem(self, poem: CreatPom, manager) -> ContentActivityLog:
        if poem.status not in (CreatPom.AWAITING_APPROVAL, CreatPom.REJECTED):
            raise ValueError(_("This poem cannot be approved from its current status."))
        poem.status = CreatPom.APPROVED
        poem.save(update_fields=['status'])
        return self._log_action(poem, manager, ContentActivityLog.Action.APPROVED)

    @transaction.atomic
    def reject_poem(self, poem: CreatPom, manager, reason: str = '') -> ContentActivityLog:
        if poem.status == CreatPom.REJECTED:
            raise ValueError(_("Poem is already rejected."))
        poem.status = CreatPom.REJECTED
        poem.save(update_fields=['status'])
        return self._log_action(
            poem,
            manager,
            ContentActivityLog.Action.REJECTED,
            description=reason,
        )

    @transaction.atomic
    def edit_poem(
        self,
        poem: CreatPom,
        manager,
        *,
        name: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Optional[ContentActivityLog]:
        changed = False
        if name is not None and name != poem.name:
            poem.name = name
            changed = True
        if text is not None and text != poem.text:
            poem.text = text
            changed = True
        if changed:
            poem.save(update_fields=['name', 'text'])
            return self._log_action(poem, manager, ContentActivityLog.Action.EDITED)
        return None

    @transaction.atomic
    def replace_audio(self, poem: CreatPom, manager, audio_file: File) -> ContentActivityLog:
        poem.voies = audio_file
        poem.save(update_fields=['voies'])
        return self._log_action(poem, manager, ContentActivityLog.Action.AUDIO_REPLACED)

    @transaction.atomic
    def delete_audio(self, poem: CreatPom, manager) -> ContentActivityLog:
        if not poem.voies:
            raise ValueError(_("No audio file to delete."))
        poem.voies.delete(save=False)
        poem.voies = None
        poem.save(update_fields=['voies'])
        return self._log_action(poem, manager, ContentActivityLog.Action.AUDIO_DELETED)

    @transaction.atomic
    def return_rejected_to_review(self, poem: CreatPom, manager) -> ContentActivityLog:
        if poem.status != CreatPom.REJECTED:
            raise ValueError(_("Only rejected poems can be returned to review."))

        poem.status = CreatPom.AWAITING_APPROVAL
        poem.save(update_fields=['status'])

        return self._log_action(
            poem,
            manager,
            ContentActivityLog.Action.RETURNED_TO_REVIEW,
        )

    def _log_action(
        self,
        poem: CreatPom,
        manager,
        action: str,
        description: str = '',
    ) -> ContentActivityLog:
        return ContentActivityLog.objects.create(
            manager=manager,
            poem=poem,
            action=action,
            description=description,
        )


class RegistrationService:
    """Handles content manager registration workflow – database, logging, admin notification."""

    @transaction.atomic
    def approve_request(self, request_obj: RegistrationRequest) -> None:
        request_obj.status = 'approved'
        request_obj.generate_token()
        request_obj.save(update_fields=['status', 'token', 'token_created_at', 'is_used', 'used_at'])
        RegistrationLog.objects.create(
            request=request_obj,
            event=RegistrationLog.Event.TOKEN_CREATED,
            detail=f"Token: {request_obj.token}",
        )

    @transaction.atomic
    def reject_request(self, request_obj: RegistrationRequest) -> None:
        request_obj.status = 'rejected'
        request_obj.token = None
        request_obj.token_created_at = None
        request_obj.save(update_fields=['status', 'token', 'token_created_at'])
        RegistrationLog.objects.create(
            request=request_obj,
            event=RegistrationLog.Event.REJECTION,
        )

    @transaction.atomic
    def create_registration(
        self,
        request_obj: RegistrationRequest,
        username: str,
        password: str,
        phone: str,
        photo_data: str,
        video_data: str,
    ) -> ContentManagerRegistration:
        from django.contrib.auth.hashers import make_password

        if ContentManagerRegistration.objects.filter(
            phone=phone, status='pending_verification'
        ).exists():
            raise ValidationError(
                _('A pending registration already exists with this phone number.')
            )

        photo_file = self._decode_and_validate_image(photo_data)
        video_file = self._decode_and_validate_video(video_data)

        User = get_user_model()
        existing_user = User.objects.filter(username=username).first()

        if existing_user is None:
            raise ValidationError(
                _("The existing user account for this registration could not be found.")
            )

        photo_file.seek(0)
        file_bytes = photo_file.read()

        img = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValidationError(_("Invalid image data."))

        faces = detect_faces(img)
        if len(faces) != 1:
            raise ValidationError(
                _("Exactly one face must be visible in the image.")
            )

        feature = extract_face_feature(img, faces[0])

        if check_duplicate_face(existing_user, feature):
            raise DuplicateFaceError()

        photo_file.seek(0)

        registration = ContentManagerRegistration.objects.create(
            request=request_obj,
            username=username,
            password=make_password(password),
            phone=phone,
            photo=photo_file,
            video=video_file,
        )
        request_obj.invalidate_token()

        RegistrationLog.objects.create(
            request=request_obj,
            registration=registration,
            event=RegistrationLog.Event.BASIC_INFO_SUBMITTED,
        )
        RegistrationLog.objects.create(
            registration=registration,
            event=RegistrationLog.Event.PHOTO_CAPTURED,
        )
        RegistrationLog.objects.create(
            registration=registration,
            event=RegistrationLog.Event.VIDEO_RECORDED,
        )
        RegistrationLog.objects.create(
            registration=registration,
            event=RegistrationLog.Event.REGISTRATION_COMPLETED,
        )

        try:
            send_admin_notification_email(registration)
            RegistrationLog.objects.create(
                registration=registration,
                event=RegistrationLog.Event.ADMIN_NOTIFICATION_SENT,
            )
        except Exception:
            logger.exception(
                "Admin notification email failed for registration id=%s.",
                registration.pk,
            )
        return registration

    @transaction.atomic
    def approve_registration(self, registration: ContentManagerRegistration) -> None:
        from django.contrib.auth.models import Permission

        User = get_user_model()
        user = User.objects.filter(username=registration.username).first()

        if user is None:
            raise ValidationError(
                _("The existing user account for this registration could not be found.")
            )

        user.is_page_permitted = True
        user.is_active = True
        user.save(update_fields=['is_page_permitted', 'is_active'])

        try:
            perm = Permission.objects.get(codename='can_manage_content')
            user.user_permissions.add(perm)
        except Permission.DoesNotExist:
            logger.warning("Permission 'can_manage_content' not found; skipping.")

        registration.status = 'approved'
        registration.save(update_fields=['status'])

        RegistrationLog.objects.create(
            registration=registration,
            event=RegistrationLog.Event.APPROVAL,
        )

    @transaction.atomic
    def reject_registration(self, registration: ContentManagerRegistration) -> None:
        registration.status = 'rejected'
        registration.save(update_fields=['status'])
        RegistrationLog.objects.create(
            registration=registration,
            event=RegistrationLog.Event.REJECTION,
        )
        self._delete_registration_media(registration)

    def _delete_registration_media(self, registration: ContentManagerRegistration):
        if registration.photo:
            registration.photo.delete(save=False)
        if registration.video:
            registration.video.delete(save=False)

    def log_access_request(self, request_obj: RegistrationRequest) -> None:
        RegistrationLog.objects.create(
            request=request_obj,
            event=RegistrationLog.Event.ACCESS_REQUEST_CREATED,
            detail="Access request submitted",
        )

    def _decode_and_validate_image(self, data: str) -> File:
        import imghdr
        if ';base64,' in data:
            header, data = data.split(';base64,')
        else:
            raise ValidationError(_('Invalid image data.'))
        ext = 'png'
        if 'image/jpeg' in header:
            ext = 'jpg'
        elif 'image/png' in header:
            ext = 'png'
        else:
            raise ValidationError(_('Unsupported image format. Use JPEG or PNG.'))

        raw = base64.b64decode(data)
        if len(raw) > 5 * 1024 * 1024:
            raise ValidationError(_('Photo must be under 5 MB.'))

        img_type = imghdr.what(None, raw)
        if img_type not in ('jpeg', 'png'):
            raise ValidationError(_('Invalid image file.'))

        file_name = f'photo_{uuid.uuid4()}.{ext}'
        return ContentFile(raw, name=file_name)

    def _decode_and_validate_video(self, data: str) -> File:
        if ';base64,' in data:
            header, data = data.split(';base64,')
        else:
            raise ValidationError(_('Invalid video data.'))
        if 'video/webm' not in header:
            raise ValidationError(_('Unsupported video format. Use WebM.'))

        raw = base64.b64decode(data)
        if len(raw) > 20 * 1024 * 1024:
            raise ValidationError(_('Video must be under 20 MB.'))

        file_name = f'video_{uuid.uuid4()}.webm'
        return ContentFile(raw, name=file_name)